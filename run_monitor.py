"""临时脚本：运行全站栏目监测并输出结果"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app import app
from monitor_core import MonitorEngine
from models import MonitorResult, UrlItem

app.app_context().push()

library_id = 3
engine = MonitorEngine(library_id=library_id, max_workers=8)
engine.load_items()
stats = engine.run()

print("=== 监测完成 ===")
print(f"总数: {stats['total']}")
print(f"成功: {stats['success']}")
print(f"失败: {stats['error']}")
print(f"逾期: {stats['overdue']}")
print(f"即将逾期: {stats['expiring']}")

# 输出逾期和即将逾期的栏目
overdue_items = MonitorResult.query.filter_by(library_id=library_id, is_overdue=True).order_by(MonitorResult.days_since_update.desc()).all()
expiring_items = MonitorResult.query.filter_by(library_id=library_id, is_expiring=True, is_overdue=False).order_by(MonitorResult.days_since_update.desc()).all()

print("\n=== 逾期栏目（前30条）===")
for i, r in enumerate(overdue_items[:30]):
    deadline = r.deadline_days or "?"
    print(f"{i+1}. [{r.column_category}] {r.column_name} | 最后更新: {r.last_max_date or '无'} | 已过期{r.days_since_update}天 (期限{deadline}天)")

print(f"\n...共 {len(overdue_items)} 个逾期栏目")

print("\n=== 即将逾期栏目（前30条）===")
for i, r in enumerate(expiring_items[:30]):
    deadline = r.deadline_days or "?"
    print(f"{i+1}. [{r.column_category}] {r.column_name} | 最后更新: {r.last_max_date or '无'} | 已过期{r.days_since_update}天 (期限{deadline}天)")

print(f"\n...共 {len(expiring_items)} 个即将逾期栏目")
