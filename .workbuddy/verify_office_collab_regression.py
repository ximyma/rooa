# -*- coding: utf-8 -*-
import os
import re
import sys
import logging
import traceback
from datetime import datetime, timedelta


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
logging.disable(logging.CRITICAL)

from app import app, db

from models import (
    User,
    MeetingRoom,
    Meeting,
    MeetingAttendance,
    SupervisionTask,
    SupervisionProgress,
    PerformancePeriod,
    PerformanceAssessment,
    WorkLog,
)


RESULTS = []
CREATED = {
    'meeting_ids': [],
    'room_ids': [],
    'task_ids': [],
    'period_ids': [],
    'record_ids': [],
    'log_ids': [],
}


def ok(name, extra=''):
    RESULTS.append({'name': name, 'ok': True, 'extra': extra})


def fail(name, message):
    raise AssertionError(f'{name} 失败：{message}')


def _response_text(response):
    return response.get_data().decode('utf-8', 'ignore')


def _extract_csrf_token(response):
    body = _response_text(response)
    match = re.search(r'id="global_csrf_token"\s+value="([^"]+)"', body)
    if not match:
        fail('提取 CSRF', '页面中未找到全局 CSRF token')
    return match.group(1)


def check_response(name, response, expected=(200,), body_contains=None):

    if response.status_code not in expected:
        body = _response_text(response)[:800]
        fail(name, f'HTTP {response.status_code}\n{body}')
    if body_contains:
        body = _response_text(response)
        missing = [item for item in body_contains if item not in body]
        if missing:
            fail(name, f'响应缺少关键内容: {missing}')
    ok(name, f'HTTP {response.status_code}')



