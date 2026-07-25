#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库完整初始化脚本
确保所有表、默认数据都正确创建
"""
import os
import sys
import secrets
import string
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app import app, db
from werkzeug.security import generate_password_hash
from datetime import datetime, date
import json


def init_all_tables():
    """创建所有数据库表"""
    print("=" * 60)
    print("1. 创建数据库表")
    print("=" * 60)
    with app.app_context():
        db.create_all()
        print("✓ 所有表创建完成")
    print()


def init_admin_user():
    """初始化管理员用户"""
    print("=" * 60)
    print("2. 初始化管理员用户")
    print("=" * 60)
    from models import User
    
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            initial_password = os.environ.get('ADMIN_INITIAL_PASSWORD') or ''.join(
                secrets.choice(string.ascii_letters + string.digits) for _ in range(16)
            )
            admin = User(
                username='admin',
                password=generate_password_hash(initial_password),
                name='系统管理员',
                department='办公室',
                role='admin',
                is_reporter=True,
                is_receiver=True,
                is_active=True,
                gender='未知'
            )
            db.session.add(admin)
            db.session.commit()
            print(f"✓ 管理员用户创建成功")
            print(f"  用户名: admin")
            print(f"  初始密码: {initial_password}")
            print(f"  请登录后立即修改密码！")
        else:
            print("✓ 管理员用户已存在")
    print()


def init_roles():
    """初始化系统角色"""
    print("=" * 60)
    print("3. 初始化系统角色")
    print("=" * 60)
    from models import Role
    
    with app.app_context():
        if Role.query.count() == 0:
            default_roles = [
                Role(
                    name='admin',
                    display_name='系统管理员',
                    description='拥有所有权限',
                    is_system=True,
                    permissions=json.dumps([
                        'user_manage', 'role_manage', 'template_manage',
                        'report_view', 'report_manage', 'task_manage',
                        'knowledge_manage', 'ai_config', 'stats_view',
                        'operation_log', 'briefing_manage', 'archive_manage',
                        'meeting_manage', 'supervision_manage', 'performance_manage'
                    ], ensure_ascii=False)
                ),
                Role(
                    name='manager',
                    display_name='部门经理',
                    description='管理本部门事务，可查看统计',
                    is_system=True,
                    permissions=json.dumps([
                        'report_view', 'report_manage', 'task_manage',
                        'knowledge_manage', 'stats_view', 'briefing_manage'
                    ], ensure_ascii=False)
                ),
                Role(
                    name='reporter',
                    display_name='信息报送员',
                    description='负责信息上报和任务完成',
                    is_system=False,
                    permissions=json.dumps([
                        'report_view', 'report_submit', 'task_view',
                        'knowledge_view'
                    ], ensure_ascii=False)
                ),
                Role(
                    name='employee',
                    display_name='普通员工',
                    description='基础功能访问',
                    is_system=False,
                    permissions=json.dumps([
                        'report_view', 'knowledge_view'
                    ], ensure_ascii=False)
                ),
            ]
            for role in default_roles:
                db.session.add(role)
            db.session.commit()
            print(f"✓ {len(default_roles)} 个角色创建成功")
        else:
            print("✓ 角色已存在")
    print()


def init_organization():
    """初始化组织架构"""
    print("=" * 60)
    print("4. 初始化组织架构")
    print("=" * 60)
    from models import Organization, Department, Position, User
    
    with app.app_context():
        if Organization.query.count() == 0:
            # 创建根机构
            root_org = Organization(
                name='智能服务办公平台',
                short_name='本单位',
                code='ROOT',
                org_type='unit',
                level=1,
                sort_order=0,
                description='系统默认根机构'
            )
            db.session.add(root_org)
            db.session.flush()
            
            # 创建默认部门
            default_depts = [
                Department(name='办公室', code='OFFICE', org_id=root_org.id,
                          dept_type='functional', sort_order=1,
                          description='综合协调、文件收发、日常行政管理'),
                Department(name='人事部门', code='HR', org_id=root_org.id,
                          dept_type='functional', sort_order=2,
                          description='人员招聘、考核、培训及薪资管理'),
                Department(name='财务部门', code='FINANCE', org_id=root_org.id,
                          dept_type='functional', sort_order=3,
                          description='财务管理、预算执行、资产管理'),
                Department(name='业务部门', code='BUSINESS', org_id=root_org.id,
                          dept_type='business', sort_order=4,
                          description='核心业务开展与管理'),
                Department(name='信息技术部', code='IT', org_id=root_org.id,
                          dept_type='support', sort_order=5,
                          description='信息化建设与运维'),
            ]
            for dept in default_depts:
                db.session.add(dept)
            db.session.flush()
            
            # 创建默认岗位
            default_positions = []
            office_dept = next((d for d in default_depts if d.code == 'OFFICE'), None)
            hr_dept = next((d for d in default_depts if d.code == 'HR'), None)
            biz_dept = next((d for d in default_depts if d.code == 'BUSINESS'), None)
            finance_dept = next((d for d in default_depts if d.code == 'FINANCE'), None)
            it_dept = next((d for d in default_depts if d.code == 'IT'), None)
            
            if office_dept:
                default_positions += [
                    Position(name='系统管理员', code='ADMIN', dept_id=office_dept.id,
                            role_name='admin', level='manager', headcount=1,
                            description='负责系统运维和管理'),
                    Position(name='办公室主任', code='OFFICE_MGR', dept_id=office_dept.id,
                            role_name='manager', level='manager', headcount=1,
                            description='主持办公室全面工作'),
                    Position(name='文秘', code='SECRETARY', dept_id=office_dept.id,
                            role_name='reporter', level='staff', headcount=2,
                            description='负责公文起草、信息报送'),
                ]
            if hr_dept:
                default_positions += [
                    Position(name='人事主管', code='HR_MGR', dept_id=hr_dept.id,
                            role_name='manager', level='supervisor', headcount=1,
                            description='负责人事管理工作'),
                    Position(name='人事专员', code='HR_STAFF', dept_id=hr_dept.id,
                            role_name='employee', level='staff', headcount=2,
                            description='日常人事事务处理'),
                ]
            if finance_dept:
                default_positions += [
                    Position(name='财务主管', code='FINANCE_MGR', dept_id=finance_dept.id,
                            role_name='manager', level='supervisor', headcount=1,
                            description='负责财务管理工作'),
                    Position(name='财务专员', code='FINANCE_STAFF', dept_id=finance_dept.id,
                            role_name='employee', level='staff', headcount=2,
                            description='日常财务事务处理'),
                ]
            if biz_dept:
                default_positions += [
                    Position(name='业务经理', code='BIZ_MGR', dept_id=biz_dept.id,
                            role_name='manager', level='manager', headcount=1,
                            description='负责业务管理'),
                    Position(name='业务员', code='BIZ_STAFF', dept_id=biz_dept.id,
                            role_name='reporter', level='staff', headcount=5,
                            description='负责具体业务'),
                ]
            if it_dept:
                default_positions += [
                    Position(name='IT主管', code='IT_MGR', dept_id=it_dept.id,
                            role_name='manager', level='supervisor', headcount=1,
                            description='负责信息化建设'),
                    Position(name='IT专员', code='IT_STAFF', dept_id=it_dept.id,
                            role_name='employee', level='staff', headcount=2,
                            description='日常运维工作'),
                ]
            
            for pos in default_positions:
                db.session.add(pos)
            db.session.flush()
            
            # 更新admin用户关联
            admin = User.query.filter_by(username='admin').first()
            if admin and office_dept:
                admin.org_id = root_org.id
                admin.dept_id = office_dept.id
                admin_pos = next((p for p in default_positions if p.code == 'ADMIN'), None)
                if admin_pos:
                    admin.position_id = admin_pos.id
            
            db.session.commit()
            print(f"✓ 组织架构创建成功")
            print(f"  - 机构: 1 个")
            print(f"  - 部门: {len(default_depts)} 个")
            print(f"  - 岗位: {len(default_positions)} 个")
        else:
            print("✓ 组织架构已存在")
    print()


def init_personal_kb():
    """初始化用户个人知识库"""
    print("=" * 60)
    print("5. 初始化个人知识库")
    print("=" * 60)
    from models import User, KnowledgeBase
    
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if admin:
            personal_kb = KnowledgeBase.query.filter_by(
                owner_id=admin.id, type='personal'
            ).first()
            if not personal_kb:
                personal_kb = KnowledgeBase(
                    name=f"{admin.name}的个人知识库",
                    type='personal',
                    owner_id=admin.id,
                    category='个人文档',
                    description='个人文档存储空间'
                )
                db.session.add(personal_kb)
                db.session.commit()
                print(f"✓ 个人知识库创建成功")
            else:
                print("✓ 个人知识库已存在")
    print()


def init_doc_templates():
    """初始化公文模板"""
    print("=" * 60)
    print("6. 初始化公文模板")
    print("=" * 60)
    from models import DocTemplate, User
    
    with app.app_context():
        if DocTemplate.query.count() == 0:
            admin = User.query.filter_by(username='admin').first()
            default_templates = [
                DocTemplate(
                    name='请示（标准格式）',
                    category='请示',
                    file_type='txt',
                    description='标准行政请示文件格式',
                    tags='请示,行政,标准',
                    created_by=admin.id if admin else None,
                    content="""【发文机关】
    XXX单位

