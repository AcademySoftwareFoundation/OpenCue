#!/bin/sh

echo "WARNING: this script is for setting up a new database only"  
echo "WARNIMG: do not run this on production hardware"
echo "ctr-c to cancel, enter to continue"
read

echo "dropping old spcue database if it exists"
dropdb spcue -U postgres
createdb spcue -U cue
createlang plpgsql spcue -U postgres

psql -U cue spcue < spcuebot.sql
