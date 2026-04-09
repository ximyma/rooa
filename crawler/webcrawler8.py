import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import sqlite3
import threading
import time
import random
import re
import os
import logging
import logging.handlers
from urllib.parse import urljoin, urlparse
from queue import Queue
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import schedule
import csv
import chardet
import warnings

# 忽略BeautifulSoup的编码警告
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

# ==================== 数据库模块 ====================
class ThreadSafeDB:
    """线程安全的数据库连接管理器"""
    def __init__(self, db_name='./data/webcrawler_data.db'):
        self.db_name = db_name
        self.local = threading.local()
        self._closed = False
        self.init_database()

    def get_conn(self):
        """获取线程专用的数据库连接（确保连接有效）"""
        if self._closed:
            raise sqlite3.ProgrammingError("Database connection has been closed")
            
        if not hasattr(self.local, 'conn') or self.local.conn is None:
            try:
                self.local.conn = sqlite3.connect(
                    self.db_name,
                    check_same_thread=False,
                    timeout=30,
                    isolation_level=None,
                    detect_types=sqlite3.PARSE_DECLTYPES
                )
                self.local.conn.execute("PRAGMA encoding = 'UTF-8'")
                self.local.conn.execute("PRAGMA journal_mode=WAL")
                self.local.conn.execute("PRAGMA busy_timeout = 5000")
            except sqlite3.Error as e:
                logging.error(f"创建数据库连接失败: {str(e)}")
                raise
        return self.local.conn

    def init_database(self):
        """初始化数据库结构（带重试机制）"""
        max_retries = 3
        for attempt in range(max_retries):
            conn = None
            try:
                conn = self.get_conn()
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS pages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE,
                        title TEXT,
                        content TEXT,
                        text_content TEXT,
                        status TEXT CHECK(status IN ('pending', 'completed', 'error', 'skipped')),
                        error_msg TEXT,
                        base_url TEXT,
                        created_at TEXT,
                        updated_at TEXT
                    )''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY,
                        base_url TEXT UNIQUE,
                        status TEXT CHECK(status IN ('running', 'paused', 'stopped')),
                        threads INTEGER,
                        download_dir TEXT,
                        schedule_enabled BOOLEAN DEFAULT 0,
                        schedule_interval INTEGER DEFAULT 24,
                        schedule_time TEXT DEFAULT '00:00',
                        updated_at TEXT
                    )''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS attachments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT UNIQUE,
                        filename TEXT,
                        content_type TEXT,
                        file_path TEXT,
                        created_at TEXT
                    )''')
                
                conn.commit()
                break
            except sqlite3.Error as e:
                if attempt == max_retries - 1:
                    logging.error(f"数据库初始化失败: {str(e)}")
                    raise
                time.sleep(1)
            finally:
                if conn:
                    conn.close()

    def close_all(self):
        """安全关闭所有数据库连接"""
        if hasattr(self.local, 'conn'):
            try:
                if self.local.conn:
                    self.local.conn.close()
            except sqlite3.Error as e:
                logging.error(f"关闭数据库连接失败: {str(e)}")
            finally:
                self.local.conn = None
        self._closed = True

    def is_closed(self):
        """检查连接是否已关闭"""
        return self._closed

    def reopen(self):
        """重新打开数据库连接"""
        if hasattr(self.local, 'conn'):
            self.close_all()
        self._closed = False
        return self.get_conn()
    
    def _safe_db_operation(self, operation, *args, **kwargs):
        """安全的数据库操作包装器"""
        max_retries = 3
        for attempt in range(max_retries):
            conn = None
            try:
                if self.is_closed():
                    self.reopen()
                
                conn = self.get_conn()
                cursor = conn.cursor()
                result = operation(cursor, *args, **kwargs)
                conn.commit()
                return result
            except sqlite3.ProgrammingError as e:
                if "closed database" in str(e) and attempt < max_retries - 1:
                    self.reopen()
                    continue
                raise
            except sqlite3.Error as e:
                if attempt == max_retries - 1:
                    logging.error(f"数据库操作失败: {str(e)}")
                    raise
                time.sleep(1)
            finally:
                if conn:
                    conn.close() 

# ==================== 核心爬虫模块 ====================
class WebCrawlerCore:
    def __init__(self, db, base_url, max_threads=5, 
                 attachment_handling='skip', download_dir='attachments',
                 log_callback=None, status_callback=None,
                 schedule_enabled=False, schedule_interval=24, schedule_time='00:00'):
        self.db = db
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_threads = max_threads
        self.attachment_handling = attachment_handling
        self.download_dir = download_dir
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.schedule_enabled = schedule_enabled
        self.schedule_interval = schedule_interval
        self.schedule_time = schedule_time
        
        # 任务控制
        self.queue = Queue()
        self.lock = threading.Lock()
        self.pause_event = threading.Event()
        self.stop_flag = threading.Event()
        self.workers = []
        self.schedule_thread = None
        self.last_run_time = None
        self.next_run_time = None
        
        # 初始化
        self.init_storage()
        self.load_task_state()
        self.load_processed_urls()

    def init_storage(self):
        """初始化存储目录"""
        if self.attachment_handling == 'download' and not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def _safe_db_operation(self, operation, *args, **kwargs):
        """安全的数据库操作包装器"""
        max_retries = 3
        for attempt in range(max_retries):
            conn = None
            try:
                conn = self.db.get_conn()
                cursor = conn.cursor()
                result = operation(cursor, *args, **kwargs)
                conn.commit()
                return result
            except sqlite3.ProgrammingError as e:
                if "closed database" in str(e) and attempt < max_retries - 1:
                    self.db.reopen()
                    continue
                raise
            except sqlite3.Error as e:
                if attempt == max_retries - 1:
                    self._log(f"数据库操作失败: {str(e)}", logging.ERROR)
                    raise
                time.sleep(1)
            finally:
                if conn:
                    conn.close()

    def load_task_state(self):
        """加载任务状态（安全版本）"""
        def op(cursor):
            cursor.execute('SELECT status FROM tasks WHERE base_url=?', (self.base_url,))
            return cursor.fetchone()
            
        try:
            result = self._safe_db_operation(op)
            if result and result[0] == 'paused':
                self.pause_event.set()
                self._log("检测到未完成的任务，进入暂停状态", logging.INFO)
        except Exception as e:
            self._log(f"加载任务状态失败: {str(e)}", logging.ERROR)

    def save_task_state(self, status):
        """保存任务状态（安全版本）"""
        def op(cursor):
            cursor.execute('''
                INSERT OR REPLACE INTO tasks 
                (id, base_url, status, threads, download_dir, schedule_enabled, schedule_interval, schedule_time, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.base_url, status, self.max_threads, 
                 self.download_dir, self.schedule_enabled, self.schedule_interval, 
                 self.schedule_time, datetime.now().isoformat()))
        
        try:
            self._safe_db_operation(op)
        except Exception as e:
            self._log(f"保存任务状态失败: {str(e)}", logging.ERROR)

    def load_processed_urls(self):
        """加载已处理的URL（安全版本）"""
        def op(cursor):
            cursor.execute('SELECT url FROM pages WHERE base_url=?', (self.base_url,))
            return {row[0] for row in cursor.fetchall()}
            
        try:
            self.processed_urls = self._safe_db_operation(op)
            if self.base_url not in self.processed_urls:
                self.queue.put(self.base_url)
                self.add_page_to_db(self.base_url, status='pending')
        except Exception as e:
            self._log(f"加载已处理URL失败: {str(e)}", logging.ERROR)
            self.processed_urls = set()

    def add_page_to_db(self, url, title=None, content=None, text_content=None, status='completed', error_msg=None):
        """添加页面记录（安全版本）"""
        now = datetime.now().isoformat()
        
        def prepare_text(text):
            if text is None:
                return None
            if isinstance(text, bytes):
                try:
                    return text.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        return text.decode('gbk', errors='replace')
                    except:
                        return "[编码错误]"
            return text
        
        title = prepare_text(title)
        content = prepare_text(content)
        text_content = prepare_text(text_content)
        error_msg = prepare_text(error_msg)
        
        def op(cursor):
            cursor.execute('''
                INSERT OR REPLACE INTO pages 
                (url, title, content, text_content, status, error_msg, base_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (url, title, content, text_content, status, error_msg, self.base_url, now, now))
        
        try:
            self._safe_db_operation(op)
        except Exception as e:
            self._log(f"数据库写入失败: {str(e)}", logging.ERROR)

    def extract_text_from_html(self, html):
        """从HTML中提取纯文本"""
        try:
            # 如果html是bytes类型，先尝试解码
            if isinstance(html, bytes):
                try:
                    html = html.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        html = html.decode('gbk')
                    except:
                        # 如果无法解码，使用chardet检测编码
                        encoding = chardet.detect(html)['encoding']
                        html = html.decode(encoding, errors='replace')
            
            # 使用BeautifulSoup解析
            soup = BeautifulSoup(html, 'html.parser')
            
            # 移除不需要的标签
            for script in soup(["script", "style", "noscript", "iframe", "meta", "link"]):
                script.decompose()
            
            # 获取文本并清理
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            self._log(f"文本提取失败: {str(e)}", logging.ERROR)
            return "文本提取错误"

    def process_attachment(self, url):
        """处理附件下载"""
        try:
            if self.pause_event.is_set():
                return

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Encoding': 'identity'
            }
            
            # 先获取头部信息
            with requests.head(url, headers=headers, timeout=10) as res:
                res.raise_for_status()
                content_type = res.headers.get('Content-Type', 'application/octet-stream')
                filename = self._get_filename(url, res.headers)

            if self.attachment_handling == 'download':
                filepath = os.path.join(self.download_dir, filename)
                with requests.get(url, stream=True, timeout=30, headers=headers) as res:
                    res.raise_for_status()
                    with open(filepath, 'wb') as f:
                        for chunk in res.iter_content(chunk_size=8192):
                            if self.stop_flag.is_set():
                                return
                            f.write(chunk)
                self._save_attachment(url, filename, content_type, filepath)
            else:
                self._save_attachment(url, filename, content_type)
                
        except Exception as e:
            self._log(f"附件处理失败: {url} - {str(e)}", logging.ERROR)

    def process_page(self, url):
        """处理单个页面"""
        try:
            while self.pause_event.is_set():
                time.sleep(1)
                if self.stop_flag.is_set():
                    return

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Accept-Encoding': 'identity'
            }
            
            # 获取原始字节内容
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            raw_content = response.content
            
            # 检测编码
            encoding = response.encoding
            if encoding == 'ISO-8859-1' or not encoding:
                detected = chardet.detect(raw_content)
                if detected['confidence'] > 0.7:
                    encoding = detected['encoding']
                else:
                    encoding = 'utf-8'
            
            # 解码内容
            try:
                html_content = raw_content.decode(encoding, errors='replace')
            except:
                html_content = raw_content.decode('utf-8', errors='replace')
            
            # 提取文本
            soup = BeautifulSoup(html_content, 'html.parser')
            title = soup.title.string if soup.title else '无标题'
            text_content = self.extract_text_from_html(html_content)
            
            # 存储到数据库
            self.add_page_to_db(url, title=title, content=html_content, text_content=text_content)
            
            # 处理页面中的链接
            for link in self._extract_links(soup, url):
                if self.stop_flag.is_set():
                    return
                
                if self._is_attachment(link):
                    if self.attachment_handling != 'skip':
                        threading.Thread(target=self.process_attachment, args=(link,)).start()
                    continue
                
                with self.lock:
                    if link not in self.processed_urls:
                        self.processed_urls.add(link)
                        self.queue.put(link)
                        self.add_page_to_db(link, status='pending')
                        self._log(f"发现新链接: {link}", logging.INFO)

        except Exception as e:
            self._log(f"页面处理失败: {url} - {str(e)}", logging.ERROR)
            self.add_page_to_db(url, status='error', error_msg=str(e))

    def worker(self):
        """工作线程主循环"""
        while not self.stop_flag.is_set():
            try:
                url = self.queue.get(timeout=5)
                self.process_page(url)
                self.queue.task_done()
            except:
                continue

    def start_crawling(self):
        """启动爬虫"""
        self.stop_flag.clear()
        self.save_task_state('running')
        self._update_status("爬虫启动中...")
        
        for _ in range(self.max_threads):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            self.workers.append(t)
        
        self._log(f"爬虫已启动，线程数: {self.max_threads}", logging.INFO)
        if self.schedule_enabled:
            self.start_scheduled_task()

    def start_scheduled_task(self):
        """启动定时任务"""
        if not self.schedule_thread:
            self.schedule_thread = threading.Thread(target=self._schedule_worker, daemon=True)
            self.schedule_thread.start()
            self._log(f"定时任务已启动，间隔：{self.schedule_interval}小时，时间：{self.schedule_time}", logging.INFO)

    def _schedule_worker(self):
        """定时任务工作线程"""
        schedule.clear()
        schedule.every(self.schedule_interval).hours.at(self.schedule_time).do(self._run_scheduled_task)
        
        while not self.stop_flag.is_set():
            self.next_run_time = schedule.next_run()
            time.sleep(1)
            schedule.run_pending()

    def _run_scheduled_task(self):
        """执行定时爬取"""
        self.last_run_time = datetime.now()
        self._log(f"定时任务启动 [{self.last_run_time.strftime('%Y-%m-%d %H:%M:%S')}]", logging.INFO)
        self.start_crawling()

    def pause(self):
        """暂停爬虫"""
        self.pause_event.set()
        self.save_task_state('paused')
        self._update_status("已暂停")
        self._log("爬虫已暂停", logging.INFO)

    def resume(self):
        """恢复爬虫"""
        self.pause_event.clear()
        self.save_task_state('running')
        self._update_status("运行中...")
        self._log("爬虫已恢复运行", logging.INFO)

    def stop(self):
        """停止爬虫"""
        self.stop_flag.set()
        self.save_task_state('stopped')
        for t in self.workers:
            t.join(timeout=1)
        self._update_status("已停止")
        self._log("爬虫已停止", logging.INFO)

    def _log(self, message, level):
        """统一日志记录方法"""
        if self.log_callback:
            record = logging.LogRecord(
                name=__name__,
                level=level,
                pathname=__file__,
                lineno=0,
                msg=message,
                args=None,
                exc_info=None
            )
            self.log_callback(record)

    def _update_status(self, message):
        """更新状态回调"""
        if self.status_callback:
            self.status_callback(message)

    def _is_attachment(self, url):
        """判断是否附件"""
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar.gz', '.png', '.jpg', '.jpeg', '.gif'
        ])

    def _extract_links(self, soup, base_url):
        """提取有效链接"""
        links = set()
        for tag in soup.find_all('a', href=True):
            href = tag['href'].strip()
            if href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
                continue
            absolute_url = urljoin(base_url, href)
            parsed = urlparse(absolute_url)
            if parsed.netloc == self.domain:
                clean_url = parsed._replace(fragment='', query='').geturl()
                links.add(clean_url)
        return links

    def _get_filename(self, url, headers):
        """获取安全文件名"""
        if 'Content-Disposition' in headers:
            match = re.findall(r'filename\*?=["\']?(?:UTF-\d["\']*)?([^;\r\n"]+)', 
                             headers['Content-Disposition'], re.IGNORECASE)
            if match:
                return self._sanitize_filename(match[0])
        
        filename = os.path.basename(urlparse(url).path)
        return self._sanitize_filename(filename or f"file_{hash(url)}.dat")

    def _save_attachment(self, url, filename, content_type, filepath=None):
        """保存附件信息"""
        try:
            conn = self.db.get_conn()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO attachments 
                (url, filename, content_type, file_path, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (url, filename, content_type, filepath, datetime.now().isoformat()))
            conn.commit()
        except sqlite3.Error as e:
            self._log(f"附件保存失败: {str(e)}", logging.ERROR)

    def _sanitize_filename(self, filename):
        """清理非法字符"""
        filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            return name[:200] + ext
        return filename

# ==================== GUI界面模块 ====================
class CrawlerGUI:
    def __init__(self, master, db=None):
        """初始化GUI界面
        Args:
            master: 主窗口
            db: 可选的数据库连接 (如果为None则创建新连接)
        """
        self.master = master
        master.title("智能网站爬虫 v8.2")
        master.geometry("1000x750")
        
        # 初始化数据库连接
        self.db = db if db is not None else ThreadSafeDB()
        
        self.log_queue = Queue()
        self._setup_logging()
        self._create_widgets()
        self.crawler = None
        
        self.master.protocol("WM_DELETE_WINDOW", self._on_close)
        self.master.after(100, self._poll_log_queue)
        self.master.after(2000, self._update_monitor)
        self._check_previous_task()

    def _get_system_font(self):
        """获取系统支持的中文字体"""
        try:
            # 测试常见中文字体
            test_fonts = ['Microsoft YaHei', 'SimHei', 'SimSun', 'Arial Unicode MS', 'Arial']
            for font in test_fonts:
                try:
                    tk.font.Font(family=font)
                    return font
                except:
                    continue
            return 'TkDefaultFont'
        except:
            return 'TkDefaultFont'

    def _setup_logging(self):
        """配置日志系统"""
        self.log_handler = logging.handlers.QueueHandler(self.log_queue)
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        root_logger.setLevel(logging.INFO)

    def _create_widgets(self):
        """创建界面组件"""
        # 配置面板
        config_frame = ttk.LabelFrame(self.master, text="配置", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)

        # 使用网格布局
        config_frame.grid_columnconfigure(1, weight=1)
        
        # 目标网址
        ttk.Label(config_frame, text="目标网址:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.url_entry = ttk.Entry(config_frame, width=70)
        self.url_entry.grid(row=0, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=2)
        self.url_entry.insert(0, "http://news.sina.com.cn")

        # 线程数设置
        ttk.Label(config_frame, text="线程数:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.thread_var = tk.IntVar(value=5)
        self.thread_spin = ttk.Spinbox(
            config_frame,
            from_=1,
            to=20,
            textvariable=self.thread_var,
            width=5,
            validate="key",
            validatecommand=(config_frame.register(self._validate_thread), '%P')
        )
        self.thread_spin.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        # 定时任务开关
        ttk.Label(config_frame, text="定时任务:").grid(row=1, column=2, sticky=tk.E, padx=5, pady=2)
        self.schedule_enabled = tk.BooleanVar()
        self.schedule_check = ttk.Checkbutton(
            config_frame,
            variable=self.schedule_enabled,
            command=self._toggle_schedule_controls
        )
        self.schedule_check.grid(row=1, column=3, sticky=tk.W, pady=2)

        # 附件处理
        ttk.Label(config_frame, text="附件处理:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.attach_var = tk.StringVar()
        self.attach_combo = ttk.Combobox(
            config_frame,
            textvariable=self.attach_var,
            values=["跳过", "记录到日志", "保存到数据库", "下载附件"],
            state="readonly",
            width=18
        )
        self.attach_combo.current(0)
        self.attach_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        self.attach_combo.bind("<<ComboboxSelected>>", self._update_ui)

        # 下载路径
        self.dl_frame = ttk.Frame(config_frame)
        ttk.Label(self.dl_frame, text="下载路径:").pack(side=tk.LEFT)
        self.dl_path = tk.StringVar()
        self.dl_entry = ttk.Entry(self.dl_frame, textvariable=self.dl_path, width=50)
        self.dl_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(self.dl_frame, text="浏览...", command=self._select_dl_path).pack(side=tk.LEFT)
        self.dl_frame.grid(row=3, column=1, sticky=tk.W, pady=2)
        self.dl_frame.grid_remove()
        
        # 定时参数框架
        self.schedule_frame = ttk.Frame(config_frame)
        self.schedule_frame.grid(row=4, column=0, columnspan=4, sticky=tk.EW, pady=5)
        
        # 间隔时间
        ttk.Label(self.schedule_frame, text="间隔:").pack(side=tk.LEFT)
        self.interval_var = tk.IntVar(value=24)
        self.interval_spin = ttk.Spinbox(
            self.schedule_frame,
            from_=1,
            to=720,
            textvariable=self.interval_var,
            width=5
        )
        self.interval_spin.pack(side=tk.LEFT, padx=5)
        ttk.Label(self.schedule_frame, text="小时").pack(side=tk.LEFT)

        # 执行时间
        ttk.Label(self.schedule_frame, text="每天时间:").pack(side=tk.LEFT, padx=(10,0))
        self.time_var = tk.StringVar(value='00:00')
        self.time_entry = ttk.Entry(self.schedule_frame, textvariable=self.time_var, width=8)
        self.time_entry.pack(side=tk.LEFT)
        ttk.Button(
            self.schedule_frame,
            text="⏰",
            width=3,
            command=self._show_time_picker
        ).pack(side=tk.LEFT, padx=5)
        self.schedule_frame.grid_remove()

        # 控制按钮
        btn_frame = ttk.Frame(config_frame)
        btn_frame.grid(row=5, column=0, columnspan=4, pady=10)
        self.start_btn = ttk.Button(btn_frame, text="开始抓取", command=self._start_crawling)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.pause_btn = ttk.Button(btn_frame, text="暂停", command=self._toggle_pause, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        # 数据操作按钮
        data_btn_frame = ttk.Frame(config_frame)
        data_btn_frame.grid(row=6, column=0, columnspan=4, pady=5)
        ttk.Button(data_btn_frame, text="查看历史数据", command=self._view_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(data_btn_frame, text="导出数据", command=self._export_data).pack(side=tk.LEFT, padx=5)
        
        # 状态监控
        status_frame = ttk.LabelFrame(self.master, text="实时状态", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        status_grid = ttk.Frame(status_frame)
        status_grid.pack(fill=tk.X, expand=True)
        
        self.queue_size = ttk.Label(status_grid, text="待处理队列: 0")
        self.queue_size.grid(row=0, column=0, padx=10, sticky=tk.W)
        
        self.processed_count = ttk.Label(status_grid, text="已处理页面: 0")
        self.processed_count.grid(row=0, column=1, padx=10, sticky=tk.W)
        
        self.attachment_count = ttk.Label(status_grid, text="处理附件: 0")
        self.attachment_count.grid(row=0, column=2, padx=10, sticky=tk.W)
        
        self.schedule_status = ttk.Label(status_grid, text="")
        self.schedule_status.grid(row=0, column=3, padx=10, sticky=tk.W)
        
        # 日志区域
        log_frame = ttk.LabelFrame(self.master, text="运行日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建带滚动条的文本区域
        self.log_text = tk.Text(
            log_frame, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=(self._get_system_font(), 10)
        )
        
        # 配置标签样式
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("error", foreground="red")
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(
            self.master, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            padding=5
        )
        status_bar.pack(fill=tk.X, padx=10, pady=2)

    def _update_ui(self, event=None):
        """更新界面显示"""
        if self.attach_var.get() == "下载附件":
            self.dl_frame.grid()
        else:
            self.dl_frame.grid_remove()

    def _select_dl_path(self):
        """选择下载路径"""
        path = filedialog.askdirectory()
        if path:
            self.dl_path.set(path)

    def _validate_thread(self, P):
        """验证线程数输入"""
        return P.isdigit() and 1 <= int(P) <= 20 or P == ""



    def _start_crawling(self, resume=False):
        """启动爬虫"""
        if not resume and not self._validate_input():
            return
            
        config = {
            'db': self.db,
            'base_url': self.url_entry.get().strip(),
            'max_threads': self.thread_var.get(),
            'attachment_handling': self._translate_attach_mode(),
            'download_dir': self.dl_path.get(),
            'log_callback': self.log_message,
            'status_callback': self._update_status,
            'schedule_enabled': self.schedule_enabled.get(),
            'schedule_interval': self.interval_var.get(),
            'schedule_time': self.time_var.get()
        }
        
        try:
            self.crawler = WebCrawlerCore(**config)
            if resume:
                self.crawler.resume()
            else:
                self.crawler.start_crawling()
            self._toggle_buttons(True)
            self._toggle_schedule_controls()
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {str(e)}")

    def _toggle_schedule_controls(self):
        """切换定时控件状态"""
        if self.schedule_enabled.get():
            self.schedule_frame.grid()
            self._update_schedule_status()
        else:
            self.schedule_frame.grid_remove()
            self.schedule_status.config(text="")

    def _show_time_picker(self):
        """显示时间选择对话框"""
        top = tk.Toplevel(self.master)
        top.title("选择时间")
        
        hour_var = tk.IntVar(value=int(self.time_var.get().split(':')[0]))
        minute_var = tk.IntVar(value=int(self.time_var.get().split(':')[1]))
        
        ttk.Spinbox(top, from_=0, to=23, textvariable=hour_var, width=3).pack(side=tk.LEFT)
        ttk.Label(top, text=":").pack(side=tk.LEFT)
        ttk.Spinbox(top, from_=0, to=59, textvariable=minute_var, width=3).pack(side=tk.LEFT)
        
        def set_time():
            self.time_var.set(f"{hour_var.get():02d}:{minute_var.get():02d}")
            top.destroy()
            self._update_schedule_status()
        
        ttk.Button(top, text="确定", command=set_time).pack(side=tk.LEFT, padx=5)
        top.transient(self.master)
        top.grab_set()

    def _update_schedule_status(self):
        """更新定时任务状态显示"""
        if self.schedule_enabled.get():
            next_run = datetime.now().replace(
                hour=int(self.time_var.get().split(':')[0]),
                minute=int(self.time_var.get().split(':')[1]),
                second=0
            )
            if next_run < datetime.now():
                next_run += timedelta(hours=self.interval_var.get())
            
            status_text = f"下次运行时间: {next_run.strftime('%Y-%m-%d %H:%M')}"
            self.schedule_status.config(text=status_text)
        else:
            self.schedule_status.config(text="")

    def _toggle_pause(self):
        """切换暂停/恢复状态"""
        if self.crawler:
            if self.crawler.pause_event.is_set():
                self.crawler.resume()
                self.pause_btn.config(text="暂停")
            else:
                self.crawler.pause()
                self.pause_btn.config(text="恢复")


    def _check_previous_task(self):
        """检查未完成的任务（安全版本）"""
        def op(cursor):
            cursor.execute('''
                SELECT base_url, status, schedule_enabled, schedule_interval, schedule_time 
                FROM tasks 
                WHERE status IN ("running", "paused")
            ''')
            return cursor.fetchone()
            
        try:
            result = self.db._safe_db_operation(op)
            if result:
                base_url, status, schedule_enabled, interval, time = result
                choice = messagebox.askyesnocancel(
                    "恢复任务",
                    f"检测到未完成的任务: {base_url}\n状态: {status}",
                    detail="选择'是'恢复任务，'否'新建任务，'取消'清除任务记录"
                )
                if choice is None:
                    self._clean_task(base_url)
                elif choice:
                    self.url_entry.delete(0, tk.END)
                    self.url_entry.insert(0, base_url)
                    self.schedule_enabled.set(schedule_enabled)
                    self.interval_var.set(interval)
                    self.time_var.set(time)
                    self._start_crawling(resume=True)
        except Exception as e:
            self.log_message(logging.makeLogRecord({
                'msg': f"任务恢复检查失败: {str(e)}",
                'levelno': logging.ERROR
            }))

    def _clean_task(self, base_url):
        """清除任务记录（安全版本）"""
        def op(cursor):
            cursor.execute('DELETE FROM tasks WHERE base_url=?', (base_url,))
            cursor.execute('DELETE FROM pages WHERE base_url=?', (base_url,))
            cursor.execute('DELETE FROM attachments WHERE url LIKE ?', (f"%{urlparse(base_url).netloc}%",))
        
        try:
            self.db._safe_db_operation(op)
            self.log_message(logging.makeLogRecord({
                'msg': f"已清除任务记录: {base_url}",
                'levelno': logging.INFO
            }))
        except Exception as e:
            self.log_message(logging.makeLogRecord({
                'msg': f"清理任务失败: {str(e)}",
                'levelno': logging.ERROR
            }))

    def _update_monitor(self):
        """更新状态监控（安全版本）"""
        if self.crawler:
            self.queue_size.config(text=f"待处理队列: {self.crawler.queue.qsize()}")
            try:
                def op(cursor):
                    cursor.execute('SELECT COUNT(*) FROM pages WHERE base_url=?', (self.crawler.base_url,))
                    self.processed_count.config(text=f"已处理页面: {cursor.fetchone()[0]}")
                    cursor.execute('SELECT COUNT(*) FROM attachments WHERE url LIKE ?', (f"%{self.crawler.domain}%",))
                    self.attachment_count.config(text=f"处理附件: {cursor.fetchone()[0]}")
                
                self.db._safe_db_operation(op)
                
                if self.crawler.schedule_enabled:
                    status_text = f"下次运行: {self.crawler.next_run_time.strftime('%Y-%m-%d %H:%M')} | 上次运行: {self.crawler.last_run_time.strftime('%Y-%m-%d %H:%M') if self.crawler.last_run_time else '无'}"
                    self.schedule_status.config(text=status_text)
            except:
                pass
        self.master.after(2000, self._update_monitor)

    def log_message(self, record):
        """处理日志显示"""
        self.log_text.config(state=tk.NORMAL)
        tag = "info"
        if record.levelno >= logging.ERROR:
            tag = "error"
        elif record.levelno >= logging.WARNING:
            tag = "warning"
        
        msg = f"[{datetime.now().strftime('%H:%M:%S')}] {record.getMessage()}\n"
        self.log_text.insert(tk.END, msg, tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _update_status(self, message):
        """更新状态栏"""
        self.status_var.set(message)
        self.master.update_idletasks()

    def _toggle_buttons(self, running):
        """切换按钮状态"""
        state = tk.DISABLED if running else tk.NORMAL
        self.start_btn.config(state=state)
        self.pause_btn.config(state=tk.NORMAL if running else tk.DISABLED)

    def _on_close(self):
        """处理窗口关闭事件"""
        if self.crawler:
            self.crawler.stop()
        self.db.close_all()
        self.master.destroy()

    def _poll_log_queue(self):
        """处理日志队列"""
        while not self.log_queue.empty():
            record = self.log_queue.get_nowait()
            self.log_message(record)
        self.master.after(100, self._poll_log_queue)

    def _translate_attach_mode(self):
        """转换附件处理模式"""
        return {
            '跳过': 'skip',
            '记录到日志': 'log',
            '保存到数据库': 'db',
            '下载附件': 'download'
        }[self.attach_var.get()]

    def _validate_input(self):
        """验证输入有效性"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入目标网址")
            return False
        if not url.startswith(('http://', 'https://')):
            messagebox.showwarning("警告", "网址必须以http://或https://开头")
            return False
        if self.attach_var.get() == "下载附件" and not self.dl_path.get():
            messagebox.showwarning("警告", "请选择下载路径")
            return False
        if self.schedule_enabled.get():
            try:
                hours, minutes = map(int, self.time_var.get().split(':'))
                if not (0 <= hours < 24 and 0 <= minutes < 60):
                    raise ValueError
            except:
                messagebox.showwarning("警告", "时间格式应为HH:MM")
                return False
            if not 1 <= self.interval_var.get() <= 720:
                messagebox.showwarning("警告", "间隔时间应在1-720小时之间")
                return False
        return True

    def _view_history(self):
        """查看历史数据"""
        try:
            def op(cursor):
                cursor.execute("SELECT DISTINCT base_url FROM pages ORDER BY created_at DESC")
                sites = [row[0] for row in cursor.fetchall()]
                
                if not sites:
                    messagebox.showinfo("提示", "没有历史数据")
                    return None
                    
                site = simpledialog.askstring(
                    "选择网站", 
                    "请输入要查看的网站URL:", 
                    initialvalue=sites[0] if sites else ""
                )
                if not site:
                    return None
                    
                cursor.execute('''
                    SELECT url, title, text_content 
                    FROM pages 
                    WHERE base_url=? AND status='completed' AND text_content IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT 100
                ''', (site,))
                return (site, cursor.fetchall())
            
            result = self.db._safe_db_operation(op)
            if not result:
                return
                
            site, results = result
            
            if not results:
                messagebox.showinfo("提示", f"没有找到 {site} 的文本数据")
                return
            
            # 创建查看窗口
            history_window = tk.Toplevel(self.master)
            history_window.title(f"历史数据 - {site}")
            history_window.geometry("1000x700")
            
            # 设置字体
            font = (self._get_system_font(), 10)
            
            # 创建带滚动条的框架
            main_frame = ttk.Frame(history_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 创建树形视图
            tree = ttk.Treeview(
                main_frame, 
                columns=('url', 'title', 'content'), 
                show='headings',
                selectmode='browse'
            )
            tree.heading('url', text='URL')
            tree.heading('title', text='标题')
            tree.heading('content', text='内容摘要')
            
            tree.column('url', width=200, anchor=tk.W)
            tree.column('title', width=150, anchor=tk.W)
            tree.column('content', width=600, anchor=tk.W)
            
            # 添加滚动条
            vsb = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
            hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            
            # 布局
            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            
            main_frame.grid_rowconfigure(0, weight=1)
            main_frame.grid_columnconfigure(0, weight=1)
            
            # 添加数据
            for row in results:
                url, title, content = row
                
                # 处理可能的编码问题
                try:
                    if isinstance(title, bytes):
                        title = title.decode('utf-8', errors='replace')
                    if isinstance(content, bytes):
                        content = content.decode('utf-8', errors='replace')
                except:
                    title = "编码错误"
                    content = "内容编码错误"
                
                # 创建摘要
                content_preview = (content[:100] + '...') if len(content) > 100 else content
                tree.insert("", "end", values=(url, title, content_preview))
            
            # 双击查看完整内容
            def on_double_click(event):
                selected_item = tree.selection()
                if not selected_item:
                    return
                
                item = selected_item[0]
                values = tree.item(item, 'values')
                
                # 创建内容窗口
                content_window = tk.Toplevel(history_window)
                content_window.title(f"完整内容 - {values[1]}")
                content_window.geometry("900x600")
                
                # 创建带滚动条的文本区域
                text_frame = ttk.Frame(content_window)
                text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                text = tk.Text(
                    text_frame, 
                    wrap=tk.WORD, 
                    font=font,
                    undo=True
                )
                
                vsb = ttk.Scrollbar(text_frame, command=text.yview)
                text.configure(yscrollcommand=vsb.set)
                
                # 布局
                text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                vsb.pack(side=tk.RIGHT, fill=tk.Y)
                
                # 查找并显示完整内容
                for row in results:
                    if row[0] == values[0]:
                        full_content = row[2]
                        try:
                            if isinstance(full_content, bytes):
                                full_content = full_content.decode('utf-8', errors='replace')
                        except:
                            full_content = "内容编码错误"
                        
                        text.insert("1.0", full_content)
                        break
                
                text.config(state=tk.DISABLED)
            
            tree.bind("<Double-1>", on_double_click)
            
        except Exception as e:
            messagebox.showerror("错误", f"查看历史数据失败: {str(e)}")
            

    def _export_data(self):
        """导出数据为CSV文件"""
        try:
            def op(cursor):
                cursor.execute("SELECT DISTINCT base_url FROM pages ORDER BY created_at DESC")
                sites = [row[0] for row in cursor.fetchall()]
                
                if not sites:
                    messagebox.showinfo("提示", "没有可导出的数据")
                    return None
                    
                site = simpledialog.askstring(
                    "选择网站", 
                    "请输入要导出的网站URL:", 
                    initialvalue=sites[0] if sites else ""
                )
                if not site:
                    return None
                    
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".csv",
                    filetypes=[
                        ("CSV文件(UTF-8带BOM)", "*.csv"), 
                        ("CSV文件(UTF-8)", "*.csv"), 
                        ("所有文件", "*.*")
                    ],
                    initialfile=f"webcrawler_export_{datetime.now().strftime('%Y%m%d')}.csv"
                )
                if not file_path:
                    return None
                    
                cursor.execute('''
                    SELECT url, title, text_content 
                    FROM pages 
                    WHERE base_url=? AND status='completed' AND text_content IS NOT NULL
                    ORDER BY created_at DESC
                ''', (site,))
                return (site, file_path, cursor.fetchall())
            
            result = self.db._safe_db_operation(op)
            if not result:
                return
                
            site, file_path, results = result
            
            if not results:
                messagebox.showinfo("提示", f"没有找到 {site} 的文本数据")
                return
            
            # 根据选择的文件类型决定编码
            if "UTF-8带BOM" in file_path:
                encoding = 'utf-8-sig'  # 带BOM的UTF-8，适合Excel
            else:
                encoding = 'utf-8'  # 标准UTF-8
            
            # 准备CSV写入
            with open(file_path, 'w', newline='', encoding=encoding) as f:
                # 使用DictWriter更灵活处理字段
                fieldnames = ['URL', '标题', '文本内容']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # 写入BOM头(如果是utf-8-sig会自动添加)
                if encoding == 'utf-8-sig':
                    f.write('\ufeff')
                
                writer.writeheader()
                
                # 写入数据行
                for row in results:
                    url, title, content = row
                    
                    # 处理编码和清理文本
                    def clean_text(text):
                        if text is None:
                            return ""
                        if isinstance(text, bytes):
                            try:
                                text = text.decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    text = text.decode('gbk', errors='replace')
                                except:
                                    text = "[编码错误]"
                        # 替换换行和特殊字符
                        text = text.replace('\r\n', ' ').replace('\n', ' ')
                        text = text.replace('\ufeff', '')  # 移除可能的BOM字符
                        return text.strip()
                    
                    writer.writerow({
                        'URL': clean_text(url),
                        '标题': clean_text(title),
                        '文本内容': clean_text(content)
                    })
            
            messagebox.showinfo("成功", f"数据已成功导出到:\n{file_path}\n\n编码格式: {encoding}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出数据失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        # 设置UI缩放（针对高DPI显示器）
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    try:
        # 创建数据库连接
        db = ThreadSafeDB()
        
        # 创建GUI实例，传入root和db
        app = CrawlerGUI(root, db)
        root.mainloop()
    except Exception as e:
        logging.error(f"应用程序错误: {str(e)}")
        messagebox.showerror("错误", f"应用程序发生严重错误: {str(e)}")
    finally:
        if 'db' in locals():
            db.close_all()