import psutil
import time

g_pid_infos = {}

def print_proc():
    global g_pid_infos

    pidlist = psutil.pids()
    for pid in pidlist:
        if not g_pid_infos.has_key(pid):
            g_pid_infos[pid] = psutil.Process(int(pid))

        proc = g_pid_infos[pid]
        print round(proc.cpu_percent() / psutil.cpu_count(), 2)

print_proc()
time.sleep(5)
print_proc()
