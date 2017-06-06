#!/bin/sh
rm -i ~/.ssh/known_hosts
ssh -o "Port=2222" facade@localhost
