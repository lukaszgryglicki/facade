#!/bin/sh
mysqldump -ufacade -pfacade facade > "facade_`date +%Y%m%d%H%M%S`.sql"