with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        fail('初始化', '未找到 admin 用户')

    other_user = User.query.filter(User.id != admin.id).order_by(User.id.asc()).first() or admin
    suffix = datetime.now().strftime('%Y%m%d%H%M%S')
    now = datetime.now().replace(second=0, microsecond=0)

    try:
        room = MeetingRoom(
            name=f'回归会议室-{suffix}',
            location='5F-测试区',
            capacity=20,
            status='available',
            manager_id=admin.id,
            equipment='投影,白板',
            remark='办公协同回归验证专用',
        )
        db.session.add(room)
        db.session.flush()
        CREATED['room_ids'].append(room.id)

        attendee_ids = [admin.id]
        if other_user.id != admin.id:
            attendee_ids.append(other_user.id)

        meeting = Meeting(
            subject=f'办公协同回归会议-{suffix}',
            meeting_type='专题会',
            level='部门级',
            priority='重要',
            room_id=room.id,
            host_id=admin.id,
            creator_id=admin.id,
            attendee_depts='办公室',
            agenda='验证会议编辑、取消与快捷筛选',
            minutes='',
            require_signin=True,
            status='pending',
            start_time=now + timedelta(hours=2),
            end_time=now + timedelta(hours=3),
        )
        meeting.set_attendee_ids(attendee_ids)
        db.session.add(meeting)
        db.session.flush()
        CREATED['meeting_ids'].append(meeting.id)

        for uid in attendee_ids:
            db.session.add(MeetingAttendance(meeting_id=meeting.id, user_id=uid, attendance_status='pending'))

        task = SupervisionTask(
            task_no=f'DB-REG-{suffix}',
            title=f'办公协同回归督办-{suffix}',
            category='重点工作',
            source='专项督查',
            content='验证督办编辑、批量催办、关闭及快捷筛选',
            creator_id=admin.id,
            owner_id=admin.id,
            priority='高',
            status='issued',
            progress_percent=20,
            due_date=now + timedelta(hours=8),
            result_summary='待验证',
        )
        task.set_helper_ids([other_user.id] if other_user.id != admin.id else [])
        db.session.add(task)
        db.session.flush()
        CREATED['task_ids'].append(task.id)
        db.session.add(SupervisionProgress(
            task_id=task.id,
            operator_id=admin.id,
            action='create',
            progress_percent=20,
            note='回归验证初始化数据',
        ))

        period = PerformancePeriod(
            name=f'回归周期-{suffix}',
            period_type=f'regression-{suffix}',
            start_date=now.date(),
            end_date=(now + timedelta(days=7)).date(),
            status='active',
            remark='办公协同回归验证专用',
            created_by=admin.id,
        )
        db.session.add(period)
        db.session.flush()
        CREATED['period_ids'].append(period.id)

        record = PerformanceAssessment(
            period_id=period.id,
            user_id=admin.id,
            assessor_id=admin.id,
            project_name=f'办公协同回归绩效-{suffix}',
            category='重点工作',
            score=96,
            full_score=100,
            weight=1,
            evaluation='初始发布记录，用于验证编辑与撤回。',
            highlights='高分样本',
            status='published',
        )
        db.session.add(record)
        db.session.flush()
        CREATED['record_ids'].append(record.id)

        returned_log = WorkLog(
            user_id=admin.id,
            log_date=now.date(),
            title=f'回归退回日志-{suffix}',
            category='日常工作',
            content='用于验证工作台提醒与快捷筛选 returned',
            achievements='待修改',
            issues='需要补充说明',
            tomorrow_plan='重新提交',
            hours=6,
            status='returned',
            related_task_id=task.id,
        )
        review_log = WorkLog(
            user_id=admin.id,
            log_date=now.date(),
            title=f'回归待阅日志-{suffix}',
            category='重点工作',
            content='用于验证管理端 need_review',
            achievements='已完成验证准备',
            issues='',
            tomorrow_plan='继续回归',
            hours=7.5,
            status='submitted',
            related_task_id=task.id,
        )
        db.session.add(returned_log)
        db.session.add(review_log)
        db.session.flush()
        CREATED['log_ids'].extend([returned_log.id, review_log.id])

        db.session.commit()
        ok('初始化测试数据', f'meeting={meeting.id}, task={task.id}, period={period.id}, record={record.id}')

        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess['_user_id'] = str(admin.id)
                sess['_fresh'] = True

            dashboard_resp = client.get('/official_doc/dashboard')
            check_response(
                'GET /official_doc/dashboard',
                dashboard_resp,
                expected=(200,),
                body_contains=['待办提醒聚合', '待办总数', '会议待跟进', '日志待处理']
            )
            csrf_token = _extract_csrf_token(dashboard_resp)


            check_response('GET /meeting?quick=today', client.get('/meeting?quick=today'), expected=(200,), body_contains=['待反馈会议'])
            check_response('GET /meeting?quick=need_signin', client.get('/meeting?quick=need_signin'), expected=(200,))
            check_response('GET /meeting?quick=pending_feedback', client.get('/meeting?quick=pending_feedback'), expected=(200,))
            check_response('GET /meeting/edit/<id>', client.get(f'/meeting/edit/{meeting.id}'), expected=(200,), body_contains=['编辑会议', '提交发布'])

            meeting_edit_resp = client.post(
                f'/meeting/edit/{meeting.id}',
                data={
                    'csrf_token': csrf_token,
                    'subject': f'办公协同回归会议-已编辑-{suffix}',
                    'meeting_type': '项目推进会',

                    'level': '单位级',
                    'priority': '紧急',
                    'start_time': (now + timedelta(hours=4)).strftime('%Y-%m-%dT%H:%M'),
                    'end_time': (now + timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M'),
                    'room_id': str(room.id),
                    'host_id': str(admin.id),
                    'attendee_depts': '办公室,综合科',
                    'attendee_ids': [str(uid) for uid in attendee_ids],
                    'require_signin': 'on',
                    'agenda': '编辑后再次验证会议时间回填与冲突排除',
                    'minutes': '编辑阶段纪要草稿',
                    'action': 'save',
                },
                follow_redirects=False,
            )
            check_response('POST /meeting/edit/<id>', meeting_edit_resp, expected=(302,))
            db.session.expire_all()
            meeting = db.session.get(Meeting, meeting.id)
            if meeting.subject != f'办公协同回归会议-已编辑-{suffix}' or meeting.priority != '紧急':
                fail('POST /meeting/edit/<id>', '会议编辑结果未落库')
            ok('会议编辑落库检查', meeting.subject)

            check_response('GET /supervision', client.get('/supervision?quick=high_priority'), expected=(200,), body_contains=['批量催办'])
            check_response('GET /supervision?quick=my_due_soon', client.get('/supervision?quick=my_due_soon'), expected=(200,))
            check_response('GET /supervision/edit/<id>', client.get(f'/supervision/edit/{task.id}'), expected=(200,), body_contains=['编辑督办任务'])

            supervision_edit_resp = client.post(
                f'/supervision/edit/{task.id}',
                data={
                    'csrf_token': csrf_token,
                    'title': f'办公协同回归督办-已编辑-{suffix}',
                    'source': '会议决定',

                    'category': '专项整改',
                    'owner_id': str(admin.id),
                    'due_date': (now + timedelta(hours=10)).strftime('%Y-%m-%dT%H:%M'),
                    'priority': '高',
                    'content': '编辑后验证督办任务信息保存',
                    'helper_ids': [str(other_user.id)] if other_user.id != admin.id else [],
                    'result_summary': '编辑后的阶段性结果',
                    'action': 'save',
                },
                follow_redirects=False,
            )
            check_response('POST /supervision/edit/<id>', supervision_edit_resp, expected=(302,))
            db.session.expire_all()
            task = db.session.get(SupervisionTask, task.id)
            if task.title != f'办公协同回归督办-已编辑-{suffix}' or task.category != '专项整改':
                fail('POST /supervision/edit/<id>', '督办编辑结果未落库')
            ok('督办编辑落库检查', task.title)

            batch_remind_resp = client.post(
                '/supervision/batch_remind',
                data={'csrf_token': csrf_token, 'task_ids': [str(task.id)], 'note': '批量催办验证'},

                follow_redirects=False,
            )
            check_response('POST /supervision/batch_remind', batch_remind_resp, expected=(302,))
            remind_log = SupervisionProgress.query.filter_by(task_id=task.id, action='manual_remind').order_by(SupervisionProgress.id.desc()).first()
            if not remind_log or '批量催办验证' not in (remind_log.note or ''):
                fail('POST /supervision/batch_remind', '未生成批量催办留痕')
            ok('批量催办留痕检查', remind_log.note or '')

            close_resp = client.post(
                f'/supervision/close/{task.id}',
                data={'csrf_token': csrf_token, 'close_type': 'completed', 'note': '关闭验证', 'result_summary': '已完成回归验证'},
                follow_redirects=False,
            )
            check_response('POST /supervision/close/<id>', close_resp, expected=(302,))

            db.session.expire_all()
            task = db.session.get(SupervisionTask, task.id)
            if task.status != 'completed' or (task.progress_percent or 0) != 100:
                fail('POST /supervision/close/<id>', '关闭任务后状态不正确')
            ok('督办关闭落库检查', task.status)

            perf_resp = client.get('/performance')
            check_response('GET /performance', perf_resp, expected=(200,), body_contains=['个人维度趋势', '高低分预警'])
            check_response('GET /performance/edit/<id>', client.get(f'/performance/edit/{record.id}'), expected=(200,), body_contains=['编辑绩效记录'])

            performance_edit_resp = client.post(
                f'/performance/edit/{record.id}',
                data={
                    'csrf_token': csrf_token,
                    'period_id': str(period.id),
                    'user_id': str(admin.id),
                    'project_name': f'办公协同回归绩效-已编辑-{suffix}',

                    'category': '协同配合',
                    'score': '92',
                    'full_score': '100',
                    'weight': '1.2',
                    'evaluation': '编辑后验证绩效记录保存',
                    'highlights': '编辑后的亮点',
                    'action': 'save',
                },
                follow_redirects=False,
            )
            check_response('POST /performance/edit/<id>', performance_edit_resp, expected=(302,))
            db.session.expire_all()
            record = db.session.get(PerformanceAssessment, record.id)
            if record.project_name != f'办公协同回归绩效-已编辑-{suffix}' or record.score != 92:
                fail('POST /performance/edit/<id>', '绩效编辑结果未落库')
            ok('绩效编辑落库检查', record.project_name)

            retract_resp = client.post(
                f'/performance/retract/{record.id}',
                data={'csrf_token': csrf_token},
                follow_redirects=False,
            )

            check_response('POST /performance/retract/<id>', retract_resp, expected=(302,))
            db.session.expire_all()
            record = db.session.get(PerformanceAssessment, record.id)
            if record.status != 'draft':
                fail('POST /performance/retract/<id>', '绩效撤回后未转为草稿')
            ok('绩效撤回落库检查', record.status)

            periods_resp = client.get('/performance/periods')
            check_response('GET /performance/periods', periods_resp, expected=(200,))

            toggle_close_resp = client.post(
                f'/performance/period/toggle/{period.id}',
                data={'csrf_token': csrf_token, 'status': 'closed'},
                follow_redirects=False,
            )

            check_response('POST /performance/period/toggle closed', toggle_close_resp, expected=(302,))
            db.session.expire_all()
            period = db.session.get(PerformancePeriod, period.id)
            if period.status != 'closed':
                fail('POST /performance/period/toggle closed', '周期未关闭')
            ok('周期关闭落库检查', period.status)

            toggle_active_resp = client.post(
                f'/performance/period/toggle/{period.id}',
                data={'csrf_token': csrf_token, 'status': 'active'},

                follow_redirects=False,
            )
            check_response('POST /performance/period/toggle active', toggle_active_resp, expected=(302,))
            db.session.expire_all()
            period = db.session.get(PerformancePeriod, period.id)
            if period.status != 'active':
                fail('POST /performance/period/toggle active', '周期未重新启用')
            ok('周期启用落库检查', period.status)

            check_response('GET /worklog?quick=today', client.get('/worklog?quick=today'), expected=(200,))
            check_response('GET /worklog?quick=returned', client.get('/worklog?quick=returned'), expected=(200,))
            check_response('GET /worklog?quick=task_related', client.get('/worklog?quick=task_related'), expected=(200,))
            check_response('GET /worklog?quick=need_review', client.get('/worklog?quick=need_review'), expected=(200,))

            cancel_resp = client.post(
                f'/meeting/status/{meeting.id}',
                data={'csrf_token': csrf_token, 'action': 'cancel'},

                follow_redirects=False,
            )
            check_response('POST /meeting/status cancel', cancel_resp, expected=(302,))
            db.session.expire_all()
            meeting = db.session.get(Meeting, meeting.id)
            if meeting.status != 'cancelled':
                fail('POST /meeting/status cancel', '会议未取消')
            ok('会议取消落库检查', meeting.status)


        print('办公协同回归验证通过')
        for item in RESULTS:
            prefix = 'PASS' if item['ok'] else 'FAIL'
            extra = f" | {item['extra']}" if item.get('extra') else ''
            print(f'[{prefix}] {item["name"]}{extra}')
        print(f'共通过 {len(RESULTS)} 项检查')

    except Exception as exc:
        print('办公协同回归验证失败')
        print(str(exc))
        print(traceback.format_exc())
        raise

    finally:
        try:
            db.session.rollback()
            for log_id in CREATED['log_ids']:
                obj = db.session.get(WorkLog, log_id)
                if obj:
                    db.session.delete(obj)
            for record_id in CREATED['record_ids']:
                obj = db.session.get(PerformanceAssessment, record_id)
                if obj:
                    db.session.delete(obj)
            for period_id in CREATED['period_ids']:
                obj = db.session.get(PerformancePeriod, period_id)
                if obj:
                    db.session.delete(obj)
            for task_id in CREATED['task_ids']:
                obj = db.session.get(SupervisionTask, task_id)
                if obj:
                    db.session.delete(obj)
            for meeting_id in CREATED['meeting_ids']:
                obj = db.session.get(Meeting, meeting_id)
                if obj:
                    db.session.delete(obj)
            for room_id in CREATED['room_ids']:
                obj = db.session.get(MeetingRoom, room_id)
                if obj:
                    db.session.delete(obj)
            db.session.commit()

        except Exception:
            db.session.rollback()
            print('清理测试数据失败，请人工检查。')
            print(traceback.format_exc())
            raise
