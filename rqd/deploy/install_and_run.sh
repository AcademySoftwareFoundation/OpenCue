#!/bin/sh

rqd_archive=$(ls rqd-*-all.tar.gz)
tar -xvzf "$rqd_archive"

cd rqd
pip install -r requirements.txt
python setup.py install

rqd

