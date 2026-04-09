# -*- coding: utf-8 -*-
"""下载前端静态资源到本地，解决 CDN 加载慢的问题"""
import urllib.request
import os
import sys

BASE = os.path.join(os.path.dirname(__file__), 'static')

def download(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"  [SKIP] {os.path.basename(dest)} (already exists)")
        return True
    print(f"  Downloading {os.path.basename(dest)} ...", end=' ', flush=True)
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(dest, 'wb') as f:
            f.write(data)
        print(f"OK ({len(data)//1024}KB)")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

tasks = [
    # Bootstrap 5.3.0 CSS
    (
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
        os.path.join(BASE, 'css', 'bootstrap.min.css')
    ),
    # Bootstrap 5.3.0 JS Bundle
    (
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
        os.path.join(BASE, 'js', 'bootstrap.bundle.min.js')
    ),
    # Font Awesome 6.4.0 CSS
    (
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
        os.path.join(BASE, 'css', 'fontawesome.all.min.css')
    ),
    # Font Awesome Webfonts
    (
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2',
        os.path.join(BASE, 'webfonts', 'fa-solid-900.woff2')
    ),
    (
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2',
        os.path.join(BASE, 'webfonts', 'fa-regular-400.woff2')
    ),
    (
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2',
        os.path.join(BASE, 'webfonts', 'fa-brands-400.woff2')
    ),
    (
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.ttf',
        os.path.join(BASE, 'webfonts', 'fa-solid-900.ttf')
    ),
    (
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.ttf',
        os.path.join(BASE, 'webfonts', 'fa-regular-400.ttf')
    ),
    (
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.ttf',
        os.path.join(BASE, 'webfonts', 'fa-brands-400.ttf')
    ),
    # marked.js
    (
        'https://cdn.jsdelivr.net/npm/marked/marked.min.js',
        os.path.join(BASE, 'js', 'marked.min.js')
    ),
    # Chart.js (如果有用到)
    (
        'https://cdn.jsdelivr.net/npm/chart.js',
        os.path.join(BASE, 'js', 'chart.min.js')
    ),
]

print("=== 下载前端静态资源 ===")
ok = 0
fail = 0
for url, dest in tasks:
    if download(url, dest):
        ok += 1
    else:
        fail += 1

print(f"\n完成: {ok} 成功, {fail} 失败")

# 修复 Font Awesome CSS 中的字体路径
fa_css = os.path.join(BASE, 'css', 'fontawesome.all.min.css')
if os.path.exists(fa_css) and os.path.getsize(fa_css) > 1000:
    with open(fa_css, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换字体路径：../webfonts/ -> /static/webfonts/
    import re
    new_content = content.replace('../webfonts/', '/static/webfonts/')
    
    if new_content != content:
        with open(fa_css, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("已修复 Font Awesome CSS 字体路径")
    else:
        print("Font Awesome CSS 字体路径已正确")

print("\n=== 下载完成 ===")
