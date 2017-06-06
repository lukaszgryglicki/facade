#!/bin/sh
docker run -p 8888:80 -p 2222:22 lukaszgryglicki-facade 1>./server1.log 2>./server2.log &
