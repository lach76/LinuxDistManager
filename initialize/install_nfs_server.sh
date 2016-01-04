#!/usr/bin/env bash

sudo apt-get -y install nfs-common nfs-kernel-server
echo "/nfsroot   *(rw,no_root_squash,async,no_subtree_check)" | sudo tee --append /etc/exports
sudo mkdir /home/nfsroot
sudo chmod 777 /home/nfsroot
sudo ln -s /home/nfsroot /nfsroot
sudo /etc/init.d/nfs-kernel-server restart
