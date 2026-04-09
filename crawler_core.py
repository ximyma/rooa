"""
网站爬虫核心引擎 - 整站爬取 + 关键词搜索 + 定时任务
"""
import threading
import time
import random
import os
import requests
from queue import Queue, Empty
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import warnings
import chardet

warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# 顶层导入 app 和 db（跨线程使用 app_context）
from app import db as _db

TRACKING_QUERY_KEYS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'spm', 'from', 'source', '_t', 'timestamp'
}
HTML_CONTENT_TYPES = ('text/html', 'application/xhtml+xml')
TEXTLIKE_CONTENT_TYPES = ('text/plain', 'application/xml', 'text/xml')


# 快捷函数：带 app_context 的 db 操作
def _with_db(fn):
    """在 app_context 中执行数据库操作"""
    from app import app
    with app.app_context():
        return fn()


# 线程安全 logger
_print_lock = threading.Lock()


def _sync_log(task_id, message, level='info'):
    """线程安全的日志输出"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    msg = f"[{timestamp}] {message}"
    with _print_lock:
        try:
            print(msg)
        except UnicodeEncodeError:
            print(msg.encode('gbk', errors='replace').decode('gbk'))

    # 写入数据库日志
    try:
        from app import app
        from models import SystemOperationLog
        with app.app_context():
            log = SystemOperationLog(
                user_id=1,
                operation=f"[爬虫-{task_id}] {message}",
                module='crawler',
                result='success' if level != 'error' else 'fail'
            )
            _db.session.add(log)
            _db.session.commit()
    except Exception:
        pass


class CrawlerCore:
    """网站爬虫核心引擎"""

    def __init__(self, task_id, base_url, max_threads=5, max_depth=3,
                 attachment_handling='skip', download_dir='crawler_attachments',
                 schedule_enabled=False, schedule_interval=24, schedule_time='00:00'):
        self.task_id = task_id
        self.base_url = self._normalize_url(base_url) or base_url.strip()
        self.domain = urlparse(self.base_url).netloc.lower()
        self.max_threads = max(1, int(max_threads or 5))
        self.max_depth = max(0, int(max_depth or 3))
        self.attachment_handling = attachment_handling
        self.download_dir = download_dir
        self.session = self._build_session()

        # 任务控制
        self.queue = Queue()
        self.lock = threading.Lock()
        self.pause_flag = threading.Event()
        self.stop_flag = threading.Event()
        self.workers = []
        self.stats = {
            'queued': 0,
            'completed': 0,
            'errors': 0,
            'attachments': 0,
            'skipped': 0,
        }
        self.processed_urls = set()
        self.seen_urls = set()

        # 附件目录
        if self.attachment_handling == 'download' and not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir, exist_ok=True)

        # 加载已处理的 URL 并为本次任务预置起始页
        self._load_processed()

    def _build_session(self):
        """复用 Session，降低连接开销并增加轻量重试"""
        session = requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.3,
            allowed_methods=frozenset(['GET', 'HEAD']),
            status_forcelist=(429, 500, 502, 503, 504),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(pool_connections=self.max_threads * 2, pool_maxsize=self.max_threads * 2, max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'identity',
            'Connection': 'keep-alive',
        })
        return session

    def _normalize_url(self, url):
        """规范化 URL，保留有效查询参数，去掉锚点和常见追踪参数"""
        if not url:
            return ''
        absolute = urljoin(self.base_url if hasattr(self, 'base_url') else url, url.strip())
        parsed = urlparse(absolute)
        if parsed.scheme.lower() not in ('http', 'https') or not parsed.netloc:
            return ''

        query_items = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() not in TRACKING_QUERY_KEYS
        ]
        normalized = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            fragment='',
            query=urlencode(sorted(query_items), doseq=True)
        ).geturl()

        if normalized.endswith('/') and parsed.path not in ('', '/'):
            normalized = normalized.rstrip('/')
        return normalized

    def _queue_url(self, url, depth, force=False):
        """将页面加入待抓取队列"""
        normalized = self._normalize_url(url)
        if not normalized:
            return False

        if urlparse(normalized).netloc.lower() != self.domain:
            return False

        with self.lock:
            if not force and normalized in self.seen_urls:
                return False
            self.seen_urls.add(normalized)
            self.queue.put((normalized, depth))
            self.stats['queued'] += 1
        return True

    def _load_processed(self):
        """加载已处理的 URL"""
        from app import app
        from models import CrawlerPage
        try:
            with app.app_context():
                pages = CrawlerPage.query.filter_by(task_id=self.task_id, status='completed').all()
                self.processed_urls = {
                    self._normalize_url(p.url) or p.url
                    for p in pages if p.url
                }
                self.seen_urls = set(self.processed_urls)
            _sync_log(self.task_id, f"从断点恢复，已处理 {len(self.processed_urls)} 个页面")
        except Exception as e:
            _sync_log(self.task_id, f"加载断点失败: {e}", 'error')
            self.processed_urls = set()
            self.seen_urls = set()

        # 起始页每次运行都重新抓一次，用于发现新链接
        self._queue_url(self.base_url, 0, force=True)

    def _save_page(self, url, title=None, content=None, text_content=None,
                   status='completed', error_msg=None):
        """保存页面到数据库"""
        from app import app
        from models import CrawlerPage
        try:
            now = datetime.now()

            def clean_text(text):
                if text is None:
                    return None
                if isinstance(text, bytes):
                    try:
                        return text.decode('utf-8', errors='replace')
                    except Exception:
                        return text.decode('gbk', errors='replace')
                return text

            title = clean_text(title)
            content = clean_text(content)
            text_content = clean_text(text_content)
            error_msg = clean_text(error_msg)

            with app.app_context():
                existing = CrawlerPage.query.filter_by(url=url).first()
                if existing:
                    existing.title = title
                    existing.content = content
                    existing.text_content = text_content
                    existing.status = status
                    existing.error_msg = error_msg
                    existing.task_id = self.task_id
                    existing.updated_at = now
                else:
                    page = CrawlerPage(
                        task_id=self.task_id,
                        url=url,
                        title=title,
                        content=content,
                        text_content=text_content,
                        status=status,
                        error_msg=error_msg,
                    )
                    _db.session.add(page)
                _db.session.commit()
        except Exception as e:
            _sync_log(self.task_id, f"数据库写入失败: {e}", 'error')
            try:
                _db.session.rollback()
            except Exception:
                pass

    def _update_task_progress(self):
        """同步任务统计，便于列表页即时显示"""
        from app import app
        from models import CrawlerTask, CrawlerPage
        try:
            with app.app_context():
                task = CrawlerTask.query.get(self.task_id)
                if task:
                    task.pages_count = CrawlerPage.query.filter_by(task_id=self.task_id, status='completed').count()
                    task.last_run_at = datetime.now()
                    task.updated_at = datetime.now()
                    _db.session.commit()
        except Exception:
            try:
                _db.session.rollback()
            except Exception:
                pass

    def _extract_text(self, html):
        """从 HTML 提取纯文本"""
        try:
            if isinstance(html, bytes):
                try:
                    html = html.decode('utf-8', errors='replace')
                except Exception:
                    for enc in ('gbk', 'gb2312', 'latin-1'):
                        try:
                            html = html.decode(enc, errors='replace')
                            break
                        except Exception:
                            continue

            soup = BeautifulSoup(html, 'html.parser')
            for tag in soup(["script", "style", "noscript", "iframe", "meta", "link"]):
                tag.decompose()

            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return '\n'.join(chunk for chunk in chunks if chunk)
        except Exception as e:
            _sync_log(self.task_id, f"文本提取失败: {e}", 'warning')
            return ""

    def _fetch_page(self, url):
        """获取页面内容，仅处理 HTML/文本类页面"""
        response = self.session.get(url, timeout=(5, 15), allow_redirects=True)
        response.raise_for_status()

        content_type = (response.headers.get('Content-Type') or '').split(';')[0].strip().lower()
        if content_type and content_type not in HTML_CONTENT_TYPES and content_type not in TEXTLIKE_CONTENT_TYPES:
            raise ValueError(f"跳过非 HTML 页面: {content_type}")

        raw = response.content
        encoding = response.encoding
        if encoding == 'ISO-8859-1' or not encoding:
            detected = chardet.detect(raw)
            if detected['confidence'] > 0.7 and detected['encoding']:
                encoding = detected['encoding'].lower()
                if encoding == 'ascii':
                    encoding = 'utf-8'
            else:
                found = None
                for enc in ('gbk', 'gb2312', 'gb18030', 'utf-8', 'latin-1'):
                    try:
                        raw.decode(enc)
                        found = enc
                        break
                    except Exception:
                        continue
                encoding = found or 'utf-8'

        try:
            html = raw.decode(encoding, errors='replace')
        except Exception:
            html = raw.decode('utf-8', errors='replace')

        final_url = self._normalize_url(response.url) or self._normalize_url(url) or url
        return html, final_url

    def _extract_links(self, soup, base_url):
        """提取同域链接"""
        links = set()
        for tag in soup.find_all('a', href=True):
            href = (tag.get('href') or '').strip()
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#', '//')):
                continue
            absolute = self._normalize_url(urljoin(base_url, href))
            if not absolute:
                continue
            parsed = urlparse(absolute)
            if parsed.netloc.lower() == self.domain:
                links.add(absolute)
        return links

    def _is_attachment(self, url):
        """判断是否附件"""
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar.gz', '.png', '.jpg', '.jpeg', '.gif'
        ])

    def _process_page(self, url, depth):
        """处理单个页面"""
        while self.pause_flag.is_set():
            if self.stop_flag.is_set():
                return
            time.sleep(1)

        try:
            html, final_url = self._fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.get_text(strip=True) if soup.title else '无标题'
            text = self._extract_text(html)

            self._save_page(final_url, title=title, content=html, text_content=text)
            with self.lock:
                self.processed_urls.add(final_url)
                self.seen_urls.add(final_url)
                self.stats['completed'] += 1
            self._update_task_progress()

            page_links = self._extract_links(soup, final_url)

            # 处理附件
            if self.attachment_handling != 'skip':
                for att_url in page_links:
                    if self._is_attachment(att_url):
                        with self.lock:
                            self.stats['attachments'] += 1
                        if self.attachment_handling == 'log':
                            _sync_log(self.task_id, f"发现附件: {att_url}")
                        elif self.attachment_handling == 'db':
                            self._save_page(att_url, status='completed')

            # 提取新链接（仅抓到最大层级为止）
            if depth < self.max_depth:
                for link in page_links:
                    if self.stop_flag.is_set() or self._is_attachment(link):
                        continue
                    self._queue_url(link, depth + 1)
            else:
                _sync_log(self.task_id, f"层级上限已命中：{final_url}（深度 {depth}）")

            time.sleep(random.uniform(0.05, 0.2))

        except ValueError as e:
            self._save_page(url, status='skipped', error_msg=str(e))
            with self.lock:
                self.stats['skipped'] += 1
            _sync_log(self.task_id, f"跳过页面 [{url[:60]}]: {e}", 'warning')
        except Exception as e:
            self._save_page(url, status='error', error_msg=str(e))
            with self.lock:
                self.stats['errors'] += 1
            _sync_log(self.task_id, f"处理失败 [{url[:60]}]: {e}", 'error')

    def _worker(self):
        """工作线程"""
        while not self.stop_flag.is_set():
            try:
                url, depth = self.queue.get(timeout=1)
            except Empty:
                continue

            try:
                self._process_page(url, depth)
            finally:
                self.queue.task_done()

    def start(self):
        """启动爬虫"""
        if any(worker.is_alive() for worker in self.workers):
            _sync_log(self.task_id, "爬虫已在运行，跳过重复启动")
            return

        self.stop_flag.clear()
        self.pause_flag.clear()
        self.workers = []
        _sync_log(
            self.task_id,
            f"爬虫启动，目标: {self.base_url}，线程: {self.max_threads}，最大层级: {self.max_depth}"
        )


        for _ in range(self.max_threads):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)

    def pause(self):
        """暂停"""
        self.pause_flag.set()
        _sync_log(self.task_id, "爬虫已暂停")


    def resume(self):
        """恢复"""
        self.pause_flag.clear()
        _sync_log(self.task_id, "爬虫已恢复")


    def stop(self):
        """停止"""
        self.stop_flag.set()
        _sync_log(self.task_id, "爬虫已停止")

        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=2)

    def get_status(self):
        """获取当前状态"""
        return {
            'queued': self.stats['queued'],
            'completed': self.stats['completed'],
            'errors': self.stats['errors'],
            'attachments': self.stats['attachments'],
            'skipped': self.stats['skipped'],
            'paused': self.pause_flag.is_set(),
            'stopped': self.stop_flag.is_set(),
            'max_depth': self.max_depth,
        }


# 全局爬虫实例字典
_active_crawlers = {}


def get_crawler(task_id):
    """获取或创建爬虫实例"""
    if task_id not in _active_crawlers:
        from models import CrawlerTask
        task = CrawlerTask.query.get(task_id)
        if not task:
            return None
        _active_crawlers[task_id] = CrawlerCore(
            task_id=task.id,
            base_url=task.base_url,
            max_threads=task.max_threads,
            max_depth=getattr(task, 'max_depth', 3) or 3,
            attachment_handling=task.attachment_handling,
            download_dir=task.download_dir or 'crawler_attachments',
            schedule_enabled=task.schedule_enabled,
            schedule_interval=task.schedule_interval,
            schedule_time=task.schedule_time,
        )
    return _active_crawlers[task_id]


def stop_crawler(task_id):
    """停止并移除爬虫实例"""
    if task_id in _active_crawlers:
        _active_crawlers[task_id].stop()
        del _active_crawlers[task_id]
