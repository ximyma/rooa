# -*- coding: utf-8 -*-
"""修复 app.py 中 ArchiveFile 的 is_active 查询"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 ArchiveFile.query.filter_by(is_active=True) 为正确的查询
content = content.replace(
    "ArchiveFile.query.filter_by(is_active=True)",
    "ArchiveFile.query.filter_by(status='active')"
)

# 替换 ArchiveFile.is_active == True
content = content.replace(
    "ArchiveFile.is_active == True",
    "ArchiveFile.status == 'active'"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('[OK] 已修复 ArchiveFile 查询')
