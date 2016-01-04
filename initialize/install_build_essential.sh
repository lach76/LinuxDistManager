#!/usr/bin/env bash

sudo apt-get -y install build-essential gcc-multilib
sudo apt-get -y install flex bison
sudo apt-get -y install tig
sudo apt-get -y install software-properties-common python-software-properties
sudo apt-get -y install python python-dev python-pip

# for 64Bit Machine
#sudo apt-get -y install lib32stdc++6 lib32z1 lib32z1-dev

# JAVA

# Oracle
# sudo add-apt-repository ppa:webupd8team/java    # add PPA repository
# sudo apt-get update                             # update package list
# sudo apt-get install oracle-java8-installer

# OpenJDK
sudo apt-get update
sudo apt-get -y install openjdk-7-jdk
sudo apt-get -y install openjdk-6-jdk
sudo update-alternatives --config java
sudo update-alternatives --config javac
