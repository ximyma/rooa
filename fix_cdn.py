# -*- coding: utf-8 -*-
import urllib.request, os

BASE = os.path.join(os.path.dirname(__file__), 'static')

def download(url, dest, label=''):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest) and os.path.getsize(dest) > 500:
        print(f"  [SKIP] {label}")
        return True
    print(f"  Downloading {label} ...", end=' ', flush=True)
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

# 下载 github-markdown CSS
mirrors = [
    'https://cdn.bootcdn.net/ajax/libs/github-markdown-css/5.2.0/github-markdown.min.css',
    'https://unpkg.com/github-markdown-css@5.2.0/github-markdown.min.css',
]
dest = os.path.join(BASE, 'css', 'github-markdown.min.css')
for url in mirrors:
    if download(url, dest, 'github-markdown.min.css'):
        break

# 运行批量替换
exec(open(os.path.join(os.path.dirname(__file__), 'replace_cdn.py'), encoding='utf-8').read())
