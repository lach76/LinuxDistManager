#!/bin/bash

if [ $# -ne 1 ]
  then
    echo "Argument is not valid. Please input userid and user passwd"
    echo "./add_user username"
	exit
fi

if [ "$(id -u)" != "0" ]; then
  echo "Sorry, you are not root."
  exit
fi

username=$1

echo "remove Samba Permission"
smbpasswd -x $username
echo "please remove user information in /etc/samba/smb.conf manually"
echo "please remove user information in /etc/samba/smb.conf manually"
echo "please remove user information in /etc/samba/smb.conf manually"

echo "remove /nfsroot/$username"
rm -rf /nfsroot/$username

echo "remove user account with home folder"
userdel -rf $username

systemctl restart smb.service

echo "Remove user info in /etc/samba/smb.conf manually"
echo "Remove user info in /etc/vncserver/vncserver.conf"
