import os, signal, time, subprocess, sys

# Kill existing app processes
for proc in os.popen('tasklist /FI "IMAGENAME eq python.exe"').readlines():
    if 'python' in proc.lower():
        pid = proc.split()[1] if len(proc.split()) > 1 else None
        if pid and pid.isdigit():
            try:
                os.kill(int(pid), signal.SIGTERM)
                print(f'Killed PID {pid}')
            except:
                pass

time.sleep(2)

# Start new app
app_py = 'c:/Users/Administrator/Desktop/ooa/app.py'
log_file = open('c:/Users/Administrator/Desktop/ooa/app_out.log', 'a')
proc = subprocess.Popen(
    [sys.executable, app_py],
    cwd='c:/Users/Administrator/Desktop/ooa',
    stdout=log_file,
    stderr=subprocess.STDOUT
)
print(f'Started new app, PID {proc.pid}')
time.sleep(4)

# Quick test
import requests
base = 'http://127.0.0.1:5000'
try:
    r = requests.get(base + '/', timeout=5)
    print(f'Home: {r.status_code}')
    # Login
    session = requests.Session()
    resp = session.post(base + '/login', data={'username': 'admin', 'password': 'admin123'}, timeout=5)
    print(f'Login: {resp.status_code}')

    routes = ['/knowledge/personal', '/knowledge/api/search', '/knowledge/my_favorites', '/knowledge/recent', '/knowledge/shared', '/knowledge/api/search_page']
    for route in routes:
        try:
            r = session.get(base + route, timeout=5)
            print(f'{route}: {r.status_code}')
        except Exception as e:
            print(f'{route}: ERROR - {e}')
except Exception as e:
    print(f'Test error: {e}')
