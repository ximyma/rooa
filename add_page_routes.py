# -*- coding: utf-8 -*-
"""添加档案系统页面路由"""

routes_to_add = '''
# ==================== 页面路由 ====================

@archive_bp.route('/fonds')
@login_required
def fonds_list():
    """全宗管理页面"""
    ArchiveFonds, _, _, _, _, _ = get_models()
    fonds_list = ArchiveFonds.query.filter_by(is_active=True).all()
    total_files = 0
    for f in fonds_list:
        total_files += f.file_count or 0
    return render_template('archive/fonds_list.html', fonds_list=fonds_list, total_files=total_files)


@archive_bp.route('/files')
@login_required
def file_list():
    """档案列表页面"""
    ArchiveFonds, _, _, ArchiveFile, _, _ = get_models()
    from models import db
    from sqlalchemy import func
    
    # 获取筛选参数
    keyword = request.args.get('keyword', '')
    fonds_id = request.args.get('fonds_id', type=int)
    retention = request.args.get('retention', '')
    year = request.args.get('year', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # 构建查询
    query = ArchiveFile.query.filter_by(is_active=True)
    
    if keyword:
        query = query.filter(ArchiveFile.title.contains(keyword))
    if fonds_id:
        query = query.filter_by(fonds_id=fonds_id)
    if retention:
        query = query.filter_by(retention_period=retention)
    if year:
        query = query.filter(func.strftime('%Y', ArchiveFile.archive_date) == str(year))
    
    # 分页
    pagination = query.order_by(ArchiveFile.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # 获取统计数据
    stats = {
        'digitized': ArchiveFile.query.filter_by(is_active=True, is_digitized=True).count(),
        'permanent': ArchiveFile.query.filter_by(is_active=True, retention_period='永久').count(),
        'borrowed': 0  # TODO: 统计借阅中数量
    }
    
    # 获取全宗列表和年度列表
    fonds_list = ArchiveFonds.query.filter_by(is_active=True).all()
    years = db.session.query(func.strftime('%Y', ArchiveFile.archive_date)).distinct().all()
    years = [y[0] for y in years if y[0]]
    
    return render_template('archive/file_list.html',
                         files=pagination.items,
                         pagination=pagination,
                         stats=stats,
                         fonds_list=fonds_list,
                         years=sorted(set(years), reverse=True))


@archive_bp.route('/search')
@login_required
def search():
    """档案检索页面"""
    ArchiveFonds, _, _, ArchiveFile, _, _ = get_models()
    from models import db
    from sqlalchemy import or_
    
    query_text = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    results = []
    total = 0
    
    if query_text:
        # 搜索标题、内容、关键词
        query = ArchiveFile.query.filter(
            ArchiveFile.is_active == True,
            or_(
                ArchiveFile.title.contains(query_text),
                ArchiveFile.content.contains(query_text),
                ArchiveFile.keywords.contains(query_text),
                ArchiveFile.archive_code.contains(query_text)
            )
        )
        
        total = query.count()
        results = query.order_by(ArchiveFile.created_at.desc()).offset((page-1)*per_page).limit(per_page).all()
    
    # 获取筛选参数
    filters = {
        'fonds_id': request.args.get('fonds_id', ''),
        'retention': request.args.get('retention', ''),
        'year': request.args.get('year', ''),
        'file_type': request.args.get('file_type', '')
    }
    
    # 获取全宗列表
    fonds_list = ArchiveFonds.query.filter_by(is_active=True).all()
    
    # 获取年度列表
    from sqlalchemy import func
    years = db.session.query(func.strftime('%Y', ArchiveFile.archive_date)).distinct().all()
    years = [y[0] for y in years if y[0]]
    
    return render_template('archive/search.html',
                         query=query_text,
                         results=results,
                         total=total,
                         page=page,
                         pages=(total // per_page) + 1 if total > 0 else 0,
                         filters=filters,
                         fonds_list=fonds_list,
                         years=sorted(set(years), reverse=True))


@archive_bp.route('/my_borrows')
@login_required
def my_borrows():
    """我的借阅页面"""
    _, _, _, _, ArchiveBorrow, _ = get_models()
    from models import db
    
    status = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = ArchiveBorrow.query.filter_by(user_id=current_user.id)
    
    if status == 'active':
        query = query.filter_by(status='borrowed')
    elif status == 'returned':
        query = query.filter_by(status='returned')
    elif status == 'overdue':
        query = query.filter(ArchiveBorrow.status == 'borrowed', ArchiveBorrow.due_date < datetime.now())
    
    pagination = query.order_by(ArchiveBorrow.created_at.desc()).paginate(page=page, per_page=per_page)
    
    # 统计
    stats = {
        'total': ArchiveBorrow.query.filter_by(user_id=current_user.id).count(),
        'active': ArchiveBorrow.query.filter_by(user_id=current_user.id, status='borrowed').count(),
        'returned': ArchiveBorrow.query.filter_by(user_id=current_user.id, status='returned').count(),
        'overdue': ArchiveBorrow.query.filter_by(user_id=current_user.id, status='borrowed').filter(ArchiveBorrow.due_date < datetime.now()).count()
    }
    
    return render_template('archive/my_borrows.html',
                         borrows=pagination.items,
                         pagination=pagination,
                         status=status,
                         stats=stats)


@archive_bp.route('/statistics')
@login_required
def statistics():
    """统计报表页面"""
    ArchiveFonds, _, _, ArchiveFile, ArchiveBorrow, _ = get_models()
    from models import db
    from sqlalchemy import func
    
    # 基础统计
    stats = {
        'total_files': ArchiveFile.query.filter_by(is_active=True).count(),
        'digitized': ArchiveFile.query.filter_by(is_active=True, is_digitized=True).count(),
        'total_fonds': ArchiveFonds.query.filter_by(is_active=True).count(),
        'total_borrows': ArchiveBorrow.query.count()
    }
    
    # 保管期限分布
    retention_data = {
        'permanent': ArchiveFile.query.filter_by(is_active=True, retention_period='永久').count(),
        'y30': ArchiveFile.query.filter_by(is_active=True, retention_period='30年').count(),
        'y10': ArchiveFile.query.filter_by(is_active=True, retention_period='10年').count(),
        'unknown': ArchiveFile.query.filter_by(is_active=True, retention_period=None).count()
    }
    
    # 年度分布
    year_data = db.session.query(
        func.strftime('%Y', ArchiveFile.archive_date).label('year'),
        func.count().label('count')
    ).filter(ArchiveFile.is_active == True).group_by('year').order_by('year').all()
    
    # 类型分布
    type_data = db.session.query(
        ArchiveFile.file_type,
        func.count().label('count')
    ).filter(ArchiveFile.is_active == True).group_by(ArchiveFile.file_type).all()
    
    # 密级分布
    security_data = {
        'public': ArchiveFile.query.filter_by(is_active=True, security_level='公开').count(),
        'internal': ArchiveFile.query.filter_by(is_active=True, security_level='内部').count(),
        'secret': ArchiveFile.query.filter_by(is_active=True, security_level='秘密').count(),
        'confidential': ArchiveFile.query.filter_by(is_active=True, security_level='机密').count()
    }
    
    # 全宗统计
    fonds_stats = db.session.query(
        ArchiveFonds.id,
        ArchiveFonds.fonds_code,
        ArchiveFonds.fonds_name,
        func.count(ArchiveFile.id).label('file_count')
    ).outerjoin(ArchiveFile).filter(ArchiveFonds.is_active == True).group_by(ArchiveFonds.id).all()
    
    # 热门借阅档案
    hot_files = db.session.query(
        ArchiveFile.title,
        func.count(ArchiveBorrow.id).label('borrow_count')
    ).join(ArchiveBorrow).group_by(ArchiveFile.id).order_by(func.count(ArchiveBorrow.id).desc()).limit(10).all()
    
    # 活跃用户
    from models import User
    active_users = db.session.query(
        User.name.label('user_name'),
        func.count(ArchiveBorrow.id).label('borrow_count')
    ).join(ArchiveBorrow).group_by(User.id).order_by(func.count(ArchiveBorrow.id).desc()).limit(10).all()
    
    return render_template('archive/statistics.html',
                         stats=stats,
                         retention_data=retention_data,
                         year_data=[{'year': y.year, 'count': y.count} for y in year_data if y.year],
                         type_data=[{'type': t.file_type or '未知', 'count': t.count} for t in type_data],
                         security_data=security_data,
                         fonds_stats=fonds_stats,
                         hot_files=hot_files,
                         active_users=active_users)


@archive_bp.route('/file/<int:file_id>')
@login_required
def file_detail(file_id):
    """档案详情页面"""
    _, _, _, ArchiveFile, ArchiveBorrow, _ = get_models()
    from models import db
    
    file = ArchiveFile.query.get_or_404(file_id)
    
    # 获取借阅历史
    borrow_history = ArchiveBorrow.query.filter_by(file_id=file_id).order_by(ArchiveBorrow.created_at.desc()).limit(5).all()
    
    # 获取相关档案（通过关键词匹配）
    related_files = []
    if file.keywords:
        keywords = file.keywords.split(',')
        if keywords:
            from sqlalchemy import or_
            related_files = ArchiveFile.query.filter(
                ArchiveFile.id != file_id,
                ArchiveFile.is_active == True,
                or_(*[ArchiveFile.keywords.contains(kw.strip()) for kw in keywords[:3] if kw.strip()])
            ).limit(5).all()
    
    return render_template('archive/file_detail.html',
                         file=file,
                         borrow_history=borrow_history,
                         related_files=related_files)

'''

with open('archive_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否已存在这些路由
if 'def fonds_list():' not in content:
    # 在文件末尾添加
    content += '\n' + routes_to_add
    with open('archive_routes.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('[OK] 页面路由已添加')
else:
    print('[INFO] 页面路由已存在')
