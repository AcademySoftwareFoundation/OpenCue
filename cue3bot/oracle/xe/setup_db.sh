#!/usr/bin/env bash

echo "Setting up Database settings..."
echo "CREATING USER: $1 - $2"
results=`su -p oracle -c "sqlplus system/$1 as sysdba" << EOF
   alter system set processes=300 scope=spfile;
   alter system reset sessions scope=spfile sid='*';
   alter system set local_listener='(DESCRIPTION=(ADDRESS=(PROTOCOL=IPC)(KEY=EXTPROC_FOR_XE)))' SCOPE=BOTH;
   CREATE USER $1 IDENTIFIED BY $2;
   GRANT CONNECT, RESOURCE, DBA TO $1;
   shutdown immediate;
   startup;
   exit;
EOF`
echo $results
echo "Finished configuring database."
