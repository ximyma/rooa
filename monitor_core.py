"""
栏目监测引擎 - 网址库监测 + 逾期标记
"""
import threading
import time
import random
import re
import requests
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

_print_lock = threading.Lock()

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
]


def _log_msg(library_id, level, message):
    """写日志到数据库"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    msg = f"[{timestamp}] {message}"
    with _print_lock:
        print(msg)
    try:
        from app import db
        from models import MonitorLog
        log = MonitorLog(library_id=library_id, level=level, message=message)
        db.session.add(log)
        db.session.commit()
    except Exception:
        pass


class MonitorEngine:
    """栏目监测引擎"""

    def __init__(self, library_id, max_workers=8, expiring_days=8):
        self.library_id = library_id
        self.max_workers = max_workers
        self.expiring_days = expiring_days
        self.items = []
        self.results = []
        self.stop_flag = threading.Event()
        self.stats = {'total': 0, 'success': 0, 'error': 0, 'overdue': 0, 'expiring': 0}

    def load_items(self):
        """加载网址库内容（转为纯字典，避免跨线程session问题）"""
        try:
            from models import UrlItem
            rows = UrlItem.query.filter_by(library_id=self.library_id, is_active=True).all()
            # 转为纯字典：避免 ORM 对象跨线程 session 错误
            self.items = [
                {
                    'id': r.id,
                    'url': r.url,
                    'column_name': r.column_name,
                    'column_category': r.column_category,
                    'update_deadline': r.update_deadline,
                    'deadline_days': r.deadline_days,
                    'serial_no': r.serial_no,
                    'website_name': r.website_name,
                }
                for r in rows
            ]
            _log_msg(self.library_id, 'info', f"已加载 {len(self.items)} 个网址")
            return len(self.items)
        except Exception as e:
            _log_msg(self.library_id, 'error', f"加载网址失败: {e}")
            return 0

    def _fetch_url(self, item):
        """获取单个URL的最大日期"""
        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }

        max_retries = 3
        for retry in range(max_retries):
            try:
                resp = requests.get(item['url'], headers=headers, timeout=10)
                resp.raise_for_status()
                
                # 处理编码问题
                raw_content = resp.content
                encoding = resp.encoding
                if encoding == 'ISO-8859-1' or not encoding:
                    try:
                        text = raw_content.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            text = raw_content.decode('gbk')
                        except:
                            text = raw_content.decode('utf-8', errors='replace')
                else:
                    text = raw_content.decode(encoding, errors='replace')
                
                soup = BeautifulSoup(text, 'html.parser')
                
                # 严格限制在 body 区域内提取日期，排除 header/nav 等导航区域
                body = soup.find('body')
                if not body:
                    all_text = soup.get_text()
                else:
                    # 移除导航、页眉、页脚等可能包含干扰日期的区域
                    for noise in body.find_all(['header', 'nav', 'footer', '.header', '.nav', '.footer', '.menu', '.sidebar']):
                        noise.decompose()
                    all_text = body.get_text()

                # 提取所有日期（更全面的模式）
                date_patterns = [
                    (r'\d{4}-\d{2}-\d{2}', '-'),           # 2024-01-01
                    (r'\d{4}/\d{2}/\d{2}', '/'),           # 2024/01/01
                    (r'\d{4}年\d{1,2}月\d{1,2}日', 'cn'),   # 2024年1月1日
                    (r'\d{4}\.\d{2}\.\d{2}', '.'),         # 2024.01.01
                ]

                all_dates = []
                for pat, fmt in date_patterns:
                    found = re.findall(pat, all_text)
                    for d in found:
                        try:
                            if fmt == '-':
                                dt = pd.to_datetime(d, format='%Y-%m-%d', errors='coerce')
                            elif fmt == '/':
                                dt = pd.to_datetime(d, format='%Y/%m/%d', errors='coerce')
                            elif fmt == 'cn':
                                dt = pd.to_datetime(d.replace('年', '-').replace('月', '-').replace('日', ''), errors='coerce')
                            elif fmt == '.':
                                dt = pd.to_datetime(d, format='%Y.%m.%d', errors='coerce')
                            
                            if dt and not pd.isnull(dt):
                                dt_date = dt.to_pydatetime().date()
                                # 过滤掉未来日期和太旧的日期（超过2年）
                                today = date.today()
                                if today - timedelta(days=730) <= dt_date <= today:
                                    all_dates.append(dt_date)
                        except:
                            continue

                max_date = max(all_dates) if all_dates else None
                return item, max_date, None

            except requests.exceptions.RequestException as e:
                if retry < max_retries - 1:
                    time.sleep(2 ** retry)  # 指数退避
                    continue
                return item, None, str(e)
            except Exception as e:
                return item, None, str(e)

    def _calculate_overdue(self, item, max_date):
        """计算是否逾期"""
        now = date.today()
        deadline_days = item.get('deadline_days')
        if max_date is None:
            days = -1
            is_overdue = True
            is_expiring = False
        else:
            days = (now - max_date).days
            is_overdue = deadline_days and days > deadline_days
            # 即将逾期：距离逾期天数 <= expiring_days
            is_expiring = deadline_days and (deadline_days - self.expiring_days) <= days <= deadline_days
        return days, is_overdue, is_expiring

    def run(self, progress_callback=None):
        """执行监测"""
        from app import db  # 导入到局部，避免跨 try/except scope 问题
        self.stop_flag.clear()
        self.stats = {'total': len(self.items), 'success': 0, 'error': 0, 'overdue': 0, 'expiring': 0}

        _log_msg(self.library_id, 'info', f"[START] Monitoring {self.stats['total']} URLs...")

        try:
            from models import MonitorResult, UrlLibrary
            # 清空旧结果
            MonitorResult.query.filter_by(library_id=self.library_id).delete()

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self._fetch_url, item): item for item in self.items}

                completed = 0
                for future in as_completed(futures):
                    if self.stop_flag.is_set():
                        break

                    item, max_date, error = future.result()
                    days, is_overdue, is_expiring = self._calculate_overdue(item, max_date)

                    # 保存结果
                    result = MonitorResult(
                        library_id=self.library_id,
                        url_item_id=item['id'],
                        url=item['url'],
                        column_name=item['column_name'],
                        column_category=item['column_category'],
                        update_deadline=item['update_deadline'],
                        deadline_days=item['deadline_days'],
                        last_max_date=max_date,
                        days_since_update=days,
                        is_overdue=is_overdue,
                        is_expiring=is_expiring,
                        status='error' if error else 'completed',
                        error_msg=error,
                    )
                    db.session.add(result)

                    col_name = (item.get('column_name') or '')[:20]
                    if error:
                        self.stats['error'] += 1
                        _log_msg(self.library_id, 'warning', f"FAIL {col_name}: {str(error)[:30]}")
                    else:
                        self.stats['success'] += 1
                        status_icon = "OVERDUE" if is_overdue else ("EXPIRING" if is_expiring else "OK")
                        _log_msg(self.library_id, 'info',
                            f"[{status_icon}] {col_name}: {max_date} ({days}days)" if max_date
                            else f"[NO-DATE] {col_name}")

                    if is_overdue:
                        self.stats['overdue'] += 1
                    if is_expiring:
                        self.stats['expiring'] += 1

                    completed += 1
                    if progress_callback:
                        progress_callback(completed, self.stats['total'])

            db.session.commit()

            # 更新库的上次监测时间
            lib = UrlLibrary.query.get(self.library_id)
            if lib:
                lib.last_monitor_at = datetime.now()
                db.session.commit()

            _log_msg(self.library_id, 'info',
                f"[OK] Monitoring complete! Success:{self.stats['success']} Errors:{self.stats['error']} "
                f"Overdue:{self.stats['overdue']} Expiring:{self.stats['expiring']}")

        except Exception as e:
            _log_msg(self.library_id, 'error', f"监测过程出错: {e}")
            db.session.rollback()

        return self.stats

    def stop(self):
        """停止监测"""
        self.stop_flag.set()
        _log_msg(self.library_id, 'info', "[STOP] Monitoring stopped")


# 全局实例
_active_monitors = {}


def get_monitor(library_id, expiring_days=8):
    if library_id not in _active_monitors:
        _active_monitors[library_id] = MonitorEngine(library_id, expiring_days=expiring_days)
    return _active_monitors[library_id]
