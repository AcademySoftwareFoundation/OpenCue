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

CLIENT_PACKAGES=( pycue pyoutline cueadmin cueman cuegui cuesubmit  )

BASE_URL=https://github.com/AcademySoftwareFoundation/OpenCue/releases/download/

mkdir opencue-downloads

cd opencue-downloads

for PACKAGE in "${CLIENT_PACKAGES[@]}"; do
    # older versions of OpenCue provided a slightly different download URL
    # format.
    wget ${BASE_URL}${VERSION}/${PACKAGE}-${VERSION}-all.tar.gz \
        || wget ${BASE_URL}v${VERSION}/${PACKAGE}-${VERSION}-all.tar.gz
    tar xvzf ${PACKAGE}-${VERSION}-all.tar.gz
    REQUIREMENTS=${PACKAGE}-${VERSION}-all/requirements.txt
    REQUIREMENTS_GUI=${PACKAGE}-${VERSION}-all/requirements_gui.txt

    pip install -r ${REQUIREMENTS}
    # requirements vary across the Python packages
    if [ -f ${REQUIREMENTS_GUI} ]; then
        pip install -r ${REQUIREMENTS_GUI}
    fi
    cd ${PACKAGE}-${VERSION}-all

    # remove *.pyc files and __pycache__ folders contained on
    # <PACKAGE-VERSION>-all.tar.gz. As these files might be generated from
    # a different operating system and/or python version than current host has
    # `python setup.py install` may raise a `ValueError: bad marshal data` error.
    # Removing these files before invoking `setup.py` prevent this error.
    # NOTE: Temporary solution until pip distribution is ready.
    find . -path '*/__pycache__*' -delete
    find . -name '*.pyc'  -type f -delete

    python setup.py install
    cd ..
done

cd ..

rm -rf opencue-downloads
