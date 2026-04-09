#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量替换所有主题模板的旧式导航为折叠式侧边栏"""
import re, os

templates = [
    'templates/index_dark.html',
    'templates/index_fresh.html',
    'templates/index_anime.html',
    'templates/index_sidebar.html',
    'templates/index_tech.html',
]

sidebar_new = '                {{ sidebar("index") }}'
import_line = "{% from '_sidebar_nav.html' import sidebar %}\n"

for tpl in templates:
    if not os.path.exists(tpl):
        print(f'SKIP (not found): {tpl}')
        continue
    with open(tpl, 'r', encoding='utf-8') as f:
        content = f.read()

    if '_sidebar_nav.html' in content:
        print(f'ALREADY done: {tpl}')
        continue

    # 匹配 .brand div + nav.flex-column + .user-info div
    pat = re.compile(
        r'<div class="brand">.*?</div>\s*<nav class="nav flex-column">.*?</nav>\s*<div class="user-info">.*?</div>',
        re.DOTALL
    )
    m = pat.search(content)
    if m:
        new_content = pat.sub(sidebar_new, content)
        new_content = import_line + new_content
        with open(tpl, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'OK: {tpl}')
    else:
        print(f'PATTERN NOT MATCHED: {tpl}')
        idx = content.find('nav flex-column')
        print(f'  nav flex-column pos: {idx}')

print('Done.')