关于XXX的请示

XXX（上级机关）：

【正文】
一、事项说明
（说明请示事项的背景、原因及必要性）

二、请示内容
（具体的请示内容，要求明确、具体）

三、相关情况
（说明相关准备工作、方案等）

妥否，请批示。

                                XXX单位（盖章）
                                XXXX年XX月XX日"""
                ),
                DocTemplate(
                    name='报告（工作总结）',
                    category='报告',
                    file_type='txt',
                    description='工作总结报告格式',
                    tags='报告,总结,工作',
                    created_by=admin.id if admin else None,
                    content="""关于XXXX工作总结报告

XXX（上级机关）：

现将我单位XXXX工作情况报告如下：

一、主要工作完成情况
（说明本阶段主要工作的完成情况，包括具体数字、成效等）

二、主要做法和经验
（总结工作中的主要做法、好的经验和做法）

三、存在的问题和不足
（客观反映工作中存在的问题和短板）

四、下一步工作打算
（提出下一步工作思路和具体措施）

以上报告，请审阅。

                                XXX单位（盖章）
                                XXXX年XX月XX日"""
                ),
                DocTemplate(
                    name='通知（标准格式）',
                    category='通知',
                    file_type='txt',
                    description='行政通知标准格式',
                    tags='通知,行政',
                    created_by=admin.id if admin else None,
                    content="""关于XXXX的通知

