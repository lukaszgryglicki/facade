#!/bin/sh
docker stop `docker ps | grep lukaszgryglicki-facade | cut -f 1 -d " "`
