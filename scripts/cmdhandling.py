import sys, os, re, subprocess, signal
import time

def exec_cmd(cmd, output=True, timeout=0):
    print('Exec: ', cmd)
    if output:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE, preexec_fn=os.setsid)
        out = proc.communicate()
        stdout = out[0].decode('utf-8')
        stderr = out[1].decode('utf-8')
        if proc.returncode != 0:
            sys.exit('Failed to execute {cmd}'.format(cmd=cmd))
    else:
        proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
        if timeout != 0:
            time.sleep(timeout)
            kill_proc(proc)
        if proc.returncode != 0:
            sys.exit('Failed to execute {cmd}'.format(cmd=cmd))
        stdout = stderr = ''
    return proc, stdout, stderr

def kill_proc(proc):
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
