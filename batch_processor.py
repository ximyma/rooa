# -*- coding: utf-8 -*-
"""
档案批量处理任务队列
支持后台异步处理大量档案
"""
from app import app, db
from flask import jsonify
from datetime import datetime
from enum import Enum
import time
import threading
import os
import json
import traceback
import uuid
import utils

class TaskStatus(Enum):
    """任务状态"""
    PENDING = 'pending'      # 等待中
    RUNNING = 'running'     # 处理中
    COMPLETED = 'completed'  # 已完成
    FAILED = 'failed'        # 失败
    CANCELLED = 'cancelled' # 已取消

class TaskType(Enum):
    """任务类型"""
    BATCH_IMPORT = 'batch_import'      # 批量导入
    OCR_PROCESS = 'ocr_process'         # OCR处理
    META_EXTRACT = 'meta_extract'       # 元数据提取
    VECTOR_INDEX = 'vector_index'       # 向量索引
    BATCH_DELETE = 'batch_delete'        # 批量删除
    BATCH_UPDATE = 'batch_update'        # 批量更新


class BatchTask(db.Model):
    """批量处理任务"""
    __tablename__ = 'batch_tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    task_type = db.Column(db.String(32), nullable=False)
    task_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    
    # 状态
    status = db.Column(db.String(20), default='pending')
    progress = db.Column(db.Integer, default=0)  # 0-100
    current_step = db.Column(db.String(100))
    
    # 统计
    total_items = db.Column(db.Integer, default=0)
    processed_items = db.Column(db.Integer, default=0)
    success_items = db.Column(db.Integer, default=0)
    failed_items = db.Column(db.Integer, default=0)
    
    # 文件信息（JSON格式存储）
    file_list = db.Column(db.Text)  # JSON数组
    result_files = db.Column(db.Text)  # JSON数组，成功处理的文件
    failed_files = db.Column(db.Text)  # JSON数组，失败的文件
    
    # 配置参数（JSON格式）
    params = db.Column(db.Text)  # JSON
    
    # 错误信息
    error_message = db.Column(db.Text)
    
    # 执行信息
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # 关联
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def to_dict(self):
        result = {
            'id': self.id,
            'task_id': self.task_id,
            'task_type': self.task_type,
            'task_name': self.task_name,
            'status': self.status,
            'progress': self.progress,
            'current_step': self.current_step,
            'total_items': self.total_items,
            'processed_items': self.processed_items,
            'success_items': self.success_items,
            'failed_items': self.failed_items,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
        
        # 解析JSON字段
        if self.file_list:
            try:
                result['file_list'] = json.loads(self.file_list)
            except:
                result['file_list'] = []
        else:
            result['file_list'] = []
            
        if self.result_files:
            try:
                result['result_files'] = json.loads(self.result_files)
            except:
                result['result_files'] = []
        else:
            result['result_files'] = []
            
        if self.failed_files:
            try:
                result['failed_files'] = json.loads(self.failed_files)
            except:
                result['failed_files'] = []
        else:
            result['failed_files'] = []
            
        if self.params:
            try:
                result['params'] = json.loads(self.params)
            except:
                result['params'] = {}
        else:
            result['params'] = {}
            
        return result
    
    def __repr__(self):
        return f'<BatchTask {self.task_id}: {self.status}>'


class BatchTaskQueue:
    """
    后台任务队列管理器
    支持多线程后台处理
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._workers = {}  # task_id -> worker thread
        self._running_tasks = {}  # task_id -> task data
    
    def submit_task(self, task_id, task_func, task_data, callback=None):
        """
        提交任务到后台队列
        
        Args:
            task_id: 任务ID
            task_func: 任务处理函数 (task: BatchTask -> None)
            task_data: 任务数据字典
            callback: 完成回调函数 (task: BatchTask -> None)
        """
        with app.app_context():
            # 创建任务记录
            task = BatchTask(
                task_id=task_id,
                task_type=task_data.get('task_type', 'unknown'),
                task_name=task_data.get('task_name', ''),
                description=task_data.get('description', ''),
                total_items=task_data.get('total_items', 0),
                file_list=json.dumps(task_data.get('file_list', [])),
                params=json.dumps(task_data.get('params', {})),
                status='pending',
                created_by=task_data.get('user_id')
            )
            db.session.add(task)
            db.session.commit()
            
            # 保存任务数据供worker使用
            self._running_tasks[task_id] = task_data
            
            # 启动后台线程
            worker = threading.Thread(
                target=self._run_task,
                args=(task_id, task_func, callback),
                daemon=True
            )
            self._workers[task_id] = worker
            worker.start()
            
            return task
    
    def _run_task(self, task_id, task_func, callback):
        """后台执行任务"""
        try:
            with app.app_context():
                # 更新状态为运行中
                task = BatchTask.query.filter_by(task_id=task_id).first()
                if not task:
                    return
                
                task.status = 'running'
                task.started_at = datetime.utcnow()
                db.session.commit()
                
                # 获取任务数据
                task_data = self._running_tasks.get(task_id, {})
                
                # 执行任务
                task_func(task, task_data)
                
                # 更新为完成
                task.status = 'completed'
                task.completed_at = datetime.utcnow()
                if task.progress == 0:
                    task.progress = 100
                db.session.commit()
                
        except Exception as e:
            with app.app_context():
                task = BatchTask.query.filter_by(task_id=task_id).first()
                if task:
                    task.status = 'failed'
                    task.error_message = str(e) + '\n' + traceback.format_exc()
                    task.completed_at = datetime.utcnow()
                    db.session.commit()
        
        finally:
            # 清理引用
            self._workers.pop(task_id, None)
            self._running_tasks.pop(task_id, None)
            
            # 执行回调
            if callback:
                try:
                    callback(task)
                except:
                    pass
    
    def get_task(self, task_id):
        """获取任务状态"""
        with app.app_context():
            return BatchTask.query.filter_by(task_id=task_id).first()
    
    def get_user_tasks(self, user_id, status=None, limit=20):
        """获取用户的任务列表"""
        with app.app_context():
            query = BatchTask.query.filter_by(created_by=user_id)
            if status:
                query = query.filter_by(status=status)
            return query.order_by(BatchTask.created_at.desc()).limit(limit).all()
    
    def cancel_task(self, task_id):
        """取消任务"""
        with app.app_context():
            task = BatchTask.query.filter_by(task_id=task_id).first()
            if task and task.status in ['pending', 'running']:
                task.status = 'cancelled'
                task.completed_at = datetime.utcnow()
                db.session.commit()
                return True
            return False
    
    def retry_task(self, task_id):
        """重试失败的任务"""
        with app.app_context():
            task = BatchTask.query.filter_by(task_id=task_id).first()
            if task and task.status == 'failed':
                task.status = 'pending'
                task.error_message = None
                task.started_at = None
                task.progress = 0
                task.processed_items = 0
                task.success_items = 0
                task.failed_items = 0
                db.session.commit()
                return True
            return False
    
    def is_running(self, task_id):
        """检查任务是否在运行"""
        return task_id in self._workers


# 全局队列实例
task_queue = BatchTaskQueue()


def update_task_progress(task, processed, success=True, failed_file=None):
    """
    更新任务进度（供任务内部调用）
    
    Args:
        task: BatchTask对象
        processed: 已处理数量
        success: 当前处理是否成功
        failed_file: 失败的文件信息
    """
    task.processed_items = processed
    if task.total_items > 0:
        task.progress = min(100, int(processed * 100 / task.total_items))
    
    if success:
        task.success_items = (task.success_items or 0) + 1
    else:
        task.failed_items = (task.failed_items or 0) + 1
        # 记录失败文件
        failed_list = []
        if task.failed_files:
            try:
                failed_list = json.loads(task.failed_files)
            except:
                pass
        if failed_file:
            failed_list.append(failed_file)
        task.failed_files = json.dumps(failed_list)
    
    db.session.commit()


def create_batch_import_task(user_id, files_data, fonds_id, catalog_id, volume_id, metadata_override=None):
    """
    创建批量导入任务
    
    Args:
        user_id: 用户ID
        files_data: 文件数据列表 [{path, filename, size}, ...]
        fonds_id: 全宗ID
        catalog_id: 目录ID
        volume_id: 案卷ID (可选)
        metadata_override: 元数据覆盖 (dict)
    
    Returns:
        task_id: 任务ID
    """
    from archive_models import ArchiveFile
    
    task_id = 'import_' + datetime.now().strftime('%Y%m%d%H%M%S') + '_' + str(uuid.uuid4())[:8]
    
    def process_batch_import(task, task_data):
        """批量导入处理函数"""
        from archive_digitizer import archive_digitizer
        from utils import allowed_file
        
        files = task_data.get('files_data', [])
        total = len(files)
        
        task.total_items = total
        task.current_step = '开始批量导入...'
        db.session.commit()
        
        success_ids = []
        failed_list = []
        
        for i, file_info in enumerate(files):
            try:
                file_path = file_info.get('path')
                if not file_path or not os.path.exists(file_path):
                    failed_list.append({
                        'filename': file_info.get('filename', 'unknown'),
                        'error': '文件不存在'
                    })
                    update_task_progress(task, i + 1, success=False, 
                                        failed_file={'filename': file_info.get('filename'), 'error': '文件不存在'})
                    continue
                
                # 元数据
                metadata = task_data.get('metadata_override', {}).copy()
                metadata.setdefault('title', file_info.get('original_name', '未命名'))
                
                # 处理数字化
                result = archive_digitizer.process_digitization(
                    file_path,
                    task_data.get('fonds_id'),
                    task_data.get('catalog_id'),
                    task_data.get('volume_id'),
                    task_data.get('user_id'),
                    metadata
                )
                
                if isinstance(result, ArchiveFile):
                    success_ids.append({
                        'id': result.id,
                        'title': result.title,
                        'code': result.get_archive_code()
                    })
                    task.result_files = json.dumps(success_ids)
                    update_task_progress(task, i + 1, success=True)
                else:
                    error_msg = result.get('error', '未知错误')
                    failed_list.append({
                        'filename': file_info.get('original_name', 'unknown'),
                        'error': error_msg
                    })
                    update_task_progress(task, i + 1, success=False,
                                        failed_file={'filename': file_info.get('original_name'), 'error': error_msg})
                
                # 每处理10个保存一次
                if (i + 1) % 10 == 0:
                    task.current_step = f'已处理 {i + 1}/{total} 个文件'
                    db.session.commit()
                    
            except Exception as e:
                failed_list.append({
                    'filename': file_info.get('filename', 'unknown'),
                    'error': str(e)
                })
                update_task_progress(task, i + 1, success=False,
                                    failed_file={'filename': file_info.get('filename'), 'error': str(e)})
        
        task.current_step = f'完成！成功 {task.success_items} 个，失败 {task.failed_items} 个'
        task.result_files = json.dumps(success_ids)
        db.session.commit()
    
    task_data = {
        'task_type': 'batch_import',
        'task_name': f'批量导入档案 ({len(files_data)} 个文件)',
        'description': f'从批量上传 {len(files_data)} 个文件导入到 {fonds_id}/{catalog_id}',
        'total_items': len(files_data),
        'files_data': files_data,
        'fonds_id': fonds_id,
        'catalog_id': catalog_id,
        'volume_id': volume_id,
        'user_id': user_id,
        'metadata_override': metadata_override or {},
        'source_folder': '批量上传'
    }
    
    task = task_queue.submit_task(task_id, process_batch_import, task_data)
    return task_id
