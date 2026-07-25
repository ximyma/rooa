#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""数据完整性验证脚本（简化版，无特殊字符）"""

import os
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置 Flask 应用
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'verify-data-key-not-for-production'

# 先导入 models.py 中的 db，然后初始化
from models import db
db.init_app(app)

from models import (
    User, Role, Organization, Department, Position,
    KnowledgeBase, KnowledgeFile,
    BriefingSource, BriefingKeyword,
    DocTemplate,
    MeetingRoom,
    SystemConfig
)

try:
    from archive_models import ArchiveFonds, ArchiveCatalog, ArchiveVolume, ArchiveFile
    HAS_ARCHIVE = True
except Exception:
    HAS_ARCHIVE = False

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def verify_users():
    print_header("1. 验证用户数据")
    with app.app_context():
        users = User.query.all()
        print(f"总用户数: {len(users)}")
        
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print("OK: 管理员用户存在")
            print(f"  - 用户名: {admin.username}")
            print(f"  - 姓名: {admin.name}")
            print(f"  - 角色: {admin.role}")
            print(f"  - 部门: {admin.department}")
            if hasattr(admin, 'org_id') and admin.org_id:
                print(f"  - 所属机构ID: {admin.org_id}")
            if hasattr(admin, 'dept_id') and admin.dept_id:
                print(f"  - 所属部门ID: {admin.dept_id}")
            return True
        else:
            print("ERROR: 管理员用户不存在!")
            return False

def verify_roles():
    print_header("2. 验证角色数据")
    with app.app_context():
        roles = Role.query.all()
        print(f"总角色数: {len(roles)}")
        
        required_roles = ['admin', 'manager', 'reporter', 'employee']
        found_count = 0
        for role in roles:
            print(f"  - {role.name}: {role.display_name}")
            if role.name in required_roles:
                found_count += 1
        
        if found_count >= len(required_roles):
            print("OK: 所有必要角色都存在")
            return True
        else:
            print(f"ERROR: 缺少必要角色!")
            return False

def verify_organization():
    print_header("3. 验证组织架构数据")
    with app.app_context():
        org_count = Organization.query.count()
        dept_count = Department.query.count()
        pos_count = Position.query.count()
        
        print(f"机构数: {org_count}")
        print(f"部门数: {dept_count}")
        print(f"岗位数: {pos_count}")
        
        root_org = Organization.query.filter_by(code='ROOT').first()
        if root_org:
            print("OK: 根组织存在")
            return True
        else:
            print("ERROR: 根组织不存在!")
            return False

def verify_knowledge_bases():
    print_header("4. 验证知识库数据")
    with app.app_context():
        kb_count = KnowledgeBase.query.count()
        file_count = KnowledgeFile.query.count()
        
        print(f"知识库总数: {kb_count}")
        print(f"文件总数: {file_count}")
        
        admin = User.query.filter_by(username='admin').first()
        if admin:
            personal_kb = KnowledgeBase.query.filter_by(
                owner_id=admin.id, type='personal'
            ).first()
            if personal_kb:
                print(f"OK: 管理员个人知识库存在")
                return True
            else:
                print("ERROR: 管理员个人知识库不存在!")
                return False
        return False

def verify_doc_templates():
    print_header("5. 验证公文模板数据")
    with app.app_context():
        templates = DocTemplate.query.all()
        print(f"模板总数: {len(templates)}")
        
        if len(templates) >= 5:
            print("OK: 公文模板数据完整")
            return True
        else:
            print(f"ERROR: 公文模板数据不完整!")
            return False

def verify_briefing_data():
    print_header("6. 验证简报系统数据")
    with app.app_context():
        sources = BriefingSource.query.all()
        keywords = BriefingKeyword.query.all()
        
        print(f"数据源数: {len(sources)}")
        print(f"关键词数: {len(keywords)}")
        
        if len(sources) > 0 and len(keywords) > 0:
            print("OK: 简报数据完整")
            return True
        else:
            print("ERROR: 简报数据不完整!")
            return False

def verify_meeting_rooms():
    print_header("7. 验证会议室数据")
    with app.app_context():
        rooms = MeetingRoom.query.all()
        print(f"会议室总数: {len(rooms)}")
        
        if len(rooms) >= 4:
            print("OK: 会议室数据完整")
            return True
        else:
            print("ERROR: 会议室数据不完整!")
            return False

def verify_archive_data():
    print_header("8. 验证档案系统数据")
    if not HAS_ARCHIVE:
        print("SKIP: 档案模型未找到，跳过检查")
        return True
    with app.app_context():
        fonds_count = ArchiveFonds.query.count()
        catalog_count = ArchiveCatalog.query.count()
        volume_count = ArchiveVolume.query.count()
        file_count = ArchiveFile.query.count()
        
        print(f"全宗数: {fonds_count}")
        print(f"目录数: {catalog_count}")
        print(f"案卷数: {volume_count}")
        print(f"档案文件数: {file_count}")
        
        if fonds_count > 0 and catalog_count > 0 and file_count > 0:
            print("OK: 档案数据完整")
            return True
        else:
            print("ERROR: 档案数据不完整!")
            return False

def verify_system_config():
    print_header("9. 验证系统配置数据")
    with app.app_context():
        configs = SystemConfig.query.all()
        print(f"配置项总数: {len(configs)}")
        
        if len(configs) >= 8:
            print("OK: 系统配置完整")
            return True
        else:
            print("ERROR: 系统配置不完整!")
            return False

def verify_database_tables():
    print_header("10. 验证数据库表")
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"数据库表总数: {len(tables)}")
        required_tables = ['users', 'roles', 'knowledge_bases', 'doc_templates']
        found_count = 0
        
        for table in tables:
            if table in required_tables:
                print(f"  - 存在: {table}")
                found_count += 1
        
        if found_count >= len(required_tables):
            print("OK: 所有必要表都存在")
            return True
        else:
            print("ERROR: 缺少必要表!")
            return False

def main():
    print("\n")
    print("="*64)
    print("  智能服务办公平台 - 数据完整性验证")
    print("="*64)
    print("\n")
    
    results = {}
    
    with app.app_context():
        results['tables'] = verify_database_tables()
        results['users'] = verify_users()
        results['roles'] = verify_roles()
        results['org'] = verify_organization()
        results['kb'] = verify_knowledge_bases()
        results['templates'] = verify_doc_templates()
        results['briefing'] = verify_briefing_data()
        results['rooms'] = verify_meeting_rooms()
        results['archive'] = verify_archive_data()
        results['config'] = verify_system_config()
    
    # 统计结果
    print_header("验证结果汇总")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"通过: {passed}/{total} 项")
    
    all_passed = passed == total
    if all_passed:
        print("\nSUCCESS: 数据完整性验证通过！所有必要数据都已就绪。")
    else:
        print("\nWARNING: 数据完整性验证未完全通过！请检查上述错误。")
    
    return all_passed

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: 验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
