#!/bin/sh

docker run -it --rm --name "cue3-bot" -p 8080:8080 -p 9018-9019:9018-9019 cue3-bot
