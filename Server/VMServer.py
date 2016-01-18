import json
import os
import threading
import Queue
import flask
import time
import datetime
import subprocess

app = flask.Flask(__name__)

USAGE_UPDATE_TIMER = 5  # minute
vmmInfos = {}
lastUsageInfos = {}


def addVMtoManagedList(json):
    global vmmInfos
    global lastUsageInfos

    dist_name = ' '.join(json['machine'][:-1])
    dist_arch = json['machine'][-1]
    host_name = json['hostname']
    if json.has_key('template'):
        template_name = json['template']
    else:
        template_name = "Undefined"
    ipaddr = json['network'][0]
    hwaddr = json['network'][1]

    bForcedUpdate = False
    if not vmmInfos.has_key(hwaddr):
        vmmInfos[hwaddr] = {}
        bForcedUpdate = True

    vminfo = {'VMInfo': [host_name, ipaddr, hwaddr, dist_name, dist_arch, template_name], 'lastupdate': time.time()}
    vmmInfos[hwaddr] = vminfo

    if bForcedUpdate:
        usageInfos = retrieveAllUsageInfo(hwaddr)
        updateUsageInfos(datetime.datetime.now(), usageInfos)
        lastUsageInfos[hwaddr] = usageInfos[hwaddr]


def processCommand(cmdDict):
    global vmmInfos

    cmdList = cmdDict['command']
    cmdJson = {"command": cmdList}

    output = []
    for hwaddr, value in vmmInfos.items():
        if len(cmdDict['target']) > 0:
            if hwaddr not in cmdDict['target']:
                continue

        ipaddr = vmmInfos[hwaddr]['VMInfo'][1]
        url = "http://%s:5009/api/command" % ipaddr
        try:
            outputdata = subprocess.check_output(
                ['curl', '-s', '-H', 'Content-type: application/json', '-X', 'GET', url, '-d', "%s" % json.dumps(cmdJson)])
            outputlist = outputdata.splitlines()
            output.append(outputlist)
        except:
            output.append(["Fail"])

    return {"result":output}


@app.route('/api/command', methods=['GET'])
def command_runner():
    if flask.request.headers['Content-Type'] == 'application/json':
        # {"command":[], "target":["hwaddr", ...]}
        # if target is Empty, command will be broadcasted
        return flask.jsonify(processCommand(flask.request.json))

    return flask.jsonify({})

@app.route('/api/users')
def command_userlist():
    global vmmInfos
    global lastUsageInfos

    result = {}
    for hwaddr, usage in lastUsageInfos.items():
        if vmmInfos.has_key(hwaddr):
            ipaddr = vmmInfos[hwaddr]['VMInfo'][1]
            hostname = vmmInfos[hwaddr]['VMInfo'][0]
            userlist = usage['users'].keys()
            result[hwaddr] = {"ipaddr":ipaddr, "hostname":hostname, "userlist":userlist}

    return flask.jsonify(result)

@app.route('/messages', methods=['POST'])
@app.route('/register', methods=['POST'])
def api_message():
    if flask.request.headers['Content-Type'] == 'application/json':
        # {"machine": ["Ubuntu", "14.04", "trusty", "x86_64"], "hostname": "stbtester", "network": ["192.168.0.23", "b8:ac:6f:82:e1:d9"], "template": "Ubuntu12045x64_XXXX\n"}
        addVMtoManagedList(flask.request.json)
        return ""

    else:
        return "415 Unsupported Media Type ;)"


"""
    usageInfos =
        {u'b8:ac:6f:82:e1:d9': {
            u'mem': [3634618368, 2618982400, 6253600768],
            u'disk': [132105613312, 328693178368, 485483528192],
            u'cpu': [0.3, 1.0, 98.8, 0.0, 0.0, 0.0],
            u'users': {u'kimjh': [[u'localhost', u':0'], [u'localhost', u'pts/0'], [u'localhost', u'pts/12'], [u'localhost', u'pts/15']], u'nobody': [], u'test_account': []}}}
"""
real_path = None


