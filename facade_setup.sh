#!/bin/sh
cd /facade/utilities/
echo "DB schema setup"
python automatic_setup.py c yes facade facade localhost facade no yes admin exampleemail@domain.com admin admin
echo "Import CNCF/gitdm settings"
python import_gitdm_configs.py -a ../cncf-config/aliases -e ../cncf-config/email-map -e ../cncf-config/domain-map -e ../cncf-config/group-map
mkdir /opt/facade && mkdir /opt/facade/git-trees/ && chown facade /opt/facade/git-trees/
echo "Setup complete"
