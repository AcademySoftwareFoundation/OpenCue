#!/bin/sh

echo "WARNING: this script is for setting up a new database only"  
echo "WARNIMG: do not run this on production hardware"
echo "ctr-c to cancel, enter to continue"
read

echo "dropping old spcue database if it exists"
dropdb spcue2 -U postgres
createdb spcue2 -U cue
createlang plpgsql spcue2 -U postgres

psql -U cue spcue2 < spcuebot.sql
