# -*- coding: utf-8 -*-
"""添加批量任务路由到 archive_routes.py"""

routes_to_add = '''

# ==================== 批量任务管理 ====================

@archive_bp.route('/tasks')
@login_required
def task_list():
    """批量任务列表"""
    from batch_processor import BatchTask
    
    # 获取最近的任务
    recent_tasks = BatchTask.query.order_by(
        BatchTask.created_at.desc()
    ).limit(30).all()
    
    return render_template('archive/task_list.html', 
                         tasks=[t.to_dict() for t in recent_tasks])


@archive_bp.route('/api/task/status/<task_id>')
@login_required
def api_task_status(task_id):
    """获取任务状态"""
    from batch_processor import BatchTask
    
    task = BatchTask.query.filter_by(task_id=task_id).first()
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify(task.to_dict())


@archive_bp.route('/api/task/cancel/<task_id>', methods=['POST'])
@login_required
def api_task_cancel(task_id):
    """取消任务"""
    from batch_processor import task_queue
    
    success = task_queue.cancel_task(task_id)
    if success:
        return jsonify({'success': True, 'message': '任务已取消'})
    else:
        return jsonify({'success': False, 'message': '无法取消任务'})


@archive_bp.route('/api/task/retry/<task_id>', methods=['POST'])
@login_required
def api_task_retry(task_id):
    """重试任务"""
    from batch_processor import task_queue, create_batch_import_task
    from batch_processor import BatchTask
    
    # 获取原始任务
    old_task = BatchTask.query.filter_by(task_id=task_id).first()
    if not old_task or old_task.status != 'failed':
        return jsonify({'success': False, 'message': '只能重试失败的任务'})
    
    # 创建新任务
    task_data = {
        'file_list': old_task.file_list,
        'fonds_id': old_task.params.get('fonds_id') if old_task.params else None,
        'catalog_id': old_task.params.get('catalog_id') if old_task.params else None,
        'user_id': old_task.created_by
    }
    
    success = task_queue.retry_task(task_id)
    if success:
        return jsonify({'success': True, 'message': '任务已重新提交'})
    else:
        return jsonify({'success': False, 'message': '无法重试任务'})


@archive_bp.route('/api/task/submit', methods=['POST'])
@login_required
def api_task_submit():
    """
    提交批量导入任务
    支持多文件上传
    """
    import os
    import uuid
    from batch_processor import create_batch_import_task
    from utils import save_upload_file, allowed_file
    from werkzeug.utils import secure_filename
    
    fonds_id = request.form.get('fonds_id')
    catalog_id = request.form.get('catalog_id')
    volume_id = request.form.get('volume_id') or None
    
    if not fonds_id or not catalog_id:
        return jsonify({'error': '请选择全宗和目录'}), 400
    
    files = request.files.getlist('files')
    if not files or all(not f.filename for f in files):
        return jsonify({'error': '请选择要上传的文件'}), 400
    
    # 保存临时文件
    files_data = []
    temp_folder = os.path.join('uploads', 'temp', 'batch_' + datetime.now().strftime('%Y%m%d%H%M%S'))
    os.makedirs(temp_folder, exist_ok=True)
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            original_name = secure_filename(file.filename)
            temp_path = os.path.join(temp_folder, original_name)
            file.save(temp_path)
            files_data.append({
                'path': temp_path,
                'filename': original_name,
                'original_name': original_name,
                'size': os.path.getsize(temp_path)
            })
    
    if not files_data:
        return jsonify({'error': '没有有效的文件'}), 400
    
    # 创建批量导入任务
    task_id = create_batch_import_task(
        user_id=current_user.id,
        files_data=files_data,
        fonds_id=int(fonds_id),
        catalog_id=int(catalog_id),
        volume_id=int(volume_id) if volume_id else None
    )
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': f'已提交 {len(files_data)} 个文件到后台处理'
    })


@archive_bp.route('/api/task/progress/<task_id>')
@login_required
def api_task_progress(task_id):
    """获取任务进度（轮询接口）"""
    from batch_processor import BatchTask
    
    task = BatchTask.query.filter_by(task_id=task_id).first()
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify({
        'task_id': task.task_id,
        'status': task.status,
        'progress': task.progress,
        'current_step': task.current_step,
        'total_items': task.total_items,
        'processed_items': task.processed_items,
        'success_items': task.success_items,
        'failed_items': task.failed_items,
        'error_message': task.error_message
    })


# ==================== Excel元数据导入 ====================

@archive_bp.route('/excel_import', methods=['GET', 'POST'])
@login_required
def excel_import():
    """Excel批量元数据导入"""
    from archive_models import ArchiveFile
    from models import db
    import pandas as pd
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('请选择Excel文件', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if not file.filename.endswith(('.xlsx', '.xls')):
            flash('请上传Excel文件', 'error')
            return redirect(request.url)
        
        try:
            # 读取Excel
            df = pd.read_excel(file)
            
            # 验证必要字段
            required_cols = ['标题', '全宗ID', '目录ID']
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                flash(f'缺少必要字段: {missing}', 'error')
                return redirect(request.url)
            
            # 批量创建/更新
            success_count = 0
            error_count = 0
            
            for idx, row in df.iterrows():
                try:
                    archive = ArchiveFile(
                        fonds_id=int(row['全宗ID']),
                        catalog_id=int(row['目录ID']),
                        title=row['标题'],
                        responsibility=str(row.get('责任者', '')),
                        retention_period=str(row.get('保管期限', '30年')),
                        security_level=str(row.get('密级', '公开')),
                        archive_type=str(row.get('档案类型', '其他')),
                        keywords=str(row.get('关键词', '')),
                        status='active',
                        created_by=current_user.id
                    )
                    db.session.add(archive)
                    success_count += 1
                except Exception as e:
                    error_count += 1
            
            db.session.commit()
            
            if error_count > 0:
                flash(f'成功导入 {success_count} 条记录，失败 {error_count} 条', 'warning')
            else:
                flash(f'成功导入 {success_count} 条记录', 'success')
            return redirect(url_for('archive.file_list'))
            
        except Exception as e:
            flash(f'导入失败: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('archive/excel_import.html')


# ==================== 批量操作 ====================

@archive_bp.route('/batch_delete', methods=['POST'])
@login_required
def batch_delete():
    """批量删除档案"""
    from archive_models import ArchiveFile
    from models import db
    import json
    
    ids = request.form.get('ids')
    if not ids:
        return jsonify({'error': '未选择要删除的档案'}), 400
    
    try:
        file_ids = json.loads(ids)
        count = ArchiveFile.query.filter(ArchiveFile.id.in_(file_ids)).delete(
            synchronize_session=False
        )
        db.session.commit()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@archive_bp.route('/batch_update_status', methods=['POST'])
@login_required
def batch_update_status():
    """批量更新档案状态"""
    from archive_models import ArchiveFile
    from models import db
    import json
    
    ids = request.form.get('ids')
    status = request.form.get('status')
    
    if not ids or not status:
        return jsonify({'error': '参数不完整'}), 400
    
    try:
        file_ids = json.loads(ids)
        count = ArchiveFile.query.filter(ArchiveFile.id.in_(file_ids)).update(
            {'status': status},
            synchronize_session=False
        )
        db.session.commit()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
'''

# 读取原文件
with open('archive_routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查是否已添加
if '# ==================== 批量任务管理 ====================' not in content:
    # 添加到文件末尾
    with open('archive_routes.py', 'w', encoding='utf-8') as f:
        f.write(content + routes_to_add)
    print('[OK] 批量任务路由已添加')
else:
    print('[INFO] 批量任务路由已存在，跳过')
