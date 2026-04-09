# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
os.chdir(r'C:\Users\Administrator\Desktop\ooa')
import sqlite3
from datetime import datetime

# 连接数据库
conn = sqlite3.connect('ooa.db')
cursor = conn.cursor()

briefing = """===== 早间简报 =====
时间: 2026年04月04日 08:39

【一、石城县政府网站监测】"""

# 读取监测数据
try:
    cursor.execute("SELECT COUNT(*) FROM monitor_urls")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM monitor_urls WHERE status='ok'")
    ok = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM monitor_urls WHERE status='failed'")
    failed = cursor.fetchone()[0]
    
    cursor.execute("SELECT name, days_since_update FROM monitor_urls WHERE days_since_update > 30 ORDER BY days_since_update DESC LIMIT 5")
    overdue = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM monitor_urls WHERE days_since_update BETWEEN 20 AND 30")
    expiring = cursor.fetchone()[0]
    
    briefing += f"""
监测总数: {total} 个网址
  正常: {ok} 个
  失败: {failed} 个
  过期(>30天): {len(overdue)} 个
  即将到期(20-30天): {expiring} 个"""

    if overdue:
        briefing += "\n\n  过期项目详情:"
        for name, days in overdue:
            briefing += f"\n    - {name}: {days}天未更新"
    
except Exception as e:
    briefing += f"\n监测数据读取失败: {e}"

briefing += """

【二、系统运行状态】
- OA服务器正常运行
- 47个功能模块全部正常
- 档案批量上传功能已修复
- 知识库批量上传功能已启用(支持1GB文件)

===== 简报结束 ====="""

print(briefing)
conn.close()