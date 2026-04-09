import os
templates = ['index_default.html','index_dark.html','index_fresh.html','index_anime.html','index_sidebar.html','index_tech.html']
keywords = ['doc_inbox','doc_outbox','doc_compose','doc_pending','doc_archive_list']
print("=" * 80)
print(f"{'模板文件':<25} {'收件箱':>6} {'发件箱':>6} {'起草':>6} {'待审批':>6} {'归档库':>6}")
print("=" * 80)
for tpl in templates:
    path = os.path.join('templates', tpl)
    with open(path, encoding='utf-8') as f:
        content = f.read()
    vals = ['Y' if k in content else 'N' for k in keywords]
    print(f"{tpl:<25} {vals[0]:>6} {vals[1]:>6} {vals[2]:>6} {vals[3]:>6} {vals[4]:>6}")
print("=" * 80)
