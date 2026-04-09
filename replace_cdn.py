# -*- coding: utf-8 -*-
"""批量替换所有模板中的 CDN 引用为本地路径"""
import os
import re

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')

# 替换规则：(旧字符串, 新字符串)
REPLACEMENTS = [
    # Bootstrap CSS
    (
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
        '/static/css/bootstrap.min.css'
    ),
    # Bootstrap JS
    (
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
        '/static/js/bootstrap.bundle.min.js'
    ),
    # Font Awesome from cdnjs
    (
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
        '/static/css/fontawesome.all.min.css'
    ),
    # marked.js
    (
        'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
        '/static/js/marked.min.js'
    ),
    # github-markdown-css（用本地版本替代，如没有本地版本则用内联样式）
    (
        'https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css',
        '/static/css/github-markdown.min.css'
    ),
]

modified = []
for root, dirs, files in os.walk(TEMPLATES_DIR):
    for fname in files:
        if not fname.endswith('.html'):
            continue
        fpath = os.path.join(root, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        for old, new in REPLACEMENTS:
            new_content = new_content.replace(old, new)
        
        if new_content != content:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            rel = os.path.relpath(fpath, TEMPLATES_DIR)
            modified.append(rel)
            print(f"  Updated: {rel}")

print(f"\n共更新 {len(modified)} 个文件")