def updateUsageInfos(now, usageInfos):
    global real_path
    global vmmInfos

    subpath = "%04d%02d%02d" % (now.year, now.month, now.day)
    subpath = os.path.join(real_path, subpath)
    if not os.path.isdir(subpath):
        os.makedirs(subpath)

    for hwaddr, value in usageInfos.items():
        hostname = vmmInfos[hwaddr]['VMInfo'][0]
        filename = os.path.join(subpath, "%s-%s.csv" % (hostname, hwaddr.replace(':', '_')))

        writeData = map(str, value['mem']) + map(str, value['disk']) + map(str, value['cpu'])
        writeData.append(str(len(value['users'].keys())))
        sessions = 0
        connectedUser = 0
        for user, value1 in value['users'].items():
            sessions += len(value1)
            if len(value1) > 0:
                connectedUser += 1

        writeData.append(str(sessions))
        writeData.append(str(connectedUser))

        idleUserData = "0;"
        if value.has_key('idle'):
            idlelist = value['idle']
            idleUserList = []
            idleCount = len(idlelist)
            for idle in idlelist:
                idleUserInfo = "%s:%s:%s" % (idle['user'], idle['idle'], idle['command'])
                idleUserList.append(idleUserInfo)
            idleUserData = "%d;" % (idleCount) + ";".join(idleUserList)

        writeData.append(idleUserData)

        if not os.path.isfile(filename):
            with open(filename, "w") as file:
                file.write(
                    "Time|MemUsed|MemFree|MemTotal|DiskUsed|DiskFree|DiskTotal|CPUUsed(SYS)|CPUUsed(User)|CPUUsed(IDLE)|CPUUsed(IOWAIT)|CPUUsed(IRQ)|CPUUsed(SIRQ)|REGUser|ConnectedSessions|ConnectedUsers|IdleSessions\n")

        with open(filename, "a") as file:
            file.write('%02d%02d|' % (now.hour, now.minute))
            file.write('|'.join(writeData))
            file.write("\n")

    pass


def curlTrigger(usageUrl, hwaddr, resultDict):
    try:
        result = subprocess.check_output(['curl', '-s', '-H', 'Content-type: application/json', '-X', 'GET', usageUrl])
    except:
        result = ""

    resultDict[hwaddr] = json.loads(result)


def retrieveAllUsageInfo(target_addr=None):
    global vmmInfos

    resultDict = {}
    callThreadList = []
    for hwaddr, value in vmmInfos.items():
        if (target_addr is None) or (target_addr == hwaddr):
            usageUrl = 'http://%s:5009/api/usage' % str(value['VMInfo'][1])
            callThread = threading.Thread(target=curlTrigger, args=(usageUrl, hwaddr, resultDict,))
            callThreadList.append(callThread)
            callThread.start()

    for thread in callThreadList:
        thread.join()

    return resultDict


def mainThread():
    global vmmInfos
    global lastUsageInfos

    last_minute = -1
    while True:
        now = datetime.datetime.now()
        minute = now.minute

        # per 5 minute update, retrive VM usage info
        if minute % USAGE_UPDATE_TIMER == 0 and minute != last_minute:
            last_minute = minute
            usageInfos = retrieveAllUsageInfo()
            updateUsageInfos(now, usageInfos)
            lastUsageInfos = usageInfos

        if minute % 10 == 0:  # remove unused VMMInfo per 10Minutes
            curr_time = time.time()
            for hwaddr, value in vmmInfos.items():
                timegap = curr_time - value['lastupdate']
                if timegap > 600:
                    del vmmInfos[hwaddr]

        time.sleep(5)
    pass


