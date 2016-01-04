import sys

if __name__ == '__main__':
    adding_user = sys.argv[1]
    adding_id   = sys.argv[2]

    file = open("/etc/vncserver/vncservers.conf", "r")
    vncconf = file.read()
    file.close()

    userlist = []
    vncconf = vncconf.split("\n")
    # find users
    for item in vncconf:
        if item.startswith("VNCSERVERS"):
            vncinfo = item.split("=")
            user = vncinfo[1].strip('"')
            eachuser = user.split(' ')
            for user in eachuser:
                userinfo = user.split(":")
                userlist.append({"id":userinfo[0], "name":userinfo[1]})

    usernames = ""
    for user in userlist:
        usernames = usernames + "%s:%s " % (user["id"], user["name"])

    usernames = usernames + "%s:%s" % (adding_id, adding_user)
    print "=============================="

    file = open("/etc/vncserver/vncservers.conf", "w")
    file.write('VNCSERVERS="%s"\n' % usernames)
    for user in userlist:
        file.write('VNCSERVERARGS[%s]="-geometry 1600x900"\n' % user['id'])
    file.write('VNCSERVERARGS[%s]="-geometry 1600x900"\n' % adding_id)
    file.close()

