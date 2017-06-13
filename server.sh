#!/bin/sh
cd /facade
./startup.sh || exit 1
while true
do
    sleep 300
done
