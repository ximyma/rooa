# -*- coding: utf-8 -*-
import requests, re

s = requests.Session()
r = s.get('http://127.0.0.1:5000/login')
token = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
csrf = token.group(1) if token else ''
r2 = s.post('http://127.0.0.1:5000/login', data={'username':'admin','password':'admin123','csrf_token':csrf})
print("Login:", r2.url)

r3 = s.get('http://127.0.0.1:5000/')
cdn_refs = re.findall(r'cdn\.jsdelivr|cdnjs\.cloudflare|unpkg\.com|bootcdn', r3.text)
local_refs = re.findall(r'/static/css/bootstrap|/static/js/bootstrap|/static/css/fontawesome', r3.text)
print("CDN refs still in HTML:", cdn_refs if cdn_refs else "None (GOOD!)")
print("Local refs in HTML:", local_refs)
print("Page OK:", r3.status_code == 200)
