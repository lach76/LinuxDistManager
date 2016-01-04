#!/bin/sh

cd /home/humax/admin/initialize
python init_system.py

Cnt=`ps -ef|grep "system_monitor.py"|grep -v grep|wc -l`
PROCESS=`ps -ef|grep "system_monitor.py"|grep -v grep|awk '{print $2}'`
if [ $Cnt -ne 0 ]
then
   kill -9 $PROCESS
fi

python /home/humax/admin/cronjob/system_monitor.py http://10.0.218.196:5010/messages &
