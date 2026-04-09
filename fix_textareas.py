#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量给专报相关页面的textarea添加md-editor class"""
import os

fixes = [
    ('templates/special_report/receiver/edit_info.html',
     'name="content" class="form-control" rows="10" required>',
     'name="content" class="form-control md-editor" rows="10" data-height="380" required>'),
    ('templates/special_report/receiver/return_report.html',
     'name="feedback" class="form-control" rows="5" required',
     'name="feedback" class="form-control md-editor" rows="5" data-height="220" required'),
    ('templates/special_report/receiver/reject_submission.html',
     'name="feedback" class="form-control" rows="5"',
     'name="feedback" class="form-control md-editor" rows="5" data-height="220"'),
    ('templates/special_report/receiver/create_task.html',
     'name="description" class="form-control" rows="5" required>',
     'name="description" class="form-control md-editor" rows="5" data-height="220" required>'),
    ('templates/special_report/receiver/refine_report.html',
     'name="reason" class="form-control" rows="5" required>',
     'name="reason" class="form-control md-editor" rows="5" data-height="220" required>'),
]

for path, old, new in fixes:
    if not os.path.exists(path):
        print(f'SKIP (not found): {path}')
        continue
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    if 'md-editor' in c:
        print(f'ALREADY done: {path}')
        continue
    if old in c:
        c2 = c.replace(old, new, 1)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(c2)
        print(f'OK: {path}')
    else:
        print(f'NOT FOUND pattern in: {path}')

print('Done.')
