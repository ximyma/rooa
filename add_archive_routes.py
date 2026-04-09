# -*- coding: utf-8 -*-
"""添加档案系统完整路由到 app.py"""

routes_code = '''
# ============================================================
#  档案管理模块 - 完整路由
# ============================================================

@app.route('/archive/fonds')
@login_required
def archive_fonds_list():
    """全宗管理页面"""
    try:
        from archive_models import ArchiveFonds
        fonds = ArchiveFonds.query.filter_by(is_active=True).order_by(ArchiveFonds.fonds_code).all()
        return render_template('archive/fonds_list.html', fonds=fonds)
    except Exception as e:
        flash(f'加载失败: {e}', 'danger')
        return render_template('archive/fonds_list.html', fonds=[])


@app.route('/archive/files')
@login_required
def archive_file_list():
    """档案列表页面"""
    try:
        from archive_models import ArchiveFonds, ArchiveFile
        from sqlalchemy import func
        
        keyword = request.args.get('keyword', '')
        fonds_id = request.args.get('fonds_id', type=int)
        retention = request.args.get('retention', '')
        year = request.args.get('year', type=int)
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        query = ArchiveFile.query.filter_by(is_active=True)
        
        if keyword:
            query = query.filter(ArchiveFile.title.contains(keyword))
        if fonds_id:
            query = query.filter_by(fonds_id=fonds_id)
        if retention:
            query = query.filter_by(retention_period=retention)
        if year:
            query = query.filter(func.strftime('%Y', ArchiveFile.archive_date) == str(year))
        
        pagination = query.order_by(ArchiveFile.created_at.desc()).paginate(page=page, per_page=per_page)
        
        stats = {
            'digitized': ArchiveFile.query.filter_by(is_active=True, is_digitized=True).count(),
            'permanent': ArchiveFile.query.filter_by(is_active=True, retention_period='永久').count(),
        }
        
        fonds_list = ArchiveFonds.query.filter_by(is_active=True).all()
        years = [y[0] for y in db.session.query(func.strftime('%Y', ArchiveFile.archive_date)).distinct().all() if y[0]]
        
        return render_template('archive/file_list.html',
                             files=pagination.items,
                             pagination=pagination,
                             stats=stats,
                             fonds_list=fonds_list,
                             years=sorted(set(years), reverse=True))
    except Exception as e:
        flash(f'加载失败: {e}', 'danger')
        return render_template('archive/file_list.html', files=[], pagination=None, stats={}, fonds_list=[], years=[])


@app.route('/archive/search')
@login_required
def archive_search():
    """档案检索页面"""
    try:
        from archive_models import ArchiveFonds, ArchiveFile
        from sqlalchemy import or_, func
        
        query_text = request.args.get('q', '')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        results = []
        total = 0
        
        if query_text:
            query = ArchiveFile.query.filter(
                ArchiveFile.is_active == True,
                or_(
                    ArchiveFile.title.contains(query_text),
                    ArchiveFile.content.contains(query_text),
                    ArchiveFile.keywords.contains(query_text)
                )
            )
            total = query.count()
            results = query.order_by(ArchiveFile.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()
        
        filters = {
            'fonds_id': request.args.get('fonds_id', ''),
            'retention': request.args.get('retention', ''),
            'year': request.args.get('year', ''),
        }
        
        fonds_list = ArchiveFonds.query.filter_by(is_active=True).all()
        years = [y[0] for y in db.session.query(func.strftime('%Y', ArchiveFile.archive_date)).distinct().all() if y[0]]
        
        return render_template('archive/search.html',
                             query=query_text,
                             results=results,
                             total=total,
                             page=page,
                             pages=(total // per_page) + 1 if total > 0 else 0,
                             filters=filters,
                             fonds_list=fonds_list,
                             years=sorted(set(years), reverse=True))
    except Exception as e:
        flash(f'搜索失败: {e}', 'danger')
        return render_template('archive/search.html', query='', results=[], total=0, page=1, pages=0, filters={}, fonds_list=[], years=[])


@app.route('/archive/file/<int:file_id>')
@login_required
def archive_file_detail(file_id):
    """档案详情页面"""
    try:
        from archive_models import ArchiveFile, ArchiveBorrow
        file = ArchiveFile.query.get_or_404(file_id)
        borrow_history = ArchiveBorrow.query.filter_by(file_id=file_id).order_by(ArchiveBorrow.created_at.desc()).limit(5).all()
        return render_template('archive/file_detail.html', file=file, borrow_history=borrow_history, related_files=[])
    except Exception as e:
        flash(f'加载失败: {e}', 'danger')
        return redirect(url_for('archive_file_list'))


@app.route('/archive/tasks')
@login_required
def archive_task_list():
    """任务管理页面"""
    try:
        from archive_models import ArchiveDigitizationTask
        tasks = ArchiveDigitizationTask.query.order_by(ArchiveDigitizationTask.created_at.desc()).all()
        return render_template('archive/task_list.html', tasks=tasks)
    except Exception as e:
        flash(f'加载失败: {e}', 'danger')
        return render_template('archive/task_list.html', tasks=[])


@app.route('/archive/my_borrows')
@login_required
def archive_my_borrows():
    """我的借阅页面"""
    try:
        from archive_models import ArchiveBorrow
        status = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        query = ArchiveBorrow.query.filter_by(user_id=current_user.id)
        
        if status == 'active':
            query = query.filter_by(status='borrowed')
        elif status == 'returned':
            query = query.filter_by(status='returned')
        
        pagination = query.order_by(ArchiveBorrow.created_at.desc()).paginate(page=page, per_page=per_page)
        
        stats = {
            'total': ArchiveBorrow.query.filter_by(user_id=current_user.id).count(),
            'active': ArchiveBorrow.query.filter_by(user_id=current_user.id, status='borrowed').count(),
            'returned': ArchiveBorrow.query.filter_by(user_id=current_user.id, status='returned').count(),
            'overdue': 0
        }
        
        return render_template('archive/my_borrows.html', borrows=pagination.items, pagination=pagination, status=status, stats=stats)
    except Exception as e:
        flash(f'加载失败: {e}', 'danger')
        return render_template('archive/my_borrows.html', borrows=[], pagination=None, status='all', stats={})


@app.route('/archive/statistics')
@login_required
def archive_statistics():
    """统计报表页面"""
    try:
        from archive_models import ArchiveFonds, ArchiveFile, ArchiveBorrow
        from sqlalchemy import func
        
        stats = {
            'total_files': ArchiveFile.query.filter_by(is_active=True).count(),
            'digitized': ArchiveFile.query.filter_by(is_active=True, is_digitized=True).count(),
            'total_fonds': ArchiveFonds.query.filter_by(is_active=True).count(),
            'total_borrows': ArchiveBorrow.query.count()
        }
        
        retention_data = {
            'permanent': ArchiveFile.query.filter_by(is_active=True, retention_period='永久').count(),
            'y30': ArchiveFile.query.filter_by(is_active=True, retention_period='30年').count(),
            'y10': ArchiveFile.query.filter_by(is_active=True, retention_period='10年').count(),
            'unknown': ArchiveFile.query.filter_by(is_active=True, retention_period=None).count()
        }
        
        year_data = db.session.query(
            func.strftime('%Y', ArchiveFile.archive_date).label('year'),
            func.count().label('count')
        ).filter(ArchiveFile.is_active == True).group_by('year').order_by('year').all()
        
        type_data = db.session.query(
            ArchiveFile.file_type,
            func.count().label('count')
        ).filter(ArchiveFile.is_active == True).group_by(ArchiveFile.file_type).all()
        
        security_data = {
            'public': ArchiveFile.query.filter_by(is_active=True, security_level='公开').count(),
            'internal': ArchiveFile.query.filter_by(is_active=True, security_level='内部').count(),
            'secret': ArchiveFile.query.filter_by(is_active=True, security_level='秘密').count(),
            'confidential': ArchiveFile.query.filter_by(is_active=True, security_level='机密').count()
        }
        
        fonds_stats = db.session.query(
            ArchiveFonds.id,
            ArchiveFonds.fonds_code,
            ArchiveFonds.fonds_name,
            func.count(ArchiveFile.id).label('file_count')
        ).outerjoin(ArchiveFile).filter(ArchiveFonds.is_active == True).group_by(ArchiveFonds.id).all()
        
        return render_template('archive/statistics.html',
                             stats=stats,
                             retention_data=retention_data,
                             year_data=[{'year': y.year, 'count': y.count} for y in year_data if y.year],
                             type_data=[{'type': t.file_type or '未知', 'count': t.count} for t in type_data],
                             security_data=security_data,
                             fonds_stats=fonds_stats,
                             hot_files=[],
                             active_users=[])
    except Exception as e:
        flash(f'加载失败: {e}', 'danger')
        return render_template('archive/statistics.html', stats={}, retention_data={}, year_data=[], type_data=[], security_data={}, fonds_stats=[], hot_files=[], active_users=[])


# ============================================================
#  档案管理模块 END
# ============================================================

'''

# 读取 app.py
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否已添加
if 'def archive_fonds_list():' not in content:
    # 在 if __name__ == '__main__': 之前插入
    insert_pos = content.find("if __name__ == '__main__':")
    if insert_pos > 0:
        content = content[:insert_pos] + routes_code + '\n' + content[insert_pos:]
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print('[OK] 档案路由已添加到 app.py')
    else:
        print('[ERR] 未找到插入位置')
else:
    print('[INFO] 档案路由已存在')
