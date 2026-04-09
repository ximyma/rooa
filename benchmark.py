# -*- coding: utf-8 -*-
import time
import requests
import re

session = requests.Session()

# 先获取登录页面
r = session.get('http://127.0.0.1:5000/login')
token = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
csrf = token.group(1) if token else ''

# 登录
r = session.post('http://127.0.0.1:5000/login', data={
    'username': 'admin',
    'password': 'admin123',
    'csrf_token': csrf
})
print("Login status:", r.status_code, r.url)

# 测试各页面速度
urls = [
    ('/', '主页(首次)'),
    ('/', '主页(二次/缓存)'),
    ('/briefing', '简报首页'),
    ('/briefing/sources', '简报数据源'),
    ('/briefing/keywords', '简报关键词'),
    ('/briefing/history', '简报历史'),
    ('/qa/ai_chat', 'AI对话'),
    ('/knowledge/personal', '个人知识库'),
    ('/special_report/reporter/report_list', '信息上报列表'),
]

results = []
for url, label in urls:
    t1 = time.time()
    r = session.get('http://127.0.0.1:5000' + url)
    elapsed = time.time() - t1
    results.append((label, elapsed, r.status_code))
    print(f"{label:20s}: {elapsed:.3f}s  [{r.status_code}]")

print("\n--- 慢页面 (>0.1s) ---")
for label, elapsed, code in results:
    if elapsed > 0.1:
        print(f"  {label}: {elapsed:.3f}s")
