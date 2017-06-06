#!/bin/sh
export DEBIAN_FRONTEND=noninteractive
echo "mysql-server mysql-server/root_password password root" | debconf-set-selections
echo "mysql-server mysql-server/root_password_again password root" | debconf-set-selections
echo "mysql-community-server mysql-server/root_password password root" | debconf-set-selections
echo "mysql-community-server mysql-server/root_password_again password root" | debconf-set-selections
echo "mysql-server-5.7 mysql-server/root_password password root" | debconf-set-selections
echo "mysql-server-5.7 mysql-server/root_password_again password root" | debconf-set-selections
echo "mysql-server-8.0 mysql-server/root_password password root" | debconf-set-selections
echo "mysql-server-8.0 mysql-server/root_password_again password root" | debconf-set-selections
