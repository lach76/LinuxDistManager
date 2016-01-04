#!/usr/bin/env bash

#sudo apt-get install samba smbfs
sudo apt-get -y install samba cifs-utils
echo "[humax]" | sudo tee --append /etc/samba/smb.conf
echo "comment = Humax SMB Directory" | sudo tee --append /etc/samba/smb.conf
echo "path = /home/$(whoami)" | sudo tee --append /etc/samba/smb.conf
echo "valid users = $(whoami)" | sudo tee --append /etc/samba/smb.conf
echo "public = yes" | sudo tee --append /etc/samba/smb.conf
echo "writable = yes" | sudo tee --append /etc/samba/smb.conf

sudo smbpasswd -a $(whoami)

sudo service smbd restart
