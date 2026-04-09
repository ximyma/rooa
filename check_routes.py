# -*- coding: utf-8 -*-
import re

content = open('archive_routes.py', encoding='utf-8').read()
routes = re.findall(r"@archive_bp\.route\('([^']+)'", content)
print("当前路由:")
for r in sorted(set(routes)):
    print(f"  {r}")

# 检查需要的路由
needed = [
    '/', '/index', '/fonds', '/files', '/file_list', '/search',
    '/batch_upload', '/tasks', '/task_list', '/my_borrows', '/statistics'
]

print("\n导航菜单需要的路由检查:")
for n in needed:
    found = any(n in r for r in routes)
    status = "✓" if found else "✗"
    print(f"  {status} {n}")
