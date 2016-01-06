#!/usr/bin/python
"""
    Monitor.py - VM Linux Server Monitoring scripts

    Needed Packages
        0. cURL
    Functions
        0. Register VM to VM Server Manager
            {
            }
        1. Support remote command call
            {
            }
        2. Gathering default VM Information
            {
            }
"""
import json
import os
import grp
import psutil
import socket
import platform

import sys
import flask
import threading
import subprocess
import time
import pwd

app = flask.Flask(__name__)

KEEP_ALIVE_TIMER = 60

def retrieveCommand(commandJson):
    if commandJson.has_key("command"):
        commandList = commandJson['command']
        try:
            output = subprocess.check_output(commandList)
        except:
            output = ""

        outputlist = output.splitlines()

        return {"result":outputlist}

    return {"result":""}

@app.route('/api/command', methods = ['GET'])
def api_message():

    if flask.request.headers['Content-Type'] == 'application/json':
        result = retrieveCommand(flask.request.json)
        return flask.jsonify(result)

    return flask.jsonify({})

@app.route('/api/pids', methods = ['GET'])
def retrieve_pids():
    infos = {}

    if flask.request.headers['Content-Type'] == 'application/json':
        pids = psutil.pids()
        for pid in pids:
            proc = psutil.Process(int(pid))
            vmem = proc.memory_info()
            pinfo = {'proc':proc, 'name':proc.name(), 'cpu':proc.cpu_percent(), 'mem':[vmem.rss, vmem.vms], 'user':proc.username(), 'created':proc.create_time()}
            infos[pid] = pinfo

        time.sleep(0.5)
        for key, value in infos.items():
            pinfo = infos[key]
            proc = pinfo['proc']
            vmem = proc.memory_info()
            pinfo = {'name':proc.name(), 'cpu':proc.cpu_percent(), 'mem':[vmem.rss, vmem.vms], 'user':proc.username(), 'created':proc.create_time()}
            infos[key] = pinfo

    return flask.jsonify(infos)

@app.route('/api/usage', methods = ['GET'])
def retrieve_usageInfo():
    if flask.request.headers['Content-Type'] == 'application/json':
        info = {}

        cpu_usages = psutil.cpu_times_percent(0.5, False)
        info['cpu'] = [cpu_usages.system, cpu_usages.user, cpu_usages.idle, cpu_usages.iowait, cpu_usages.irq, cpu_usages.softirq]
        memory = psutil.virtual_memory()
        info['mem'] = [memory.used, memory.free, memory.total]
        disk = psutil.disk_usage('/')
        info['disk'] = [disk.used, disk.free, disk.total]

        developerlist = []
        grplist = grp.getgrall()
        for group in grplist:
            if group.gr_name == 'developer':
                developerlist = group.gr_mem

        userlist = []
        for user in pwd.getpwall():
            if user.pw_uid >= 1000:
                userlist.append(user[0])

        users = {}
        allusers = list(set(developerlist + userlist))
        for user in allusers:
            users[user] = []

        connected = psutil.users()
        for user in connected:
            if users.has_key(user.name):
                users[user.name].append([user.host, user.terminal])

        info['users'] = users

        # idle user sessions
        try:
            output = subprocess.check_output(['w', '-hfs'])
        except:
            output = ""

        idlelist = []
        outlist = output.splitlines()
        for item in outlist:
            if 'days' in item:
                itemlist = item.split()
                idle = {"user":itemlist[0], "pts":itemlist[1], "idle":itemlist[2], "command":" ".join(itemlist[3:])}
                idlelist.append(idle)

        info['idle'] = idlelist

        return flask.jsonify(info)

    return flask.jsonify({})

# host name, ipaddress, packagelist, hwaddress, VM Specific Information
# installed package list
simpleVMInfo = {}
def keepAliveVM(serverAddr):
    global simpleVMInfo

    while True:
        if not simpleVMInfo.has_key('hostname'):
            simpleVMInfo['hostname'] = socket.gethostname()

        if not simpleVMInfo.has_key('template'):
            if os.path.isfile("/etc/hvmtemplates"):
                with open('/etc/hvmtemplates') as template_file:
                    simpleVMInfo['template'] = template_file.read()

        if not simpleVMInfo.has_key('machine'):
            distid, distver, distnick = platform.linux_distribution()
            architect = platform.machine()
            simpleVMInfo['machine'] = [distid, distver, distnick, architect]

        if not simpleVMInfo.has_key('network'):
            netIfInfo = psutil.net_if_addrs()
            if 'eth0' in netIfInfo:
                addrs = netIfInfo['eth0']
                for addr in addrs:
                    if addr.family == 2:
                        ipaddr = addr.address
                    elif addr.family == 17:
                        hwaddr = addr.address

            simpleVMInfo['network'] = [ipaddr or "0.0.0.0", hwaddr or "00:00:00:00:00:00"]

        jsondata = json.dumps(simpleVMInfo)
        try:
            subprocess.call(['curl', '-s', '-H', 'Content-type: application/json', '-X', 'POST', serverAddr, '-d', jsondata])
        except:
            pass

        time.sleep(KEEP_ALIVE_TIMER)


MonitorTitle = """
+-------------------------------------------------------+
|  Linux VM Monitor                                     |
|                                                       |
|                                        2015 Simpler   |
+-------------------------------------------------------+
"""

if __name__ == '__main__':
    print MonitorTitle

    if len(sys.argv) < 2:
        print "usage : system_monitor.py [url]"
        exit()

    timerThreading = threading.Thread(target=keepAliveVM, args=(sys.argv[1],))
    timerThreading.daemon = True
    timerThreading.start()

    app.run(debug=False, host="0.0.0.0", port=5009)
