#!/usr/bin/python

import grp
import json
import os
import subprocess
import psutil
import threading
import time
import socket
import platform
import signal
import sys

#ServerIPAddr = 'http://10.0.218.196:5009/messages'
#ServerIPAddr = 'http://localhost:5009/messages'
ServerAddr = ''

USAGE_TIMEOUT = 60
USERPROC_TIMEOUT = 600
ALLPROC_TIMEOUT = 1200

SLEEP_DEBUG = 1

SLEEP_VMINFO = (86400 / SLEEP_DEBUG)
SLEEP_PROCESSINFO = (3600 / SLEEP_DEBUG)
SLEEP_USAGEINFO = (30 / SLEEP_DEBUG)

_MachineInformation = {}
_ResourceInformation = {}
_ProcessInformation = {}
_PackageInformation = []
_pidInfos = {}

# host name, ipaddress, packagelist, hwaddress, VM Specific Information
# installed package list
def retrieveInformationVM():
    global _MachineInformation

    while True:
        info = {}

        # get Host Name
        info['hostname'] = socket.gethostname()

        # get template name
        if os.path.isfile("/etc/hvmtemplates"):
            with open('/etc/hvmtemplates') as template_file:
                info['template'] = template_file.read()
        else:
            info['template'] = "Not Defined"

        # get Linux Distributions
        distid, distver, distnick = platform.linux_distribution()
        architect = platform.machine()
        distribution = [distid, distver, distnick, architect]
        info['machine'] = distribution

        # get Network Information

        IPAddr = 'undefined'
        HWAddr = 'undefined'
        netIfInfo = psutil.net_if_addrs()
        if 'eth0' in netIfInfo:
            addrs = netIfInfo['eth0']
            for addr in addrs:
                if addr.family == 2:
                    IPAddr = addr.address
                elif addr.family == 17:
                    HWAddr = addr.address

        info['ipaddr'] = IPAddr
        info['hwaddr'] = HWAddr

        _PackageInformation = []
        if distid == 'Ubuntu':
            packages = subprocess.check_output(["dpkg-query", "-W", "-f=${Package}\t${Version}\n"])
            packages = packages.replace('\r', '')
            packagelist = packages.split('\n')
            for index, package in enumerate(packagelist):
                package = package.split('\t')
                packagelist[index] = package

            _PackageInformation = packagelist
        elif distid == 'Fedora':
            packages = subprocess.check_output(["rpm", "-qa", "--qf", '%{NAME}\t%{VERSION}.%{RELEASE}.%{ARCH}\n'])
            packages = packages.replace('\r', '')
            packagelist = packages.split('\n')
            for index, package in enumerate(packagelist):
                package = package.split('\t')
                packagelist[index] = package
            _PackageInformation = packagelist

        _MachineInformation = info

        postVMInformation(_MachineInformation, 'Packages', _PackageInformation)

        time.sleep(SLEEP_VMINFO)

    pass

# process info
def retrieveInformationProcessUsage():
    global _ProcessInformation
    global _pidInfos

    while True:
        infos = {}
        pidlist = psutil.pids()
        # remove pid in _pidInfos
        for key, value in _pidInfos.items():
            if key not in pidlist:
                del _pidInfos[key]

        # add pid in _pidInfos
        for pid in pidlist:
            if not _pidInfos.has_key(pid):
                try:
                    _pidInfos[pid] = psutil.Process(int(pid))
                except:
                    pass

            if _pidInfos.has_key(pid):
                proc = _pidInfos[pid]
                vmem = proc.memory_info()
                pinfo = {'name':proc.name(), 'cpu':proc.cpu_percent(), 'mem':[vmem.rss, vmem.vms], 'user':proc.username(), "created":proc.create_time()}
                infos[pid] = pinfo

        _ProcessInformation = infos

        postVMInformation(_MachineInformation, "Process", _ProcessInformation)

        time.sleep(SLEEP_PROCESSINFO)
    pass

# CPU / resource information
def retrieveInformationUsage():
    global _ResourceInformation

    while True:
        info = {}

        # get CPU usage
        cpulist = []
        cpu_usages = psutil.cpu_times_percent(None, True)
        for cpu in cpu_usages:
            cpuinfo = [cpu.system, cpu.user, cpu.idle, cpu.iowait, cpu.irq, cpu.softirq]
            cpulist.append(cpuinfo)
        info['cpu'] = cpulist

        # get Network IO
        netiocount = psutil.net_io_counters()
        packetinfo = [netiocount.packets_sent, netiocount.packets_recv]
        info['net'] = packetinfo

        # get Memory usage
        vMem = psutil.virtual_memory()
        info['mem'] = [vMem.used, vMem.free, vMem.total]

        # get disk space
        disk = psutil.disk_usage('/')
        info['disk'] = [disk.used, disk.free, disk.total]

        # get registered user
        registered_users = []
        grplist = grp.getgrall()
        for group in grplist:
            if group.gr_name == 'developer':
                registered_users = group.gr_mem

        userinfo = {}
        if len(registered_users) > 0:
            for reg_user in registered_users:
                if not userinfo.has_key(reg_user):
                    userinfo[reg_user] = []
        else:
            import pwd
            for p in pwd.getpwall():
                if p.pw_uid >= 1000:
                    if not userinfo.has_key(p[0]):
                        userinfo[p[0]] = []

        connected_user = psutil.users()

        for con_user in connected_user:
            if userinfo.has_key(con_user.name):
                userinfo[con_user.name].append([con_user.host, con_user.terminal])
        info['user'] = userinfo

        _ResourceInformation = info

        postVMInformation(_MachineInformation, "Usage", _ResourceInformation)

        time.sleep(SLEEP_USAGEINFO)
    pass

def postVMInformation(vmInfo, infoType = None, addtionalInfo = None):
    global ServerAddr

    sendData = {}
    sendData['VMInfo'] = vmInfo
    if infoType is not None:
        sendData[infoType] = addtionalInfo

    jsondata = json.dumps(sendData)
    try:
        subprocess.call(['curl', '-H', 'Content-type: application/json', '-X', 'POST', ServerAddr, '-d', jsondata])
    except:
        pass

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "usage : system_monitor.py [url]"
        exit()

    ServerAddr = sys.argv[1]

    threadProcList = [
        retrieveInformationVM,
        retrieveInformationProcessUsage,
        retrieveInformationUsage
    ]

    thread = []
    for index, proc in enumerate(threadProcList):
        thread.append(threading.Thread(target=proc))
        thread[index].start()

    for proc in thread:
        proc.join()
