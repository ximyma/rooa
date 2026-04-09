# -*- coding: utf-8 -*-
"""添加批量上传页面路由"""

new_route = '''
@archive_bp.route('/batch_upload')
@login_required
def batch_upload():
    """批量上传页面"""
    ArchiveFonds, _, _, _, _, _ = get_models()
    fonds_list = ArchiveFonds.query.filter_by(is_active=True).all()
    return render_template('archive/batch_upload.html', fonds_list=fonds_list)
'''

with open('archive_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否已存在
if 'def batch_upload():' not in content:
    # 找到第一个 @archive_bp.route 的位置，在它之前插入
    first_route_idx = content.find("@archive_bp.route")
    if first_route_idx > 0:
        content = content[:first_route_idx] + new_route + '\n' + content[first_route_idx:]
        with open('archive_routes.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('[OK] 批量上传页面路由已添加')
    else:
        print('[ERROR] 未找到插入位置')
else:
    print('[INFO] 批量上传页面路由已存在')
