#!/bin/sh

set -e

chmod 660 /var/run/docker.sock
chgrp docker /var/run/docker.sock

su -c "/sbin/tini -- /usr/local/bin/jenkins.sh" jenkins

