# -*- coding: utf-8 -*-
"""从多个镜像源下载前端静态资源"""
import urllib.request
import os

BASE = os.path.join(os.path.dirname(__file__), 'static')

def download(url, dest, label=''):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        print(f"  [SKIP] {label or os.path.basename(dest)}")
        return True
    print(f"  Downloading {label or os.path.basename(dest)} ...", end=' ', flush=True)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(dest, 'wb') as f:
            f.write(data)
        print(f"OK ({len(data)//1024}KB)")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def try_mirrors(mirrors, dest, label=''):
    for url in mirrors:
        if download(url, dest, label):
            return True
    return False

# Font Awesome 和 marked.js 使用国内可访问的 bootcdn.cn / unpkg.com 镜像
tasks = [
    # Font Awesome 6.4.0 CSS
    (
        [
            'https://cdn.bootcdn.net/ajax/libs/font-awesome/6.4.0/css/all.min.css',
            'https://unpkg.com/@fortawesome/fontawesome-free@6.4.0/css/all.min.css',
        ],
        os.path.join(BASE, 'css', 'fontawesome.all.min.css'),
        'fontawesome.all.min.css'
    ),
    # Font Awesome Webfonts
    (
        [
            'https://cdn.bootcdn.net/ajax/libs/font-awesome/6.4.0/webfonts/fa-solid-900.woff2',
            'https://unpkg.com/@fortawesome/fontawesome-free@6.4.0/webfonts/fa-solid-900.woff2',
        ],
        os.path.join(BASE, 'webfonts', 'fa-solid-900.woff2'),
        'fa-solid-900.woff2'
    ),
    (
        [
            'https://cdn.bootcdn.net/ajax/libs/font-awesome/6.4.0/webfonts/fa-regular-400.woff2',
            'https://unpkg.com/@fortawesome/fontawesome-free@6.4.0/webfonts/fa-regular-400.woff2',
        ],
        os.path.join(BASE, 'webfonts', 'fa-regular-400.woff2'),
        'fa-regular-400.woff2'
    ),
    (
        [
            'https://cdn.bootcdn.net/ajax/libs/font-awesome/6.4.0/webfonts/fa-brands-400.woff2',
            'https://unpkg.com/@fortawesome/fontawesome-free@6.4.0/webfonts/fa-brands-400.woff2',
        ],
        os.path.join(BASE, 'webfonts', 'fa-brands-400.woff2'),
        'fa-brands-400.woff2'
    ),
    (
        [
            'https://cdn.bootcdn.net/ajax/libs/font-awesome/6.4.0/webfonts/fa-v4compatibility.woff2',
        ],
        os.path.join(BASE, 'webfonts', 'fa-v4compatibility.woff2'),
        'fa-v4compatibility.woff2'
    ),
    # marked.js
    (
        [
            'https://cdn.bootcdn.net/ajax/libs/marked/9.1.6/marked.min.js',
            'https://unpkg.com/marked@9.1.6/marked.min.js',
        ],
        os.path.join(BASE, 'js', 'marked.min.js'),
        'marked.min.js'
    ),
    # Chart.js
    (
        [
            'https://cdn.bootcdn.net/ajax/libs/Chart.js/4.4.0/chart.umd.min.js',
            'https://unpkg.com/chart.js@4.4.0/dist/chart.umd.min.js',
        ],
        os.path.join(BASE, 'js', 'chart.min.js'),
        'chart.min.js'
    ),
]

print("=== 下载剩余前端静态资源（使用国内镜像）===")
ok = 0
fail = 0
for mirrors, dest, label in tasks:
    if try_mirrors(mirrors, dest, label):
        ok += 1
    else:
        fail += 1

print(f"\n完成: {ok} 成功, {fail} 失败")

# 修复 Font Awesome CSS 中的字体路径
fa_css = os.path.join(BASE, 'css', 'fontawesome.all.min.css')
if os.path.exists(fa_css) and os.path.getsize(fa_css) > 1000:
    with open(fa_css, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = content.replace('../webfonts/', '/static/webfonts/')
    if new_content != content:
        with open(fa_css, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("已修复 Font Awesome CSS 字体路径 (../webfonts/ -> /static/webfonts/)")
    else:
        print("Font Awesome CSS 字体路径已正确")
