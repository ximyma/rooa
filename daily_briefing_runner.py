import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import subprocess
from datetime import datetime

# 设置工作目录
os.chdir(r'C:\Users\Administrator\Desktop\ooa')

# 创建日志目录
os.makedirs('logs', exist_ok=True)

date_str = datetime.now().strftime('%Y%m%d')
log_file = f'logs/daily_briefing_{date_str}.log'

def log(msg):
    print(msg)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {msg}\n')

log('===== 开始执行每日简报生成任务 =====')
log(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
log('')

# 1. 石城县政府网站监测
log('[1/4] 执行石城县政府网站监测...')
try:
    result = subprocess.run(['python', 'run_monitor.py'], capture_output=True, encoding='utf-8', errors='ignore', timeout=600)
    log(f'监测完成，返回码: {result.returncode}')
    if result.stdout:
        log(result.stdout[:500])
except Exception as e:
    log(f'监测出错: {e}')

log('')

# 2. 24小时新闻热点简报
log('[2/4] 生成24小时新闻热点简报...')
try:
    result = subprocess.run(['python', 'run_news_briefing.py'], capture_output=True, encoding='utf-8', errors='ignore', timeout=300)
    log(f'新闻简报生成完成，返回码: {result.returncode}')
    if result.stdout:
        log(result.stdout[:500])
except Exception as e:
    log(f'新闻简报出错: {e}')

log('')

# 3. 经济金融简报
log('[3/4] 生成经济金融简报...')
try:
    result = subprocess.run(['python', 'run_finance_briefing.py'], capture_output=True, encoding='utf-8', errors='ignore', timeout=300)
    log(f'金融简报生成完成，返回码: {result.returncode}')
    if result.stdout:
        log(result.stdout[:500])
except Exception as e:
    log(f'金融简报出错: {e}')

log('')

# 4. AI学习简报
log('[4/4] 生成AI学习简报...')
try:
    result = subprocess.run(['python', 'run_ai_briefing.py'], capture_output=True, encoding='utf-8', errors='ignore', timeout=300)
    log(f'AI简报生成完成，返回码: {result.returncode}')
    if result.stdout:
        log(result.stdout[:500])
except Exception as e:
    log(f'AI简报出错: {e}')

log('')
log('===== 所有任务执行完成 =====')
log(f'时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
log(f'日志文件: {log_file}')
