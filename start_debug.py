import subprocess, os, time, signal, sys

# Kill existing python processes
r = subprocess.run(['tasklist'], capture_output=True, text=True)
for line in r.stdout.split('\n'):
    parts = line.split()
    if len(parts) >= 2 and 'python' in parts[0].lower():
        try:
            pid = int(parts[1])
            os.kill(pid, signal.SIGTERM)
        except: pass
time.sleep(2)

# Start debug server
p = subprocess.Popen(
    [sys.executable, 'run_debug.py'],
    cwd=r'c:\Users\Administrator\Desktop\ooa',
    stdout=open(r'c:\Users\Administrator\Desktop\ooa\debug_out.log','w'),
    stderr=subprocess.STDOUT,
    text=True
)
time.sleep(5)
print('Server started PID:', p.pid)
