#!/bin/sh
cd /facade/utilities/
echo "Running Facade analysis"
git config merge.renameLimit 100000
git config diff.renameLimit 100000
python facade-worker.py
echo "Facade complete"
