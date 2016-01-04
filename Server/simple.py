import datetime
import flask
import time
#from flask import json
#from flask import Flask
app = flask.Flask(__name__)

system_information = {}
system_monitor = {}

MAX_MONITOR_NUM = 20000

def getCPUAverage(cpuInfos):
    cpu_no = len(cpuInfos)
    cpu_idle = 0.0
    for cpu in cpuInfos:
        cpu_idle = cpu_idle + cpu[2]      #[cpu.system, cpu.user, cpu.idle, cpu.iowait, cpu.irq, cpu.softirq]
    cpu_idle = round(cpu_idle / cpu_no, 1)
    cpu_run  = 100 - cpu_idle

    return cpu_no, cpu_run

def getDiskUsage(diskInfos):
    # [disk.used, disk.free, disk.total]
    return diskInfos[0] >> 30, diskInfos[2] >> 30, diskInfos[0] * 100 / diskInfos[2]

def getMemUsage(memInfos):
    # [vMem.used, vMem.free, vMem.total]
    return memInfos[0] >> 20, memInfos[2] >> 20, memInfos[0] * 100 / memInfos[2]

def parse_SystemInformation(dataJson):
    global system_information
    global system_monitor

    if not dataJson.has_key('VMInfo'):
        return
    if not dataJson['VMInfo'].has_key('hwaddr'):
        return

    """
    {"VMInfo" :{
            "hostname":"hostname", "hwaddr":"mac address", "ipaddr":"local ip addr",
            "machine":["Ubuntu", "14.04", "trusty", "x86_64"},
            "template":"templateName"
        }
    }
    """
    hwaddr = dataJson['VMInfo']['hwaddr']
    if not system_information.has_key(hwaddr):
        system_information[hwaddr] = {}

    system_information[hwaddr]['lastupdate'] = int(time.time())
    if dataJson.has_key('VMInfo'):
        system_information[hwaddr]['VMInfo'] = dataJson['VMInfo']

    """
        {'Packages':[["packagename", "version"], ["packagename", "version"]]}
    """
    if dataJson.has_key('Packages'):
        # check package difference
        if not system_information[hwaddr].has_key('Packages'):
            system_information[hwaddr]['Packages'] = []

        org_list = system_information[hwaddr]['Packages']

        del_package_list = [x for x in org_list if x not in dataJson['Packages']]
        add_package_list = [x for x in dataJson['Packages'] if x not in org_list]

        system_information[hwaddr]['Packages'] = dataJson['Packages']
        system_information[hwaddr]['addPackages'] = add_package_list
        system_information[hwaddr]['delPackages'] = del_package_list

    """
        {"Usage":{  "cpu" : [ [[cpu.system, cpu.user, cpu.idle, cpu.iowait, cpu.irq, cpu.softirq], [], ...],
                    "disk" : [disk.used, disk.free, disk.total],
                    "mem" : [vMem.used, vMem.free, vMem.total],
                    "net" : [recv, send],
                    "user" : { "userid" : [ ["sessioninfo_from", teminalid], [] ]
                               "userid2" : ... }
                }
        }
    """
    if dataJson.has_key('Usage'):
        import pprint
        pprint.pprint(dataJson)
        system_information[hwaddr]['Usage'] = dataJson['Usage']
        if not system_monitor.has_key(hwaddr):
            system_monitor[hwaddr] = []

        cpu_no, cpu_run = getCPUAverage(dataJson['Usage']['cpu'])
        mem_used, mem_total, mem_usages = getMemUsage(dataJson['Usage']['mem'])
        disk_used, disk_total, disk_usage = getDiskUsage(dataJson['Usage']['disk'])
        unixtime = int(time.time())
        session_num = 0
        for user, list in dataJson['Usage']['user'].items():
            session_num += len(list)
        monitor = {'time':unixtime, 'cpu': cpu_run, 'mem' : mem_usages, 'disk':disk_usage, 'session':session_num}
        system_monitor[hwaddr].append(monitor)
        if len(system_monitor[hwaddr]) > MAX_MONITOR_NUM:
            system_monitor[hwaddr] = system_monitor[hwaddr][int(MAX_MONITOR_NUM * 0.3):]

    """
        {"Process":{
                "pid" : {
                    "cpu":"cpu_usages",
                    "created":"process created time",
                    "mem" : [RSS, VMM],
                    "name": "process name",
                    "user" : "process user"
                }, {
                "pid" : ....
                }
            }
        }

    """
    if dataJson.has_key('Process'):
        system_information[hwaddr]['Process'] = dataJson['Process']

