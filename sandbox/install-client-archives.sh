#!/bin/bash

set -e

# To run this script, you must first set the version number.
# For more information, see README.md

if [[ -z "${VERSION}" ]]; then
    echo "You must set the release version number. For example:"
    echo "export VERSION=0.2.31" 1>&2
    exit 1
fi

CLIENT_PACKAGES=( cueadmin cuegui cuesubmit pycue pyoutline )

BASE_URL=https://github.com/AcademySoftwareFoundation/OpenCue/releases/download/v

mkdir opencue-downloads

cd opencue-downloads

for PACKAGE in "${CLIENT_PACKAGES[@]}"; do
    wget ${BASE_URL}${VERSION}/${PACKAGE}-${VERSION}-all.tar.gz
    tar xvzf ${PACKAGE}-${VERSION}-all.tar.gz
    pip install -r ${PACKAGE}-${VERSION}-all/requirements.txt
    cd ${PACKAGE}-${VERSION}-all
    python setup.py install
    cd ..
done

cd ..

rm -rf opencue-downloads
