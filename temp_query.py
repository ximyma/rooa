import sqlite3
conn = sqlite3.connect('instance/oa.db')
c = conn.cursor()
c.execute("SELECT DISTINCT column_category FROM monitor_results WHERE date(monitor_time)=date('now') LIMIT 30")
for row in c.fetchall():
    print(repr(row[0]))
conn.close()
