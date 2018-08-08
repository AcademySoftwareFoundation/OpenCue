#!/bin/sh

if (( $# < 1 )); then
  echo "Please pass a password as the first argument!"
  echo "Usage:"
  echo "   ./populate_db_and_start_cuebot.sh db_password"
  exit 1
fi

export CUEBOT_DB_TNS=oraxetest
export CUEBOT_DB_SYS_PWD=$1
export CUEBOT_ENABLE_JMS=false

cd /src && bin/sbt test

cd /opt/cue3 && bin/cuebot

