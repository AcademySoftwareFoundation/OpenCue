#!/bin/sh

docker run -td -p 8080:8080 -v /var/run/docker.sock:/var/run/docker.sock opencue/jenkins

