#!/bin/bash

set -e

# To run this script, you must first set the version number.
# For example, to set the version to 0.2.31, run:
# export VERSION=0.2.31
# For additional requirements, see https://www.opencue.io/docs/quick-starts/

if [[ -z "${VERSION}" ]]; then
    echo "You must set the release version number. For example:"
    echo "export VERSION=0.2.31"
    echo "For a list of OpenCue version numbers, visit the following URL:"
    echo "https://github.com/AcademySoftwareFoundation/OpenCue/releases/"
    exit 1
fi

CLIENT_PACKAGES=( pycue pyoutline cueadmin cuegui cuesubmit  )

BASE_URL=https://github.com/AcademySoftwareFoundation/OpenCue/releases/download/

mkdir opencue-downloads

cd opencue-downloads

for PACKAGE in "${CLIENT_PACKAGES[@]}"; do
    # older versions of OpenCue provided a slightly different download URL
    # format.
    wget ${BASE_URL}${VERSION}/${PACKAGE}-${VERSION}-all.tar.gz \
        || wget ${BASE_URL}v${VERSION}/${PACKAGE}-${VERSION}-all.tar.gz
    tar xvzf ${PACKAGE}-${VERSION}-all.tar.gz
    pip install -r ${PACKAGE}-${VERSION}-all/requirements.txt
    pip install -r ${PACKAGE}-${VERSION}-all/requirements_gui.txt
    cd ${PACKAGE}-${VERSION}-all
    python setup.py install
    cd ..
done

cd ..

rm -rf opencue-downloads
