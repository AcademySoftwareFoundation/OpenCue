#!/usr/bin/env bash

echo "Applying Database schema..."

# Install pip
curl "https://bootstrap.pypa.io/get-pip.py" -o "/tmp/get-pip.py"
python /tmp/get-pip.py
rm /tmp/get-pip.py

# install cx_Oracle
pip install cx_Oracle

su oracle -c "LD_LIBRARY_PATH=/u01/app/oracle/product/11.2.0/xe/lib/ bash -c \"python /tmp/apply_schema.py -p $1 -u $2 -s $3\""
echo "Finished applying schema."