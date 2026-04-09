# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
os.chdir(r'C:\Users\Administrator\Desktop\ooa')

from datetime import datetime
import json

print('===== 早间简报 =====')
now = datetime.now()
print(f'时间: {now.strftime("%Y年%m月%d日 %H:%M")}')
print()

# 读取监测结果
print('【一、石城县政府网站监测】')
try:
    from monitor_core import MonitorCore
    mc = MonitorCore()
    items = mc.get_all_items()
    
    total = len(items)
    ok = sum(1 for i in items if i.status == 'ok')
    failed = sum(1 for i in items if i.status == 'failed')
    overdue = [i for i in items if i.days_since_update and i.days_since_update > 30]
    expiring = [i for i in items if i.days_since_update and 20 <= i.days_since_update <= 30]
    
    print(f'监测总数: {total} 个网址')
    print(f'  正常: {ok} 个')
    print(f'  失败: {failed} 个')
    print(f'  过期(>30天): {len(overdue)} 个')
    print(f'  即将到期(20-30天): {len(expiring)} 个')
    
    if overdue:
        print()
        print('  过期项目:')
        for item in overdue[:5]:
            print(f'    - {item.name}: {item.days_since_update}天未更新')
except Exception as e:
    print(f'监测读取失败: {e}')

print()

# 读取新闻简报
print('【二、24小时新闻热点】')
try:
    # 查找最新的新闻简报文件
    import glob
    files = glob.glob('briefings/news_*.md')
    if files:
        latest = max(files, key=os.path.getmtime)
        with open(latest, 'r', encoding='utf-8') as f:
            content = f.read()
            # 显示前1500字符
            print(content[:1500])
            if len(content) > 1500:
                print('...(更多内容省略)')
    else:
        print('暂无新闻简报')
except Exception as e:
    print(f'新闻简报读取失败: {e}')

print()

# 读取经济金融简报
print('【三、经济金融简报】')
try:
    files = glob.glob('briefings/finance_*.md')
    if files:
        latest = max(files, key=os.path.getmtime)
        with open(latest, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content[:1000])
    else:
        print('暂无金融简报')
except Exception as e:
    print(f'金融简报读取失败: {e}')

print()

# 读取AI简报
print('【四、AI学习简报】')
try:
    files = glob.glob('briefings/ai_*.md')
    if files:
        latest = max(files, key=os.path.getmtime)
        with open(latest, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content[:1000])
    else:
        print('暂无AI简报')
except Exception as e:
    print(f'AI简报读取失败: {e}')

print()
print('===== 简报结束 =====')
