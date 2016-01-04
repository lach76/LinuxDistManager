#!/usr/bin/env bash

sudo apt-get -y install tftp tftpd

sudo touch /etc/xinetd.d/tftp
echo "service tftp" | sudo tee --append /etc/xinetd.d/tftp
echo "{" | sudo tee --append /etc/xinetd.d/tftp
echo "    socket_type = dgram" | sudo tee --append /etc/xinetd.d/tftp
echo "    protocol    = udp" | sudo tee --append /etc/xinetd.d/tftp
echo "    wait        = yes" | sudo tee --append /etc/xinetd.d/tftp
echo "    user        = root" | sudo tee --append /etc/xinetd.d/tftp
echo "    server      = /usr/sbin/in.tftpd" | sudo tee --append /etc/xinetd.d/tftp
echo "    server_args = -s /tftpboot" | sudo tee --append /etc/xinetd.d/tftp
echo "    disable     = no" | sudo tee --append /etc/xinetd.d/tftp
echo "}" | sudo tee --append /etc/xinetd.d/tftp

sudo mkdir /home/tftpboot
sudo chmod 777 /home/tftpboot
sudo ln -s /home/tftpboot /tftpboot

sudo /etc/init.d/xinetd restart

