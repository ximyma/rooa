"""
全面初始化测试数据脚本
覆盖：角色、用户、公文模板、电子公文、统计数据、操作日志、简报、专报等
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import (
    User, Role, DocTemplate, SystemOperationLog, SystemUsageStat,
    OfficialDoc, DocFlow, DocReadRecord,
    SpecialReport, AssignmentTask, KnowledgeBase, KnowledgeFile,
    ChatSession, ChatMessage, AIModelConfig
)
from datetime import datetime, timedelta
import json
import random


def run():
    with app.app_context():
        print("=" * 60)
        print("开始初始化测试数据...")
        print("=" * 60)

        # ==================== 1. 初始化角色 ====================
        print("\n[1/8] 初始化角色权限...")
        default_roles = [
            {
                'name': 'admin',
                'display_name': '系统管理员',
                'description': '拥有所有权限，负责系统维护和用户管理',
                'is_system': True,
                'permissions': [
                    'user_manage', 'role_manage', 'template_manage', 'operation_log',
                    'ai_config', 'report_view', 'report_submit', 'report_manage',
                    'task_view', 'task_manage', 'knowledge_view', 'knowledge_manage',
                    'stats_view', 'briefing_manage'
                ]
            },
            {
                'name': 'manager',
                'display_name': '部门经理',
                'description': '负责审核专报、管理约稿任务，查看统计数据',
                'is_system': True,
                'permissions': [
                    'report_view', 'report_submit', 'report_manage',
                    'task_view', 'task_manage', 'knowledge_view', 'knowledge_manage',
                    'stats_view', 'template_manage', 'briefing_manage'
                ]
            },
            {
                'name': 'reporter',
                'display_name': '信息报送员',
                'description': '负责日常信息上报和任务处理',
                'is_system': True,
                'permissions': [
                    'report_view', 'report_submit', 'task_view', 'knowledge_view'
                ]
            },
            {
                'name': 'employee',
                'display_name': '普通员工',
                'description': '基础功能使用，含AI写作、知识库查阅',
                'is_system': True,
                'permissions': ['knowledge_view', 'task_view']
            },
        ]
        for rd in default_roles:
            r = Role.query.filter_by(name=rd['name']).first()
            if not r:
                r = Role(name=rd['name'], display_name=rd['display_name'],
                         description=rd['description'], is_system=rd['is_system'])
                db.session.add(r)
            else:
                r.display_name = rd['display_name']
                r.description = rd['description']
                r.is_system = rd['is_system']
            r.set_permissions(rd['permissions'])
        db.session.commit()
        print(f"  ✓ 角色初始化完成（{len(default_roles)} 个）")

        # ==================== 2. 初始化测试用户 ====================
        print("\n[2/8] 初始化测试用户...")
        from werkzeug.security import generate_password_hash
        test_users = [
            {'username': 'admin',    'password': 'admin123',    'role': 'admin',    'is_receiver': True,  'department': '系统管理部'},
            {'username': 'manager1', 'password': 'manager123',  'role': 'manager',  'is_receiver': True,  'department': '办公室'},
            {'username': 'reporter1','password': 'report123',   'role': 'reporter', 'is_receiver': False, 'department': '财务科'},
            {'username': 'reporter2','password': 'report123',   'role': 'reporter', 'is_receiver': False, 'department': '人事科'},
            {'username': 'employee1','password': 'emp123',      'role': 'employee', 'is_receiver': False, 'department': '技术部'},
        ]
        created_users = 0
        for ud in test_users:
            u = User.query.filter_by(username=ud['username']).first()
            if not u:
                u = User(
                    username=ud['username'],
                    password=generate_password_hash(ud['password']),
                    role=ud['role'],
                    is_receiver=ud['is_receiver'],
                    department=ud.get('department', '')
                )
                db.session.add(u)
                created_users += 1
            else:
                u.role = ud['role']
                u.is_receiver = ud['is_receiver']
                if not hasattr(u, 'department') or not u.department:
                    try:
                        u.department = ud.get('department', '')
                    except:
                        pass
        db.session.commit()
        print(f"  ✓ 用户初始化完成（新建 {created_users} 个，共 {User.query.count()} 个）")

        # ==================== 3. 初始化公文模板 ====================
        print("\n[3/8] 初始化公文模板...")
        admin_user = User.query.filter_by(username='admin').first()
        
        template_data = [
            {
                'name': '请示（标准格式）',
                'category': '上行文',
                'description': '用于向上级机关请求指示或批准事项的标准公文格式',
                'tags': '请示,上行文,申请',
                'sort_order': 10,
                'content': '''【标题】
[发文机关名称]关于[请示事由]的请示

【主送机关】
[上级主管机关名称]：

【正文】
[说明请示的原因、依据和背景]

[阐述请示的具体事项和理由]

[提出具体请求]

妥否，请批示。

[发文机关名称]（印章）
[成文日期]

【附注】
联系人：[姓名]  联系电话：[电话号码]
'''
            },
            {
                'name': '工作报告（标准格式）',
                'category': '上行文',
                'description': '用于向上级汇报工作情况、反映问题的标准报告格式',
                'tags': '报告,总结,汇报,上行文',
                'sort_order': 9,
                'content': '''【标题】
[发文机关名称]关于[报告事由]的报告

【主送机关】
[上级主管机关名称]：

【正文】

一、工作概况
[简要说明工作总体情况]

二、主要工作及成效
（一）[工作一]
[具体内容描述]

（二）[工作二]
[具体内容描述]

三、存在的问题
[客观说明存在的问题]

四、下一步工作打算
[提出下阶段工作计划]

以上报告，请予审阅。

[发文机关名称]（印章）
[成文日期]
'''
            },
            {
                'name': '通知（标准格式）',
                'category': '下行文',
                'description': '用于布置工作、传达事项的标准通知格式',
                'tags': '通知,下行文,布置工作',
                'sort_order': 10,
                'content': '''【标题】
关于[通知事由]的通知

【主送机关】
各[单位/部门]：

【正文】
[说明通知的背景和目的]

现将有关事项通知如下：

一、[事项一]
[具体内容]

二、[事项二]
[具体内容]

三、工作要求
（一）各单位要高度重视，认真落实。
（二）如有疑问，请及时与[联系人/联系部门]联系。

[发文机关名称]（印章）
[成文日期]
'''
            },
            {
                'name': '函（标准格式）',
                'category': '平行文',
                'description': '用于不相隶属机关之间商洽工作、询问和答复问题的公文格式',
                'tags': '函,平行文,商洽',
                'sort_order': 8,
                'content': '''【标题】
[发文机关名称]关于[事由]的函

【主送机关】
[收文机关名称]：

【正文】
[说明发函的背景和目的]

[阐明商洽的具体事项]

[提出希望或要求]

请予研究，并将有关情况函复我[机关]。

[发文机关名称]（印章）
[成文日期]
'''
            },
            {
                'name': '会议纪要（标准格式）',
                'category': '纪要',
                'description': '记录会议主要议题、讨论情况和决定事项的公文格式',
                'tags': '会议纪要,纪要,决议',
                'sort_order': 8,
                'content': '''[会议名称]纪要

[会议时间]，[会议地点]召开了[会议名称]。[主持人]主持会议，[参会人员]参加了会议。

会议听取了[汇报人]关于[议题]的汇报，与会人员进行了讨论。现将会议主要内容纪要如下：

一、关于[议题一]
[会议讨论情况和形成的意见]

二、关于[议题二]
[会议讨论情况和形成的意见]

三、会议要求
[会议提出的工作要求]

[会议主办单位]（印章）
[成文日期]
'''
            },
            {
                'name': '批复（标准格式）',
                'category': '下行文',
                'description': '用于答复下级机关请示事项的公文格式',
                'tags': '批复,下行文,答复',
                'sort_order': 7,
                'content': '''【标题】
关于[批复内容]的批复

【主送机关】
[请示单位名称]：

【正文】
你[单位]《关于[请示事由]的请示》（[文件编号]）收悉。

[表明对请示的总体态度]

[针对请示的具体事项逐条批复]

此复。

[发文机关名称]（印章）
[成文日期]
'''
            },
            {
                'name': '意见（标准格式）',
                'category': '下行文',
                'description': '用于对重要问题提出见解和处理办法的公文格式',
                'tags': '意见,下行文,部署',
                'sort_order': 7,
                'content': '''【标题】
关于[事由]的意见

【主送机关】
各[单位/部门]：

【正文】
[说明提出意见的背景和依据]

[阐述问题的现状和重要性]

现提出如下意见：

一、总体要求
[总体目标和工作要求]

二、重点工作
（一）[工作一]
[具体要求]

（二）[工作二]
[具体要求]

三、保障措施
[组织保障、制度保障等]

[发文机关名称]（印章）
[成文日期]
'''
            },
            {
                'name': '年度工作总结',
                'category': '通用',
                'description': '年度工作总结的通用模板，适用于部门和个人',
                'tags': '总结,年度总结,工作汇报',
                'sort_order': 6,
                'content': '''[年份]年度工作总结

[单位/部门名称]

一、年度工作概况
[简要介绍年度整体工作情况]

二、主要工作成效
（一）[工作一]
[工作情况、取得成绩]

（二）[工作二]
[工作情况、取得成绩]

（三）[工作三]
[工作情况、取得成绩]

三、主要经验做法
[总结成功经验和有效做法]

四、存在的不足
[客观分析工作中存在的问题]

五、[年份+1]年工作打算
（一）[重点工作一]
（二）[重点工作二]
（三）[重点工作三]

[撰写人]
[日期]
'''
            },
        ]
        
        new_templates = 0
        for td in template_data:
            existing = DocTemplate.query.filter_by(name=td['name']).first()
            if not existing:
                tpl = DocTemplate(
                    name=td['name'],
                    category=td['category'],
                    description=td['description'],
                    tags=td.get('tags', ''),
                    sort_order=td.get('sort_order', 0),
                    content=td['content'],
                    file_type='txt',
                    is_active=True,
                    use_count=random.randint(5, 80),
                    created_by=admin_user.id if admin_user else None,
                    updated_by=admin_user.id if admin_user else None,
                )
                db.session.add(tpl)
                new_templates += 1
        db.session.commit()
        print(f"  ✓ 公文模板初始化完成（新建 {new_templates} 个，共 {DocTemplate.query.count()} 个）")

        # ==================== 4. 初始化电子公文测试数据 ====================
        print("\n[4/8] 初始化电子公文...")
        admin = User.query.filter_by(username='admin').first()
        manager = User.query.filter_by(username='manager1').first()
        reporter = User.query.filter_by(username='reporter1').first()
        
        if admin and OfficialDoc.query.count() == 0:
            docs_data = [
                {
                    'title': '关于开展2026年度安全生产专项检查的通知',
                    'doc_type': '通知', 'urgency': '普通', 'secrecy': '普通',
                    'status': 'sent',
                    'content': '各部门：\n\n根据上级部门工作部署，决定于2026年4月开展年度安全生产专项检查工作。现将有关事项通知如下：\n\n一、检查范围：全局各部门、直属单位\n二、检查时间：2026年4月15日-4月30日\n三、检查重点：安全生产制度落实、设备安全管理、应急预案等\n\n各部门要高度重视，认真做好自查自纠工作。\n\n办公室\n2026年3月31日',
                    'sender_dept': '办公室',
                    'days_ago': 1
                },
                {
                    'title': '关于请示购置办公设备的请示',
                    'doc_type': '请示', 'urgency': '普通', 'secrecy': '普通',
                    'status': 'approved',
                    'content': '局领导：\n\n现有打印机等办公设备已使用超过8年，故障频发，严重影响工作效率。为保障日常工作正常开展，特申请购置：打印机2台、扫描仪1台、复印机1台，预计费用约3.8万元。\n\n妥否，请批示。\n\n财务科\n2026年3月28日',
                    'sender_dept': '财务科',
                    'days_ago': 3
                },
                {
                    'title': '2026年第一季度工作总结报告',
                    'doc_type': '报告', 'urgency': '普通', 'secrecy': '内部',
                    'status': 'archived',
                    'content': '局领导：\n\n2026年第一季度，本部门在局党委的正确领导下，圆满完成各项工作任务。现将一季度工作情况报告如下：\n\n一、主要工作完成情况\n（一）制度建设：完成6项管理制度修订\n（二）项目推进：3个重点项目按期推进\n（三）队伍建设：组织培训8次，培训人次达320\n\n二、存在问题\n人员紧缺，部分工作压力较大。\n\n三、下季度工作计划\n继续推进各项重点工作，加强服务质量提升。\n\n人事科\n2026年3月30日',
                    'sender_dept': '人事科',
                    'days_ago': 1
                },
                {
                    'title': '关于调整部分岗位人员的函',
                    'doc_type': '函', 'urgency': '紧急', 'secrecy': '内部',
                    'status': 'pending_approval',
                    'content': '技术部：\n\n因工作需要，拟调整以下岗位人员配置，请协商处理：\n\n1. 将王某某调至信息中心任职\n2. 增补技术部后勤保障岗1人\n\n请研究并函复。\n\n办公室\n2026年3月31日',
                    'sender_dept': '办公室',
                    'days_ago': 0
                },
                {
                    'title': '关于举办政策法规学习培训的通知',
                    'doc_type': '通知', 'urgency': '普通', 'secrecy': '普通',
                    'status': 'sent',
                    'content': '各部门：\n\n为提升干部职工政策法规素养，决定举办2026年第一期政策法规专题培训班。\n\n培训时间：2026年4月8日（周三）上午9:00-12:00\n培训地点：三楼会议室\n培训内容：新修订《保密法》及相关配套规定解读\n参加对象：各部门分管领导及相关业务骨干\n\n请各部门于4月5日前将参训人员名单报送办公室。\n\n办公室\n2026年3月29日',
                    'sender_dept': '办公室',
                    'days_ago': 2
                },
            ]
            
            for i, dd in enumerate(docs_data):
                days = dd.pop('days_ago', 0)
                create_time = datetime.utcnow() - timedelta(days=days, hours=i*2)
                
                # 生成公文编号
                doc_no = f"办[2026]{(i+1):03d}号"
                
                doc = OfficialDoc(
                    doc_no=doc_no,
                    title=dd['title'],
                    doc_type=dd['doc_type'],
                    urgency=dd['urgency'],
                    secrecy=dd['secrecy'],
                    status=dd['status'],
                    content=dd['content'],
                    sender_id=admin.id,
                    sender_dept=dd['sender_dept'],
                    receiver_ids=json.dumps([manager.id] if manager else []),
                    created_at=create_time,
                    updated_at=create_time
                )
                db.session.add(doc)
                db.session.flush()
                
                # 添加流转记录
                flow = DocFlow(
                    doc_id=doc.id,
                    operator_id=admin.id,
                    action='submit',
                    opinion='提交审核',
                    created_at=create_time
                )
                db.session.add(flow)
                
                if dd['status'] in ('approved', 'sent', 'archived'):
                    flow2 = DocFlow(
                        doc_id=doc.id,
                        operator_id=manager.id if manager else admin.id,
                        action='approve',
                        opinion='审核通过，同意发送',
                        created_at=create_time + timedelta(hours=1)
                    )
                    db.session.add(flow2)
                
                if dd['status'] == 'archived':
                    flow3 = DocFlow(
                        doc_id=doc.id,
                        operator_id=admin.id,
                        action='archive',
                        opinion='归档保存',
                        created_at=create_time + timedelta(hours=3)
                    )
                    db.session.add(flow3)
            
            db.session.commit()
            print(f"  ✓ 电子公文初始化完成（新建 {len(docs_data)} 条）")
        else:
            print(f"  - 电子公文已有 {OfficialDoc.query.count()} 条，跳过")

        # ==================== 5. 初始化系统使用统计数据 ====================
        print("\n[5/8] 初始化统计数据...")
        modules = ['AI写作', '公文模板', 'AI对话', '知识库', '专报上报', '简报生成', '电子公文']
        actions = ['view', 'create', 'export']
        
        added_stats = 0
        for days_ago in range(30, -1, -1):
            stat_date = (datetime.utcnow() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            for mod in modules:
                for act in ['view', 'create']:
                    existing = SystemUsageStat.query.filter_by(
                        stat_date=stat_date, module=mod, action=act
                    ).first()
                    if not existing:
                        # 模拟真实使用趋势（工作日多、周末少）
                        d = datetime.utcnow() - timedelta(days=days_ago)
                        is_weekend = d.weekday() >= 5
                        base = random.randint(2, 15) if not is_weekend else random.randint(0, 4)
                        stat = SystemUsageStat(
                            stat_date=stat_date,
                            module=mod,
                            action=act,
                            count=base,
                            user_count=min(base, random.randint(1, 5))
                        )
                        db.session.add(stat)
                        added_stats += 1
        
        db.session.commit()
        print(f"  ✓ 统计数据初始化完成（新建 {added_stats} 条）")

        # ==================== 6. 初始化操作日志 ====================
        print("\n[6/8] 初始化操作日志...")
        if SystemOperationLog.query.count() < 10:
            log_samples = [
                ('admin', 'user_manage', 'create', '用户 reporter1', '创建新用户 reporter1，角色：信息报送员'),
                ('admin', 'user_manage', 'create', '用户 manager1', '创建新用户 manager1，角色：部门经理'),
                ('admin', 'role_manage', 'update', '角色 manager', '更新角色 manager 的权限配置'),
                ('admin', 'ai_config', 'create', 'AI配置', '新增AI模型配置'),
                ('manager1', 'report_manage', 'update', '专报审核', '审核通过专报《关于...》'),
                ('admin', 'template_manage', 'create', '公文模板', '新增模板：请示（标准格式）'),
                ('admin', '系统', 'login', '登录', '管理员登录系统'),
                ('manager1', '系统', 'login', '登录', '部门经理登录系统'),
                ('reporter1', 'report_submit', 'create', '信息上报', '提交信息：关于季度工作...'),
                ('admin', 'template_manage', 'create', '公文模板', '新增模板：会议纪要（标准格式）'),
            ]
            for i, (uname, module, action, target, detail) in enumerate(log_samples):
                u = User.query.filter_by(username=uname).first()
                log = SystemOperationLog(
                    user_id=u.id if u else None,
                    username=uname,
                    module=module,
                    action=action,
                    target=target,
                    detail=detail,
                    ip_addr='127.0.0.1',
                    created_at=datetime.utcnow() - timedelta(hours=i*3)
                )
                db.session.add(log)
            db.session.commit()
            print(f"  ✓ 操作日志初始化完成（新建 {len(log_samples)} 条）")
        else:
            print(f"  - 操作日志已有 {SystemOperationLog.query.count()} 条，跳过")

        # ==================== 7. 初始化AI配置 ====================
        print("\n[7/8] 初始化AI模型配置...")
        if AIModelConfig.query.count() == 0:
            configs = [
                {
                    'name': '通义千问（示例）',
                    'provider': 'openai',
                    'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
                    'api_key': 'sk-xxxx请替换为真实key',
                    'model_name': 'qwen-turbo',
                    'is_active': True,
                },
                {
                    'name': 'DeepSeek（示例）',
                    'provider': 'deepseek',
                    'api_base': 'https://api.deepseek.com/v1',
                    'api_key': 'sk-xxxx请替换为真实key',
                    'model_name': 'deepseek-chat',
                    'is_active': False,
                },
            ]
            for cd in configs:
                try:
                    cfg = AIModelConfig(
                        name=cd['name'],
                        provider=cd['provider'],
                        api_base=cd['api_base'],
                        api_key=cd['api_key'],
                        model_name=cd['model_name'],
                        is_active=cd['is_active'],
                    )
                    db.session.add(cfg)
                except Exception as e:
                    print(f"  ! AI配置创建跳过: {e}")
            try:
                db.session.commit()
                print(f"  ✓ AI配置初始化完成")
            except Exception as e:
                db.session.rollback()
                print(f"  ! AI配置初始化失败: {e}")
        else:
            print(f"  - AI配置已有 {AIModelConfig.query.count()} 条，跳过")

        # ==================== 8. 最终检查 ====================
        print("\n[8/8] 最终数据统计:")
        print(f"  角色:     {Role.query.count()} 个")
        print(f"  用户:     {User.query.count()} 个")
        print(f"  公文模板: {DocTemplate.query.count()} 个")
        print(f"  电子公文: {OfficialDoc.query.count()} 条")
        print(f"  统计数据: {SystemUsageStat.query.count()} 条")
        print(f"  操作日志: {SystemOperationLog.query.count()} 条")
        print(f"  AI配置:   {AIModelConfig.query.count()} 条")
        print(f"  专报:     {SpecialReport.query.count()} 条")
        print(f"  知识库:   {KnowledgeBase.query.count()} 个")

        print("\n" + "=" * 60)
        print("✅ 测试数据初始化完成！")
        print("=" * 60)


if __name__ == '__main__':
    run()
