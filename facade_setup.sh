#!/bin/sh
cd /facade/utilities/
echo "DB schema setup"
# If DB is totally empty
python automatic_setup.py c yes facade facade no localhost facade no no yes admin exampleemail@domain.com admin admin || exit 1
# If DB contains some data
# python automatic_setup.py c yes facade facade no localhost facade no no yes clear clear admin exampleemail@domain.com admin admin
echo "Import CNCF/gitdm settings"
python import_gitdm_configs.py -a ../cncf-config/aliases -e ../cncf-config/email-map -e ../cncf-config/domain-map -e ../cncf-config/group-map || exit 2
# mkdir /opt/facade && mkdir /opt/facade/git-trees/ && chown facade /opt/facade/git-trees/
git config merge.renameLimit 100000
git config diff.renameLimit 100000
cd /facade/
echo "Restoring Facade projects/Repos setup"
# Restore only SQL structure
# xz -d dumps/facade_structure.sql.xz && mysql -ufacade -pfacade facade < dumps/facade_structure.sql
# Restore version configured for Kubernetes but without generated data
# xz -d dumps/facade_configured.sql.xz && mysql -ufacade -pfacade facade < dumps/facade_configured.sql
# Restore version configured for Kubernetes and completed analysis on 2017-06-07 11:30 UTC
# xz -d dumps/facade_populated.sql.xz && mysql -ufacade -pfacade facade < dumps/facade_populated.sql
echo "Setup complete"
