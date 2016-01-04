#!/bin/sh
#echo $(date) >> /home/humax/admin/cronjob/log/timestamp.txt
git reset --hard
git pull
#svn revert -R /home/humax/admin
#svn update /home/humax/admin
/home/humax/admin/cronjob/system_management.sh
