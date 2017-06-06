#!/bin/sh
cd /facade
./startup.sh || exit 1
while true
do
    date
    sleep 60
done
