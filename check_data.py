import sqlite3
conn = sqlite3.connect('instance/oa.db')
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in c.fetchall()]
print('Tables:', tables)

if 'users' in tables:
    c.execute("SELECT id, username, is_reporter FROM users WHERE username='admin'")
    print('Admin user:', c.fetchone())

if 'assignment_tasks' in tables:
    c.execute("SELECT id, title, status FROM assignment_tasks WHERE status='active' LIMIT 5")
    print('Active tasks:', c.fetchall())

if 'special_reports' in tables:
    c.execute("SELECT id, title, reporter_id FROM special_reports LIMIT 5")
    print('Special reports:', c.fetchall())

if 'doc_templates' in tables:
    c.execute("SELECT id, name, category FROM doc_templates WHERE is_active=1 LIMIT 5")
    print('Active templates:', c.fetchall())

conn.close()