def getVMInfoSystemInformation(value, userName = None):
    postvminfo = {}
    if not value.has_key('VMInfo'):
        return None

    VMInfo = value['VMInfo']

    postvminfo['ipaddr'] = VMInfo['ipaddr']
    postvminfo['hostname'] = VMInfo['hostname']
    postvminfo['template'] = VMInfo['template']
    postvminfo['hwaddr'] = VMInfo['hwaddr']

    postvminfo['distribution'] = '%s(%s)' % (VMInfo['machine'][0] + VMInfo['machine'][1], VMInfo['machine'][3])

    if value.has_key('Packages'):
        postvminfo['pack_added'] = len(value['addPackages'])
        postvminfo['pack_removed'] = len(value['delPackages'])

    if value.has_key('Usage'):
        UsageInfo = value['Usage']
        cpu_no, cpu_run = getCPUAverage(UsageInfo['cpu'])
        postvminfo['cpu'] = "%s core(s) / %d %% used" % (cpu_no, cpu_run)

        disk_used, disk_total, disk_usage = getDiskUsage(UsageInfo['disk'])
        postvminfo['disk'] = '%d/%d (%d%%)' % (disk_used, disk_total, disk_usage)

        mem_used, mem_total, mem_usage = getMemUsage(UsageInfo['mem'])
        postvminfo['memory'] = '%d/%d (%d%%)' % (mem_used, mem_total, mem_usage)

        postvminfo['url'] = '/vminfo/' + postvminfo['hwaddr']
        postvminfo['sshurl'] = postvminfo['ipaddr']

        session_count = 0
        connected_user = 0
        register_user = 0
        userUsageInfo = UsageInfo['user']  # user = {'id':[], 'id':[]}

        bFoundUser = False
        for user, list in userUsageInfo.items():
            if userName is not None:
                if userName == user:
                    bFoundUser = True

            register_user = register_user + 1
            session_count = session_count + len(list)
            if len(list) > 0:
                connected_user = connected_user + 1

        postvminfo['users'] = '%d/%d connected' % (connected_user, register_user)
        postvminfo['sessions'] = '%d session(s)' % session_count

        if (not bFoundUser) and (userName is not None):
            return None

    return postvminfo

@app.route('/user/<userName>')
def userInfo(userName):
    global system_information

    postinfo = []
    for key, value in system_information.items():
        postvminfo = getVMInfoSystemInformation(value, userName)
        if postvminfo is not None:
            postinfo.append(postvminfo)

    return flask.render_template('userinfo_detail.html', user = userName, posts=postinfo)

@app.route('/user')
def userInfoList():
    global system_information

    UserInfos = {}
    for vm_key, vm_value in system_information.items():
        if not vm_value.has_key('Usage'):
            continue

        VMInfo = vm_value['VMInfo']
        UsageInfo = vm_value['Usage']
        UserInfo = UsageInfo['user']
        for user_key, user_value in UserInfo.items():
            if not UserInfos.has_key(user_key):
                UserInfos[user_key] = []
            UserInfos[user_key].append({'name':VMInfo['hostname'], 'ipaddr':VMInfo['ipaddr']})

    return flask.render_template('userinfo.html',
                           users=UserInfos)

