import json
import os
import threading
import Queue
import flask
import time
import datetime
import subprocess

app = flask.Flask(__name__)

USAGE_UPDATE_TIMER = 1      #   minute
vmmInfos = {}
lastUsageInfos = {}

def addVMtoManagedList(json):
    global vmmInfos

    dist_name = ' '.join(json['machine'][:-1])
    dist_arch = json['machine'][-1]
    host_name = json['hostname']
    template_name = json['template']
    ipaddr = json['network'][0]
    hwaddr = json['network'][1]

    if not vmmInfos.has_key(hwaddr):
        vmmInfos[hwaddr] = {}

    vminfo = {'VMInfo' : [host_name, ipaddr, hwaddr, dist_name, dist_arch, template_name], 'lastupdate':time.time()}
    vmmInfos[hwaddr] = vminfo

@app.route('/messages', methods=['POST'])
@app.route('/register', methods = ['POST'])
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

    if real_path is None:
        real_path = os.path.dirname(os.path.realpath(__file__))

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
        for user, value in value['users'].items():
            sessions += len(value)
        writeData.append(str(sessions))

        if not os.path.isfile(filename):
            with open(filename, "w") as file:
                file.write("Time|MemUsed|MemFree|MemTotal|DiskUsed|DiskFree|DiskTotal|CPUUsed(SYS)|CPUUsed(User)|CPUUsed(IDLE)|CPUUsed(IOWAIT)|CPUUsed(IRQ)|CPUUsed(SIRQ)|REGUser|ConnectedSessions\n")

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

def retrieveAllUsageInfo():
    global vmmInfos

    resultDict = {}
    callThreadList = []
    for hwaddr, value in vmmInfos.items():
        usageUrl = 'http://%s:5009/api/usage' % str(value['VMInfo'][1])
        callThread = threading.Thread(target=curlTrigger, args=(usageUrl, hwaddr, resultDict, ))
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

        if minute % 10 == 0:        # remove unused VMMInfo per 10Minutes
            curr_time = time.time()
            for hwaddr, value in vmmInfos.items():
                timegap = curr_time - value['lastupdate']
                if timegap > 600:
                    del vmmInfos[hwaddr]

        time.sleep(5)
    pass

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

            vminfo['users'] = "%d/%d" % (connectedUser, totalUser)
            vminfo['sessions'] = "%d" % sessions

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
    mainThread = threading.Thread(target=mainThread)
    mainThread.daemon = True
    mainThread.start()

    app.run(debug=True, host="0.0.0.0", port=5010)
