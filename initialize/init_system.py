#!/usr/bin/python

import os
import subprocess
import platform
import json

_installed_packages = {}
_needed_packages = {}
_needed_packages_py = {}
_distribution_vm = {}

def load_package_list(filename):
    packagelist = None
    with open(filename) as package_file:
        packagelist = json.loads(package_file.read())

    return packagelist

def load_system_distribution():
    dist_id, dist_ver, dist_nick = platform.linux_distribution()
    dist_id = dist_id.lower()
    if os.path.isfile("/etc/hvmtemplates"):
        with open('/etc/hvmtemplates') as template_file:
            dist_template = template_file.read().lower()
    else:
        dist_template = 'ubuntu'

    return {'id':dist_id, 'ver':dist_ver, 'nick':dist_nick, 'template':dist_template}

def load_installed_packagelist(distribution):
    installed_packages = None

    if distribution == 'ubuntu':
        raw_packages = subprocess.check_output(["dpkg-query", "-W"]) #, "-f=${Package}\t${Version}\n"])
        if "python" not in raw_packages:
            print "error in package list"
            return None

        raw_packages = raw_packages.replace('\r', '')
        raw_packages_list = raw_packages.split('\n')

        installed_packages = {}
        for package in raw_packages_list:
            if len(package) > 0:
                items = package.split('\t')
                if not installed_packages.has_key(items[0]):
                    installed_packages[items[0]] = items[1]
    else:
        print "Not supported yet"
        return None

    return installed_packages

def check_package_install(installed_packages, need_package):
    need_install = False
    version_check = False
    
    if installed_packages.has_key(need_package['name']):
        installed = installed_packages[need_package['name']]
        if need_package.has_key('version'):
            if need_package['version'] not in installed:
                need_install = True
                version_check = True
    else:
        need_install = True
        if need_package.has_key('version'):
            version_check = True

    return need_install, version_check

def check_distribution(packageinfo, distribution):
    if not packageinfo.has_key('distribution'):
        return {}

    distlist = packageinfo['distribution']

    for dist in distlist:
        if dist['dist'] in distribution['id']:
            if dist.has_key('version'):
                if dist['version'] in distribution['ver']:
                    return dist
            else:
                return dist

    return None

def check_template(packageinfo, distribution):
    template = distribution['template']
    if packageinfo.has_key('templates'):
        templatelist = packageinfo['templates']
        for temp in templatelist:
            if temp in template:
                return True

        return False

    return True

installation_command = {
    'ubuntu':'sudo apt-get -y install %s'
}

remove_command = {
    'ubuntu':'sudo apt-get -y purge %s'
}

maintain_command = {
    'ubuntu':'sudo apt-get -y autoremove'
}

def install_packages(packagelist, installed_packages, distribution):
    if installed_packages is None:
        print "Not supported in Update Packages"
        return

    for key, value in packagelist.items():
        if key == '_package_name':
            continue

        print "Check package - %s" % key
        # check linux distribution
        distItem = check_distribution(value, distribution)
        if distItem is None:
            continue

        # check vm template
        if not check_template(value, distribution):
            continue

        # check package install
        need_install, version_check = check_package_install(installed_packages, value)
        if not need_install:
            print "  - Installed"
            continue

        print " **** Start Installation [%s] ****" % value['name']
        # remove package first
        os.system(remove_command[distribution['id']] %  value['name'])
        # auto remove unused package
        os.system(maintain_command[distribution['id']])
        # check extra function for install package
        if distItem.has_key('extra'):
            for command in distItem['extra']:
                os.system("sudo " + command)
        # install package
        os.system(installation_command[distribution['id']] % value['name'])

        print need_install, version_check
    pass

def load_installed_packagelist_py():
    installed_python_packages = {}

    raw_packages = subprocess.check_output(["sudo", "pip", "list"])
    raw_packages = raw_packages.replace('\r', '')
    raw_packages_list = raw_packages.split('\n')
    for package in raw_packages_list:
        if len(package) > 0:
            items = package.split(' ')
            installed_python_packages[items[0]] = items[1]

    return installed_python_packages

def install_packages_python(needed_package, installed_package):
    for key, value in needed_package.items():
        print " -- Python Package [%s]" % key
        if not installed_package.has_key(key):
            os.system("sudo pip install %s" % key)
        else:
            print "    * Installed"

if __name__ == '__main__':
    print "*********************************************"
    print "***            VM Initializer             ***"
    print "*********************************************"

    distribution_vm = load_system_distribution()
    needed_packages = load_package_list('./packages.json')
    needed_packages_py = load_package_list('./python_packages.json')

    installed_packages = load_installed_packagelist(distribution_vm['id'])
    install_packages(needed_packages, installed_packages, distribution_vm)

    installed_packages_py = load_installed_packagelist_py()
    install_packages_python(needed_packages_py, installed_packages_py)

    print "*********************************************"
    print "***               Finished                ***"
    print "*********************************************"