@app.route('/usageinfo/<hwaddr>')
@app.route('/usageinfo/<hwaddr>/<int:step>')
def usageinfo(hwaddr, step=60):
    global vmmInfos
    global lastUsageInfos

    if not vmmInfos.has_key(hwaddr):
        return ""

    hostname = vmmInfos[hwaddr]['VMInfo'][0]
    filename = "%s-%s.csv" % (hostname, hwaddr.replace(':', '_'))

    now = datetime.datetime.now()
    startDate = now - datetime.timedelta(days=6)
    timedelta = datetime.timedelta(days=1)

    # chart info
    chart_timeline = []
    chart_registered = []
    chart_connected = []
    chart_sessions = []
    chart_idlesessions = []
    chart_runsessions = []

    usagesList = []
    for day in range(7):
        subpath = "%04d%02d%02d" % (startDate.year, startDate.month, startDate.day)
        subpath = os.path.join(real_path, subpath)
        if os.path.isdir(subpath):
            csvname = os.path.join(subpath, filename)
            with open(csvname, "r") as file:
                lines = file.readlines()
                del lines[0]
                lines = map(lambda s: s.strip(), lines)
                for line in lines:
                    lineitem = line.split('|')
                    if len(lineitem) < 16:
                        lineitem.append(lineitem[13])
                    if len(lineitem) < 17:
                        lineitem.append("0;")
                    time = "%02d/%02d %s" % (startDate.month, startDate.day, lineitem[0])
                    memory = "%d/%d (MB)" % (int(lineitem[1]) >> 20, int(lineitem[3]) >> 20)
                    disk = "%d/%d (GB)" % (int(lineitem[4]) >> 30, int(lineitem[6]) >> 30)
                    cpu = "%3.1f %%" % (100.0 - float(lineitem[9]))
                    users = "%s / %s" % (lineitem[15], lineitem[13])
                    session = lineitem[14]
                    usage = {"time": time, "memory": memory, 'storage': disk, 'cpu': cpu, 'users': users,
                             'sessions': session, 'idlesessions': lineitem[16]}
                    usagesList.append(usage)

                    chart_timeline.append(
                        "%02d/%02d %s:%s" % (startDate.month, startDate.day, lineitem[0][:2], lineitem[0][2:]))
                    chart_registered.append(int(lineitem[13]))
                    chart_connected.append(int(lineitem[15]))
                    chart_sessions.append(int(lineitem[14]))

                    idlelist = lineitem[16].split(';')
                    idlecount = int(idlelist[0])
                    chart_idlesessions.append(idlecount)
                    chart_runsessions.append(int(lineitem[14]) - idlecount)

        startDate += timedelta

    xstep = max((step / 5), 1)  # step is minute

    usagesList.reverse()
    usagesList = usagesList[::xstep]

    users = {}
    if lastUsageInfos.has_key(hwaddr):
        userinfo = lastUsageInfos[hwaddr]['users']
        totalusers = ""
        connectedUser = ""
        for user, value in userinfo.items():
            totalusers += user + ' '
            if len(value) > 0:
                connectedUser += "%s(%d) " % (user, len(value))

        users = {'registered': totalusers, 'connected': connectedUser}

    ## Chart
    chartinfo = {"renderTo": 'chart_ID', "type": 'line', "height": 300, }
    title = {"text": ''}
    yAxis = {"title": {"text": "User connected"}}
    xAxis = {"categories": chart_timeline[::xstep]}
    series = [{"name": "Registered User", "data": chart_registered[::xstep]},
              {"name": "Connected User", "data": chart_connected[::xstep]},
              {"name": "Connected Sessions", "data": chart_sessions[::xstep]},
              {"name": "Idle Sessions", "data": chart_idlesessions[::xstep]},
              {"name": "Run Sessions", "data": chart_runsessions[::xstep]}]
    chart = {"chartID": "chart_ID", "chart": chartinfo, "series": series, "title": title, "xAxis": xAxis,
             "yAxis": yAxis}

    return flask.render_template('VMInfoSeries.html', title='VM Usage Information', usageslist=usagesList, user=users,
                                 chart=chart)


@app.route('/')
@app.route('/index')
def index():
    global vmmInfos
    global lastUsageInfos

    postinfo = []
    for key, value in vmmInfos.items():
        VMInfo = value['VMInfo']
        vminfo = {}
        vminfo['hostname'] = VMInfo[0]
        vminfo['ipaddr'] = VMInfo[1]
        vminfo['hwaddr'] = VMInfo[2]
        vminfo['url'] = '/usageinfo/' + vminfo['hwaddr']
        vminfo['distribution'] = VMInfo[3] + '(%s)' % VMInfo[4]
        vminfo['template'] = VMInfo[5]

        if lastUsageInfos.has_key(key):
            usageInfo = lastUsageInfos[key]
            meminfo = usageInfo['mem']
            diskinfo = usageInfo['disk']
            cpuinfo = usageInfo['cpu']
            userinfo = usageInfo['users']

            vminfo['memory'] = "%dM/%dM (%d%%)" % (meminfo[0] >> 20, meminfo[2] >> 20, meminfo[0] * 100 / meminfo[2])
            vminfo['disk'] = "%dG/%dG (%d%%)" % (diskinfo[0] >> 30, diskinfo[2] >> 30, diskinfo[0] * 100 / diskinfo[2])
            vminfo['cpu'] = "%d%%" % (100 - cpuinfo[2])

            totalUser = 0
            connectedUser = 0
            sessions = 0
            for user, value in userinfo.items():
                totalUser += 1
                if len(value) > 0:
                    connectedUser += 1
                sessions += len(value)

            if usageInfo.has_key('idle'):
                idlelist = usageInfo['idle']
                idlecount = len(idlelist)
            else:
                idlecount = 0

            vminfo['users'] = "%d/%d" % (connectedUser, totalUser)
            vminfo['sessions'] = "%d(%d)" % (sessions - idlecount, sessions)
            if (sessions - idlecount) == 0:
                vminfo['used'] = False
            else:
                vminfo['used'] = True

        postinfo.append(vminfo)

    return flask.render_template('index2.html',
                                 title='Build Server Management',
                                 posts=postinfo)


MonitorTitle = """
+-------------------------------------------------------+
|  Linux VM Monitoring Server                           |
|                                                       |
|                                        2015 Simpler   |
+-------------------------------------------------------+
"""

if __name__ == "__main__":
    if real_path is None:
        real_path = os.path.dirname(os.path.realpath(__file__))

    mainThread = threading.Thread(target=mainThread)
    mainThread.daemon = True
    mainThread.start()

    app.run(debug=True, host="0.0.0.0", port=5010)
