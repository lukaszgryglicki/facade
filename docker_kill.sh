#!/bin/sh
docker kill `docker ps | grep lukaszgryglicki-facade | cut -f 1 -d " "`
