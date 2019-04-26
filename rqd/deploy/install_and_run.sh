#!/bin/sh

rqd_archive=$(ls rqd-*-all.tar.gz)
tar -xvzf "$rqd_archive"

rqd_dir=$(ls -d rqd*/)
cd "$rqd_dir"
pip install -r requirements.txt
python setup.py install

exec rqd