@app.route('/vminfo/<vmname>')
def vmInfo(vmname):
    global system_information

    user_proc_info = {}
    packagelist = []

    if system_information.has_key(vmname):
        VMInformation = system_information[vmname]
        VMInfo = VMInformation['VMInfo']
        if VMInformation.has_key('Packages'):
            PackageInformation = VMInformation['Packages']
            for package in PackageInformation:
                if len(package) > 1:
                    packagelist.append({'name':package[0], 'version':package[1]})

        if VMInformation.has_key('Usage') and VMInformation.has_key('Process'):
            UsageInformation = VMInformation['Usage']
            ProcInformation = VMInformation['Process']
            UserInfos = UsageInformation['user']
            for proc_pid, proc_value in ProcInformation.items():
                if UserInfos.has_key(proc_value['user']):
                    # add Process to user list
                    if not user_proc_info.has_key(proc_value['user']):
                        user_proc_info[proc_value['user']] = []

                    proc_info = {}
                    proc_info['pid'] = proc_pid
                    proc_info['cpu'] = proc_value['cpu']
                    proc_info['memory'] = '%d / %d' % (proc_value['mem'][0] >> 20, proc_value['mem'][1] >> 20)
                    proc_info['name'] =  proc_value['name']
                    proc_info['created'] = datetime.datetime.fromtimestamp(proc_value['created']).strftime("%Y-%m-%d %H:%M:%S")

                    user_proc_info[proc_value['user']].append(proc_info)

    #   sort by CPU
    #for vmuser in user_proc_info:
    #    vmuser['process'].sort(lambda x, y : cmp(y['cpu'], x['cpu']))

    return flask.render_template('vminfo.html',
                           title='VM Server - [%s]' % VMInfo['hostname'],
                           users=user_proc_info, packagelist = packagelist)

@app.route('/')
@app.route('/index')
def index():
    global system_information

    # remove useless System Information < 6Hours
    curr_time = int(time.time())
    thres_time = curr_time - 21600      # current time - 6hours
    for key, value in system_information.items():
        update_time = value['lastupdate']
        if thres_time > update_time:
            del system_information[key]

    postinfo = []
    for key, value in system_information.items():
        postvminfo = getVMInfoSystemInformation(value)
        if postvminfo is not None:
            postinfo.append(postvminfo)

    return flask.render_template('index.html',
                           title='Build Server Management',
                           posts=postinfo)

@app.route('/messages', methods = ['POST'])
def api_message():

    if flask.request.headers['Content-Type'] == 'text/plain':
        return "Text Message: " + flask.request.data

    elif flask.request.headers['Content-Type'] == 'application/json':
        parse_SystemInformation(flask.request.json)
        return ""

    elif flask.request.headers['Content-Type'] == 'application/octet-stream':
        f = open('./binary', 'wb')
        f.write(flask.request.data)
        f.close()
        return "Binary message written!"

    else:
        return "415 Unsupported Media Type ;)"

@app.route('/charts')
def charts(chartID = 'chart_ID', chart_type = 'line', chart_height = 720):
    global system_monitor
    global system_information

    chart = {"renderTo": chartID, "type": chart_type, "height": chart_height,}

    title = {"text": 'VM Connected Sessions'}
    yAxis = {"title":{"text" : "Connected Sessions"}}

    series = []

    # make timeline -500Min - Current
    MINUTE = 60
    itemGap = 30
    itemNum = 50
    timeline = []
    curtime = int(time.time())
    for index in range(0, itemNum):
        timeline.append(curtime - (itemNum - index) * itemGap * MINUTE)

    for key, list in system_monitor.iteritems():
        valueList = [0] * itemNum
        latestList = list[-itemGap * itemNum:]
        maximum = latestList[0]['session']
        for index, timeinfo in enumerate(latestList):
            if (index % itemGap) == 0:
                pos = (timeinfo['time'] - timeline[0]) / (itemGap * MINUTE)
                valueList[pos] = maximum
                maximum = timeinfo['session']
            maximum = max(maximum, timeinfo['session'])

        name = system_information[key]['VMInfo']['hostname']

        item = {"name":str(name), "data":valueList}
        series.append(item)

    xCategory = []
    for item in timeline:
        xCategory.append(time.strftime("%H:%M", time.localtime(item)))
    xAxis = {"categories":xCategory}

    post = {"chartID":"chart_ID", "chart":chart, "series":series, "title":title, "xAxis":xAxis, "yAxis":yAxis}
    posts = [post]

    return flask.render_template('charts.html', posts=posts)#chartID=chartID, chart=chart, series=series, title=title, xAxis=xAxis, yAxis=yAxis)

#        monitor = {'time':unixtime, 'cpu': cpu_run, 'mem' : mem_usages, 'disk':disk_usage, 'session':session_num}
#        system_monitor[hwaddr].append(monitor)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5010)
