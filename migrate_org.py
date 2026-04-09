"""
数据库迁移脚本：添加组织架构相关字段到 users 表
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from sqlalchemy import text

def migrate():
    with app.app_context():
        conn = db.engine.connect()
        
        # 检查 users 表已有字段
        result = conn.execute(text("PRAGMA table_info(users)"))
        existing = {row[1] for row in result}
        print(f"现有字段: {existing}")
        
        new_cols = [
            ("org_id", "INTEGER"),
            ("dept_id", "INTEGER"),
            ("position_id", "INTEGER"),
            ("employee_no", "VARCHAR(30)"),
            ("avatar", "VARCHAR(200)"),
            ("gender", "VARCHAR(5) DEFAULT '未知'"),
            ("is_active", "BOOLEAN DEFAULT 1"),
            ("remark", "VARCHAR(300)"),
        ]
        
        for col_name, col_type in new_cols:
            if col_name not in existing:
                try:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                    print(f"  ✅ 添加字段: users.{col_name}")
                except Exception as e:
                    print(f"  ⚠️ 跳过: users.{col_name} - {e}")
            else:
                print(f"  ⏭ 已存在: users.{col_name}")
        
        conn.commit()
        
        # 建新表（organizations, departments, positions）
        db.create_all()
        print("✅ 新表创建/确认完成")
        
        # 初始化默认组织架构（如果没有数据）
        from models import Organization, Department, Position, User
        from werkzeug.security import generate_password_hash
        
        if not Organization.query.first():
            root = Organization(name='本单位', short_name='本单位', code='ROOT',
                                org_type='unit', level=1, sort_order=0)
            db.session.add(root)
            db.session.flush()
            
            depts = [
                Department(name='办公室', code='OFFICE', org_id=root.id, dept_type='functional', sort_order=1),
                Department(name='人事部门', code='HR', org_id=root.id, dept_type='functional', sort_order=2),
                Department(name='财务部门', code='FINANCE', org_id=root.id, dept_type='functional', sort_order=3),
                Department(name='业务部门', code='BUSINESS', org_id=root.id, dept_type='business', sort_order=4),
                Department(name='信息技术部', code='IT', org_id=root.id, dept_type='support', sort_order=5),
            ]
            for d in depts:
                db.session.add(d)
            db.session.flush()
            
            office = next((d for d in depts if d.code=='OFFICE'), None)
            if office:
                positions = [
                    Position(name='系统管理员', code='ADMIN', dept_id=office.id, role_name='admin', level='manager', headcount=1),
                    Position(name='办公室主任', code='OFFICE_MGR', dept_id=office.id, role_name='manager', level='manager', headcount=1),
                    Position(name='文秘', code='SECRETARY', dept_id=office.id, role_name='reporter', level='staff', headcount=2),
                ]
                for p in positions:
                    db.session.add(p)
                db.session.flush()
                
                admin = User.query.filter_by(username='admin').first()
                if admin:
                    admin.org_id = root.id
                    admin.dept_id = office.id
                    admin.is_active = True
                    admin_pos = next((p for p in positions if p.code=='ADMIN'), None)
                    if admin_pos:
                        admin.position_id = admin_pos.id
            
            db.session.commit()
            print("✅ 默认组织架构初始化完成")
        else:
            print("⏭ 组织架构已存在，跳过初始化")
        
        print("\n🎉 迁移完成！")

if __name__ == '__main__':
    migrate()
