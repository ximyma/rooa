#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
栏目监测系统 - 定时任务调度模块
"""
from flask_apscheduler import APScheduler
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)
scheduler = APScheduler()


def init_monitor_scheduler(app):
    """初始化栏目监测调度器"""
    if not scheduler.running:
        scheduler.init_app(app)
        scheduler.start()
    
    # 重新加载所有活跃的定时任务
    with app.app_context():
        from models import MonitorScheduledTask
        tasks = MonitorScheduledTask.query.filter_by(is_active=True).all()
        for task in tasks:
            job_id = f'monitor_task_{task.id}'
            
            # 如果任务已存在，先移除
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
            
            # 添加新任务
            try:
                scheduler.add_job(
                    id=job_id,
                    func=execute_scheduled_monitor_task,
                    args=[task.id],
                    trigger='cron',
                    **parse_cron_expression(task.cron_expression)
                )
                logger.info(f"监测定时任务已加载: {task.name}")
            except Exception as e:
                logger.error(f"监测定时任务加载失败: {task.name} - {str(e)}")


def parse_cron_expression(expr):
    """解析Cron表达式
    
    支持格式:
    - "每天 08:00" - 每天指定时间执行
    - "每周一 09:00" - 每周指定星期和时间执行
    - "每月1号 10:00" - 每月指定日期和时间执行
    """
    if not expr:
        return {'hour': 8, 'minute': 0}  # 默认值
    
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
        # 提取数字
        digits = ''.join(filter(str.isdigit, expr[2:5]))
        day_num = int(digits) if digits else 1
        time_parts = parts[-1].split(':')
        return {
            'day': day_num,
            'hour': int(time_parts[0]),
            'minute': int(time_parts[1]) if len(time_parts) > 1 else 0
        }
    
    # 默认每天执行
    return {'hour': 8, 'minute': 0}


def execute_scheduled_monitor_task(task_id):
    """执行定时监测任务"""
    from app import app
    from models import db, MonitorScheduledTask, MonitorResult, UrlLibrary
    from monitor_core import MonitorEngine
    # MonitorEmailSender is in this file
    
    with app.app_context():
        task = MonitorScheduledTask.query.get(task_id)
        if not task or not task.is_active:
            return
        
        try:
            MonitorSystemLog.log('INFO', 'scheduler', f'定时监测任务开始执行: {task.name}')
            
            # 创建监测引擎
            monitor = MonitorEngine(task.library_id)
            
            # 加载网址
            count = monitor.load_items()
            if count == 0:
                MonitorSystemLog.log('WARNING', 'scheduler', f'网址库为空: {task.name}')
                return
            
            # 执行监测
            stats = monitor.run()
            
            # 获取最新结果用于邮件
            results = MonitorResult.query.filter_by(library_id=task.library_id).order_by(
                MonitorResult.monitor_time.desc()
            ).all()
            
            # 发送邮件
            recipients = json.loads(task.email_recipients) if task.email_recipients else []
            if recipients:
                email_sender = MonitorEmailSender()
                email_sender.init_app(app)
                
                # 构建邮件内容
                subject = f"[监测报告] {task.name} - {datetime.now().strftime('%Y-%m-%d')}"
                body = build_monitor_report_email(task, stats, results)
                
                email_sender.send_monitor_report(recipients, subject, body)
            
            # 更新任务状态
            task.last_run_time = datetime.now()
            task.run_count += 1
            db.session.commit()
            
            MonitorSystemLog.log('INFO', 'scheduler', 
                f'定时监测任务完成: {task.name}, 成功:{stats["success"]} 失败:{stats["error"]}')
            
        except Exception as e:
            MonitorSystemLog.log('ERROR', 'scheduler', f'定时监测任务执行失败: {str(e)}')
            import traceback
            traceback.print_exc()


def build_monitor_report_email(task, stats, results):
    """构建监测报告邮件内容"""
    overdue = [r for r in results if r.is_overdue]
    expiring = [r for r in results if r.is_expiring]
    normal = [r for r in results if not r.is_overdue and not r.is_expiring]
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; }}
            .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .summary h3 {{ margin-top: 0; color: #333; }}
            .stat {{ display: inline-block; margin-right: 20px; }}
            .stat-value {{ font-size: 24px; font-weight: bold; }}
            .stat-label {{ color: #666; }}
            .overdue {{ color: #d32f2f; }}
            .expiring {{ color: #f57c00; }}
            .normal {{ color: #388e3c; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .badge {{ display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 12px; }}
            .badge-overdue {{ background: #ffcdd2; color: #c62828; }}
            .badge-expiring {{ background: #ffe0b2; color: #e65100; }}
            .badge-ok {{ background: #c8e6c9; color: #2e7d32; }}
            .badge-error {{ background: #ffcdd2; color: #c62828; }}
        </style>
    </head>
    <body>
        <h2>[监测报告] {task.name}</h2>
        <p>监测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <h3>汇总统计</h3>
            <div class="stat">
                <div class="stat-value">{stats['total']}</div>
                <div class="stat-label">总网址数</div>
            </div>
            <div class="stat">
                <div class="stat-value overdue">{stats['success']}</div>
                <div class="stat-label">成功</div>
            </div>
            <div class="stat">
                <div class="stat-value">{stats['error']}</div>
                <div class="stat-label">失败</div>
            </div>
            <div class="stat">
                <div class="stat-value overdue">{stats['overdue']}</div>
                <div class="stat-label">已逾期</div>
            </div>
            <div class="stat">
                <div class="stat-value expiring">{stats['expiring']}</div>
                <div class="stat-label">即将逾期</div>
            </div>
        </div>
    """
    
    if overdue:
        html += """
        <h3 class="overdue">已逾期栏目 ({}个)</h3>
        <table>
            <tr>
                <th>栏目名称</th>
                <th>网站名称</th>
                <th>最后更新</th>
                <th>逾期天数</th>
            </tr>
        """.format(len(overdue))
        for r in overdue[:10]:  # 最多显示10条
            html += f"""
            <tr>
                <td>{r.column_name or 'N/A'}</td>
                <td>{r.website_name or 'N/A'}</td>
                <td>{r.last_max_date or '无'}</td>
                <td class="overdue">{r.days_since_update}天</td>
            </tr>
            """
        html += "</table>"
    
    if expiring:
        html += """
        <h3 class="expiring">即将逾期栏目 ({}个)</h3>
        <table>
            <tr>
                <th>栏目名称</th>
                <th>网站名称</th>
                <th>最后更新</th>
                <th>剩余天数</th>
            </tr>
        """.format(len(expiring))
        for r in expiring[:10]:
            html += f"""
            <tr>
                <td>{r.column_name or 'N/A'}</td>
                <td>{r.website_name or 'N/A'}</td>
                <td>{r.last_max_date or '无'}</td>
                <td class="expiring">{r.days_since_update}天</td>
            </tr>
            """
        html += "</table>"
    
    if normal and not overdue and not expiring:
        html += """
        <h3 class="normal">正常栏目</h3>
        <p>所有 {} 个栏目均正常运行，无逾期或即将逾期情况。</p>
        """.format(len(normal))
    
    html += """
        <hr>
        <p style="color: #666; font-size: 12px;">
            此邮件由智能服务办公平台自动发送<br>
            如需修改定时任务设置，请登录系统管理
        </p>
    </body>
    </html>
    """
    
    return html


# 邮件发送器
class MonitorEmailSender:
    """栏目监测系统 - 邮件发送器"""
    
    def __init__(self, app=None):
        self.app = app
        self.enabled = False
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        self.enabled = app.config.get('MAIL_SERVER') is not None
    
    def send_monitor_report(self, recipients, subject, body):
        """发送监测报告邮件"""
        if not self.enabled:
            logger.warning("邮件服务未配置")
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEBase, MIMEMultipart
            from email import encoders
            
            msg = MIMEMultipart()
            msg['From'] = self.app.config.get('MAIL_DEFAULT_SENDER', 'noreply@oa.local')
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject
            
            # 邮件正文
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # 发送邮件
            mail_server = self.app.config.get('MAIL_SERVER')
            mail_port = self.app.config.get('MAIL_PORT', 465)
            
            with smtplib.SMTP_SSL(mail_server, mail_port) as server:
                server.login(
                    self.app.config.get('MAIL_USERNAME'),
                    self.app.config.get('MAIL_PASSWORD')
                )
                server.send_message(msg)
            
            logger.info(f"监测报告邮件发送成功: {recipients}")
            return True
        
        except Exception as e:
            logger.error(f"监测报告邮件发送失败: {str(e)}")
            return False
