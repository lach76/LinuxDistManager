#!/bin/bash

if [ $# -ne 1 ]
  then
    echo "Argument is not valid. Please input userid"
    echo "./add_user username"
	exit
fi

if [ "$(id -u)" != "0" ]; then
  echo "Sorry, you are not root."
  exit
fi

username=$1

echo "Create user with [$username|$userpasswd]"
adduser $username
#useradd $username -p $userpasswd -m -s /bin/bash
echo "Add user to Developer Group"
usermod -a -G developer $username

#echo "Make internal NFSRoot Folder and Symbolic Link"
#mkdir /home/$username/nfsroot
#chown -R $username:developer /home/$username/nfsroot
#ln -s /home/$username/nfsroot /nfsroot/$username
#chown -R $username:developer /nfsroot/$username

echo "Add user to SMB"
smbpasswd -a $username
echo -e "\n[$username]\npath = /home/$username\ncomment = $username's Folder\nwriteable = yes\nvalid users = $username\npublic = yes" >> /etc/samba/smb.conf

service smbd restart


#
# add VNC user
cnt=`dpkg -l | grep vnc4server | grep -v grep | wc -l`
if [ $cnt -ne 0 ]
then
  echo -e "VNC is installed --> add account for VNCServer"

  if [ ! -f ./incr.txt ]; then
    echo -e "10" >> ./incr.txt
  fi

  value=$(cat incr.txt)
  newvalue=$(( value + 1 ))
  echo -e $newvalue > ./incr.txt
  python ./add_vnc_user.py $username $newvalue
  #echo -e "VNCSERVERS=\"$newvalue:$username\"" >> /etc/vncserver/vncservers.conf
  #echo -e "VNCSERVERARGS[$newvalue]=\"-geometry 1600x900\"" >> /etc/vncserver/vncservers.conf
  echo -e "VNCServer needs your password (at least 6 characters) - wait for prompt"
  su $username -c vncserver
  cp -f ./xstartup /home/$username/.vnc/
  cp -f ./xfce4-keyboard-shortcuts.xml /home/$username/.config/xfce4/xfconf/xfce-perchannel-xml/
  echo -e "VNCServer is restarted"
  service vncserver restart
  echo -e "VNCServer is setting with $username, [$newvalue]"
else
  echo -e "VNC Server is not installed"
fi