各有关单位：

【正文】
根据XXX要求，现将有关事项通知如下：

一、XXXX
（通知内容第一条）

二、XXXX
（通知内容第二条）

三、其他事项
（其他需要说明的事项）

请各单位遵照执行，如有问题请及时联系。

联系人：XXX，联系电话：XXXXXXXX

                                XXX单位（盖章）
                                XXXX年XX月XX日"""
                ),
                DocTemplate(
                    name='函（商洽事项）',
                    category='函',
                    file_type='txt',
                    description='行政函件格式',
                    tags='函,商洽',
                    created_by=admin.id if admin else None,
                    content="""关于XXXX的函

XXX（对方单位）：

【正文】
为（目的/原因），现就XXX事项函告（或：商洽）如下：

一、XXXX

二、XXXX

请贵单位研究处理，并将处理结果函复。

                                XXX单位（盖章）
                                XXXX年XX月XX日"""
                ),
                DocTemplate(
                    name='会议纪要',
                    category='纪要',
                    file_type='txt',
                    description='会议纪要标准格式',
                    tags='会议,纪要',
                    created_by=admin.id if admin else None,
                    content="""XXX会议纪要

会议时间：XXXX年XX月XX日
会议地点：XXXXXX
主持人：XXX
参会人员：XXX、XXX、XXX
记录人：XXX

会议主要内容如下：

一、XXX情况通报
（通报相关情况）

二、研究讨论XXX事项
（会议讨论的主要事项及结论）

三、会议决定
1. XXX（具体决定事项）
2. XXX（具体决定事项）

四、其他事项
（其他讨论内容）

