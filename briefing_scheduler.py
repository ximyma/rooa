#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简报系统 - 定时任务调度模块
"""
from flask_apscheduler import APScheduler
from datetime import datetime
from models import db, BriefingScheduledTask, Briefing, BriefingSource, BriefingKeyword, BriefingSystemLog
import json
import logging

logger = logging.getLogger(__name__)
scheduler = APScheduler()


def init_briefing_scheduler(app):
    """初始化简报调度器"""
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()
    
    # 重新加载所有活跃的定时任务
    with app.app_context():
        tasks = BriefingScheduledTask.query.filter_by(is_active=True).all()
        for task in tasks:
            job_id = f'briefing_task_{task.id}'
            
            # 如果任务已存在，先移除
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
            
            # 添加新任务
            try:
                scheduler.add_job(
                    id=job_id,
                    func=execute_scheduled_briefing_task,
                    args=[task.id],
                    trigger='cron',
                    **parse_cron_expression(task.cron_expression)
                )
            except Exception as e:
                BriefingSystemLog.log('ERROR', 'scheduler', f'定时任务加载失败: {task.name} - {str(e)}')


def parse_cron_expression(expr):
    """解析Cron表达式"""
    if not expr:
        return {'hour': 8, 'minute': 0}  # 默认值
        
    # 支持: "每天 08:00", "每周一 09:00", "每月1号 10:00"
    parts = expr.split()
    
    if '每天' in expr:
        time_parts = parts[-1].split(':')
        return {
            'hour': int(time_parts[0]),
            'minute': int(time_parts[1]) if len(time_parts) > 1 else 0
        }
    elif '每周' in expr:
        weekdays = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 0}
        day_char = expr[2] if len(expr) > 2 else '一'
        time_parts = parts[-1].split(':')
        return {
            'day_of_week': weekdays.get(day_char, 1),
            'hour': int(time_parts[0]),
            'minute': int(time_parts[1]) if len(time_parts) > 1 else 0
        }
    elif '每月' in expr:
        day_num = int(''.join(filter(str.isdigit, expr[2:5])))
        time_parts = parts[-1].split(':')
        return {
            'day': day_num,
            'hour': int(time_parts[0]),
            'minute': int(time_parts[1]) if len(time_parts) > 1 else 0
        }
    
    # 默认每天执行
    return {'hour': 8, 'minute': 0}


def execute_scheduled_briefing_task(task_id):
    """执行定时简报任务"""
    # 在函数内部导入，打破循环引用
    from app import app, briefing_task_queue
    
    with app.app_context():
        task = BriefingScheduledTask.query.get(task_id)
        if not task or not task.is_active:
            return
        
        try:
            # 创建简报任务
            date_str = datetime.now().strftime('%Y%m%d')
            task_uid = f"SCHEDULED_{task_id}_{date_str}"
            
            briefing = Briefing(
                task_id=task_uid,
                title=f"{task.name}_{date_str}",
                keywords=task.keywords,
                sources=task.sources,
                target_date=date_str,
                status='pending'
            )
            db.session.add(briefing)
            db.session.commit()
            
            # 加入任务队列
            briefing_task_queue.put({
                'task_id': task_uid,
                'keywords': json.loads(task.keywords) if task.keywords else [],
                'source_ids': json.loads(task.sources) if task.sources else [],
                'date': date_str,
                'title': briefing.title,
                'email_recipients': json.loads(task.email_recipients) if task.email_recipients else []
            })
            
            # 更新任务状态
            task.last_run_time = datetime.now()
            task.run_count += 1
            db.session.commit()
            
            BriefingSystemLog.log('INFO', 'scheduler', f'定时任务已触发: {task.name}')
            
        except Exception as e:
            BriefingSystemLog.log('ERROR', 'scheduler', f'定时任务执行失败: {str(e)}')
