import sys
sys.stdout.reconfigure(encoding="utf-8")
import os
import json

os.chdir(r"C:\Users\Administrator\Desktop\ooa")

print("=== OOA系统功能分析 ===\n")

# 1. 分析models
print("【1. 数据模型分析】")
with open("models.py", "r", encoding="utf-8") as f:
    models_content = f.read()
    # 提取所有类名
    import re
    models = re.findall(r'class (\w+)\(', models_content)
    print(f"数据模型总数: {len(models)}")
    for m in sorted(models):
        print(f"  - {m}")

print("\n【2. API端点分析】")
endpoints_dir = "app/api/endpoints"
if os.path.exists(endpoints_dir):
    api_files = [f for f in os.listdir(endpoints_dir) if f.endswith(".py")]
    print(f"API模块数: {len(api_files)}")
    for f in sorted(api_files):
        mod_name = f[:-3]
        print(f"  - {mod_name}")

print("\n【3. 前端视图分析】")
views_dir = "app/templates/views"
if os.path.exists(views_dir):
    vue_files = [f for f in os.listdir(views_dir) if f.endswith(".vue")]
    print(f"Vue组件数: {len(vue_files)}")
    for f in sorted(vue_files):
        print(f"  - {f}")

print("\n【4. 工具模块分析】")
utils_dir = "utils"
if os.path.exists(utils_dir):
    utils_files = [f for f in os.listdir(utils_dir) if f.endswith(".py")]
    print(f"工具模块数: {len(utils_files)}")
    for f in sorted(utils_files):
        print(f"  - {f}")

print("\n【5. 核心功能分类】")
categories = {
    "公文管理": ["doc", "document", "dispatch", "公文", "发文", "收文"],
    "人力资源": ["hr", "staff", "employee", "人事", "考勤", "培训", "合同"],
    "行政管理": ["meeting", "vehicle", "car", "会议室", "车辆"],
    "财务管理": ["salary", "finance", "payroll", "薪资", "报销"],
    "知识管理": ["knowledge", "wiki", "文档", "知识库"],
    "简报系统": ["briefing", "monitor", "report", "简报", "监测"],
    "系统管理": ["auth", "user", "role", "config", "系统"],
}

with open("models.py", "r", encoding="utf-8") as f:
    content = f.read()
    for cat, keywords in categories.items():
        matches = [m for m in re.findall(r'class (\w+)\(', content) 
                   if any(k.lower() in m.lower() for k in keywords)]
        if matches:
            print(f"  {cat}: {len(matches)}个模型")
            for m in matches:
                print(f"    - {m}")

print("\n【6. 简报数据统计】")
try:
    from app import app, db
    from models import Briefing, BriefingSource, MonitorResult
    
    with app.app_context():
        b_count = Briefing.query.count()
        s_count = BriefingSource.query.count()
        m_count = MonitorResult.query.count()
        print(f"  简报记录: {b_count}条")
        print(f"  数据源: {s_count}个")
        print(f"  监测记录: {m_count}条")
except Exception as e:
    print(f"  数据库查询失败: {e}")

print("\n分析完成！")
