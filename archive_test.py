# -*- coding: utf-8 -*-
"""扩展档案页面测试"""
import traceback
from app import app, db

results = []

with app.test_client() as c:
    with app.app_context():
        r = c.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        
        # 档案所有页面测试
        pages = [
            ('/archive/', '档案首页'),
            ('/archive/fonds', '全宗列表'),
            ('/archive/files', '档案文件列表'),
            ('/archive/search', '档案搜索'),
            ('/archive/statistics', '档案统计'),
            ('/archive/my_borrows', '我的借阅'),
            ('/archive/tasks', '批量任务'),
            ('/archive/batch_upload', '批量上传'),
            ('/archive/borrow', '借阅管理'),
            ('/archive/borrow_manage', '借阅审批'),
            ('/archive/digitization/tasks', '数字化任务'),
            ('/archive/quality', '质检仪表板'),
            ('/archive/digitize_manage', '数字化管理'),
            ('/archive/notifications', '消息通知'),
        ]
        
        for url, name in pages:
            try:
                r = c.get(url, follow_redirects=True)
                status = r.status_code
                if status >= 400:
                    body = r.data.decode('utf-8', errors='replace')
                    import re
                    errs = re.findall(r'(?:BuildError|Error|Exception|错误)[^\n<]{0,200}', body)
                    error_hint = ' | '.join(errs[:2]) if errs else body[:200]
                    results.append(f"[FAIL-{status}] {url} ({name}): {error_hint[:250]}")
                else:
                    results.append(f"[OK-{status}] {url} ({name})")
            except Exception as e:
                results.append(f"[EXC] {url} ({name}): {e}")
                traceback.print_exc()

with open('archive_test.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

ok = sum(1 for r in results if r.startswith('[OK'))
fail = sum(1 for r in results if r.startswith('[FAIL') or r.startswith('[EXC'))
print(f"完成: {ok} OK, {fail} FAIL")