本纪要经与会人员审阅，如无异议，自发出之日起生效。"""
                ),
            ]
            for tmpl in default_templates:
                db.session.add(tmpl)
            db.session.commit()
            print(f"✓ {len(default_templates)} 个公文模板创建成功")
        else:
            print("✓ 公文模板已存在")
    print()


def init_briefing_data():
    """初始化简报系统数据"""
    print("=" * 60)
    print("7. 初始化简报系统数据")
    print("=" * 60)
    from models import BriefingSource, BriefingKeyword
    
    with app.app_context():
        if BriefingSource.query.count() == 0:
            default_sources = [
                BriefingSource(name='人民日报', url='http://paper.people.com.cn/rmrb/',
                              source_type='website', category='中央媒体', priority=1),
                BriefingSource(name='新华网', url='http://www.xinhuanet.com/',
                              source_type='website', category='中央媒体', priority=2),
                BriefingSource(name='央视新闻', url='http://www.cctv.com/',
                              source_type='website', category='中央媒体', priority=3),
                BriefingSource(name='中国政府网', url='http://www.gov.cn/',
                              source_type='website', category='政府网站', priority=4),
                BriefingSource(name='光明日报', url='https://www.gmw.cn/',
                              source_type='website', category='中央媒体', priority=5),
            ]
            for src in default_sources:
                db.session.add(src)
            db.session.commit()
            print(f"✓ {len(default_sources)} 个简报数据源创建成功")
        else:
            print("✓ 简报数据源已存在")
        
        if BriefingKeyword.query.count() == 0:
            default_keywords = [
                BriefingKeyword(text='经济', category='经济', color='#e74c3c'),
                BriefingKeyword(text='科技', category='科技', color='#3498db'),
                BriefingKeyword(text='民生', category='民生', color='#2ecc71'),
                BriefingKeyword(text='教育', category='教育', color='#f39c12'),
                BriefingKeyword(text='乡村振兴', category='农业', color='#27ae60'),
                BriefingKeyword(text='改革', category='政策', color='#8e44ad'),
                BriefingKeyword(text='创新', category='科技', color='#2980b9'),
                BriefingKeyword(text='安全', category='安全', color='#95a5a6'),
            ]
            for kw in default_keywords:
                db.session.add(kw)
            db.session.commit()
            print(f"✓ {len(default_keywords)} 个简报关键词创建成功")
        else:
            print("✓ 简报关键词已存在")
    print()


def init_meeting_rooms():
    """初始化会议室"""
    print("=" * 60)
    print("8. 初始化会议室")
    print("=" * 60)
    from models import MeetingRoom, User
    
    with app.app_context():
        if MeetingRoom.query.count() == 0:
            admin = User.query.filter_by(username='admin').first()
            default_rooms = [
                MeetingRoom(
                    name='第一会议室',
                    location='3楼301',
                    capacity=20,
                    equipment='投影仪、白板、视频会议系统',
                    manager_id=admin.id if admin else None,
                    status='available',
                    remark='主会议室'
                ),
                MeetingRoom(
                    name='第二会议室',
                    location='3楼302',
                    capacity=10,
                    equipment='投影仪、白板',
                    manager_id=admin.id if admin else None,
                    status='available',
                    remark='小会议室'
                ),
                MeetingRoom(
                    name='多功能厅',
                    location='4楼401',
                    capacity=50,
                    equipment='投影仪、音响、舞台',
                    manager_id=admin.id if admin else None,
                    status='available',
                    remark='大型会议'
                ),
                MeetingRoom(
                    name='视频会议室',
                    location='4楼402',
                    capacity=15,
                    equipment='视频会议系统、投影仪',
                    manager_id=admin.id if admin else None,
                    status='available',
                    remark='远程会议专用'
                ),
            ]
            for room in default_rooms:
                db.session.add(room)
            db.session.commit()
            print(f"✓ {len(default_rooms)} 个会议室创建成功")
        else:
            print("✓ 会议室已存在")
    print()


def init_archive_data():
    """初始化档案数据"""
    print("=" * 60)
    print("9. 初始化档案系统数据")
    print("=" * 60)
    from archive_models import ArchiveFonds, ArchiveCatalog, ArchiveVolume, ArchiveFile
    import random
    
    with app.app_context():
        if ArchiveFonds.query.count() == 0:
            # 创建全宗
            fonds = ArchiveFonds(
                fonds_code='DATIAN',
                fonds_name='达天科技有限公司',
                fonds_type='企业',
                description='达天科技企业档案全宗',
                total_volumes=0,
                total_files=0,
                is_active=True
            )
            db.session.add(fonds)
            db.session.flush()
            
            # 创建目录
            catalogs = []
            catalog_names = [
                ('WL', '文书档案', '30年'),
                ('KJ', '科技档案', '永久'),
                ('KUAI', '会计档案', '30年'),
                ('RS', '人事档案', '永久'),
                ('HT', '合同档案', '30年'),
            ]
            for code, name, retention in catalog_names:
                cat = ArchiveCatalog(
                    fonds_id=fonds.id,
                    catalog_code=code,
                    catalog_name=name,
                    retention_period=retention
                )
                catalogs.append(cat)
                db.session.add(cat)
            db.session.flush()
            
            # 为文书档案创建年度子目录
            wl_catalog = catalogs[0]
            for year in [2022, 2023, 2024]:
                sub_cat = ArchiveCatalog(
                    fonds_id=fonds.id,
                    catalog_code=f'WL-{year}',
                    catalog_name=f'{year}年度文书',
                    parent_id=wl_catalog.id,
                    retention_period='30年'
                )
                db.session.add(sub_cat)
            db.session.flush()
            
            # 创建案卷
            volumes = []
            vol_titles = ['综合管理类', '人事劳资类', '财务会计类', '市场营销类', '技术研发类']
            for i, title in enumerate(vol_titles):
                vol = ArchiveVolume(
                    fonds_id=fonds.id,
                    catalog_id=catalogs[0].id,
                    volume_code=f'2024-{str(i+1).zfill(3)}',
                    volume_title=f'{title}第{i+1}卷',
                    volume_year=2024,
                    retention_period='30年',
                    security_level='公开',
                    responsibility='达天科技综合管理部',
                    storage_location=f'A-{str(random.randint(1,5)).zfill(2)}-{str(random.randint(1,20)).zfill(2)}'
                )
                volumes.append(vol)
                db.session.add(vol)
            db.session.flush()
            
            # 创建示例档案
            archive_titles = [
                '关于2024年度工作总结的通知',
                '关于表彰先进的报告',
                '关于人员招聘的请示',
                '设备采购合同',
                '场地租赁协议',
                '关于加强安全管理的通知',
                '年度财务审计报告',
                '新产品研发立项报告',
                '员工绩效考核办法',
                '办公室管理规定',
            ]
            keywords_list = [
                '通知,总结,年度',
                '表彰,先进,报告',
                '招聘,人员,请示',
                '设备,采购,合同',
                '场地,租赁,协议',
                '安全,管理,通知',
                '财务,审计,报告',
                '研发,立项,产品',
                '绩效,考核,员工',
                '办公,管理,规定',
            ]
            
            for i, (title, keywords) in enumerate(zip(archive_titles, keywords_list)):
                year = random.choice([2022, 2023, 2024])
                file_date = date(year, random.randint(1, 12), random.randint(1, 28))
                
                archive_file = ArchiveFile(
                    fonds_id=fonds.id,
                    catalog_id=catalogs[0].id,
                    volume_id=random.choice(volumes).id if random.random() > 0.3 else None,
                    file_code=f'{year}-{str(i+1).zfill(4)}',
                    title=title,
                    responsibility='达天科技综合管理部',
                    file_date=file_date,
                    file_year=year,
                    retention_period=random.choice(['永久', '30年', '10年']),
                    security_level=random.choice(['公开', '内部']),
                    archive_type=random.choice(['通知', '报告', '请示', '合同', '制度']),
                    page_count=random.randint(1, 50),
                    keywords=keywords,
                    content_text=f'这是{title}的正文内容...',
                    summary=f'{title}的主要内容摘要...',
                    is_digitized=True,
                    status='active'
                )
                db.session.add(archive_file)
            
            db.session.commit()
            
            # 更新统计
            fonds.total_volumes = ArchiveVolume.query.filter_by(fonds_id=fonds.id).count()
            fonds.total_files = ArchiveFile.query.filter_by(fonds_id=fonds.id).count()
            db.session.commit()
            
            print(f"✓ 档案数据创建成功")
            print(f"  - 全宗: 1 个")
            print(f"  - 目录: {ArchiveCatalog.query.filter_by(fonds_id=fonds.id).count()} 个")
            print(f"  - 案卷: {ArchiveVolume.query.filter_by(fonds_id=fonds.id).count()} 个")
            print(f"  - 档案: {ArchiveFile.query.filter_by(fonds_id=fonds.id).count()} 个")
        else:
            print("✓ 档案数据已存在")
    print()


def init_system_config():
    """初始化系统配置"""
    print("=" * 60)
    print("10. 初始化系统配置")
    print("=" * 60)
    from models import SystemConfig, User
    
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        configs_to_create = []
        
        # 系统基础配置
        configs_to_create.append({
            'config_key': 'system_name',
            'config_value': '智能服务办公平台',
            'config_type': 'string',
            'category': 'system',
            'description': '系统名称',
            'is_public': True,
            'sort_order': 1
        })
        
        # 知识库配置
        configs_to_create.append({
            'config_key': 'kb_max_file_size',
            'config_value': '104857600',  # 100MB
            'config_type': 'integer',
            'category': 'knowledge',
            'description': '知识库最大文件大小(字节)',
            'is_public': True,
            'sort_order': 10
        })
        configs_to_create.append({
            'config_key': 'kb_auto_extract',
            'config_value': 'true',
            'config_type': 'boolean',
            'category': 'knowledge',
            'description': '是否自动提取文件内容',
            'is_public': True,
            'sort_order': 11
        })
        
        # AI配置
        configs_to_create.append({
            'config_key': 'ai_default_model',
            'config_value': 'deepseek',
            'config_type': 'string',
            'category': 'ai',
            'description': '默认AI模型',
            'is_public': True,
            'sort_order': 20
        })
        configs_to_create.append({
            'config_key': 'ai_temperature',
            'config_value': '0.7',
            'config_type': 'float',
            'category': 'ai',
            'description': 'AI温度参数',
            'is_public': True,
            'sort_order': 21
        })
        
        # 上传配置
        configs_to_create.append({
            'config_key': 'upload_allowed_types',
            'config_value': 'pdf,doc,docx,xls,xlsx,ppt,pptx,txt,jpg,jpeg,png,gif',
            'config_type': 'string',
            'category': 'upload',
            'description': '允许上传的文件类型',
            'is_public': True,
            'sort_order': 30
        })
        
        # 安全配置
        configs_to_create.append({
            'config_key': 'security_password_min_length',
            'config_value': '6',
            'config_type': 'integer',
            'category': 'security',
            'description': '密码最小长度',
            'is_public': False,
            'sort_order': 40
        })
        configs_to_create.append({
            'config_key': 'security_session_timeout',
            'config_value': '1800',
            'config_type': 'integer',
            'category': 'security',
            'description': '会话超时时间(秒)',
            'is_public': False,
            'sort_order': 41
        })
        
        created_count = 0
        for config_data in configs_to_create:
            existing = SystemConfig.query.filter_by(config_key=config_data['config_key']).first()
            if not existing:
                config = SystemConfig(
                    **config_data,
                    updated_by=admin.id if admin else None
                )
                db.session.add(config)
                created_count += 1
        
        if created_count > 0:
            db.session.commit()
            print(f"✓ {created_count} 个系统配置项创建成功")
        else:
            print("✓ 系统配置已存在")
    print()


def perform_migrations():
    """执行数据库迁移和字段补充"""
    print("=" * 60)
    print("11. 执行数据库迁移")
    print("=" * 60)
    from models import CrawlerTask
    
    with app.app_context():
        try:
            # 检查crawler_tasks表是否有max_depth字段
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('crawler_tasks')]
            
            if 'max_depth' not in columns:
                db.session.execute(db.text("ALTER TABLE crawler_tasks ADD COLUMN max_depth INTEGER DEFAULT 3"))
                db.session.commit()
                print("✓ 添加crawler_tasks.max_depth字段成功")
            else:
                print("✓ crawler_tasks.max_depth字段已存在")
                
        except Exception as e:
            db.session.rollback()
            print(f"⚠  迁移检查: {str(e)}")
    print()


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "智能服务办公平台 - 数据库完整初始化" + " " * 10 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        # 执行所有初始化步骤
        init_all_tables()
        init_admin_user()
        init_roles()
        init_organization()
        init_personal_kb()
        init_doc_templates()
        init_briefing_data()
        init_meeting_rooms()
        init_archive_data()
        init_system_config()
        perform_migrations()
        
        # 完成总结
        print("=" * 60)
        print("✓ 数据库初始化完成!")
        print("=" * 60)
        print()
        print("管理员登录信息请查看上方输出")
        print("（密码为随机生成，请妥善保存！）")
        print()
        
    except Exception as e:
        print(f"\n✗ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
