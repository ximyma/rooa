# -*- coding: utf-8 -*-
"""修复模板中的 url_for 调用 - 完整版"""
import os
import re

# 完整映射表
url_map = {
    'archive.index': 'archive_index',
    'archive.fonds_list': 'archive_fonds_list',
    'archive.file_list': 'archive_file_list',
    'archive.search': 'archive_search',
    'archive.batch_upload': 'archive_batch_upload',
    'archive.task_list': 'archive_task_list',
    'archive.my_borrows': 'archive_my_borrows',
    'archive.statistics': 'archive_statistics',
    'archive.file_detail': 'archive_file_detail',
    'archive.file_upload': 'archive_batch_upload',  # 没有单独的 file_upload，用 batch_upload
    'archive.borrow_file': 'archive_file_detail',   # 借阅功能在详情页
    'archive.digitization_tasks': 'archive_task_list',
    'archive.catalog': 'archive_fonds_list',
    'archive.fonds_create': 'archive_fonds_list',
    'archive.statistics_export': 'archive_statistics',
}

template_dir = r'C:\Users\Administrator\Desktop\ooa\templates\archive'

for filename in os.listdir(template_dir):
    if filename.endswith('.html'):
        filepath = os.path.join(template_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        for old, new in url_map.items():
            # 单引号版本
            pattern1 = f"url_for('{old}'"
            if pattern1 in content:
                content = content.replace(pattern1, f"url_for('{new}'")
                modified = True
            # 双引号版本
            pattern2 = f'url_for("{old}"'
            if pattern2 in content:
                content = content.replace(pattern2, f"url_for('{new}'")
                modified = True
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f'[OK] {filename}')
        else:
            print(f'[--] {filename} (no changes)')

print('Done!')
