#!/bin/sh
rm -i ~/.ssh/known_hosts
sftp -o "Port=2222" facade@localhost
