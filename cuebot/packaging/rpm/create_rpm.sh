#!/bin/bash
#
# Creates an RPM for the specified IMAGE_NAME.
# IMAGE_NAME corresponds to the OpenCue service and source sub-directory,
# e.g. cuebot, rqd
# This script expects the RPM spec file to be in the current directory
# and named in the format <IMAGE_NAME>.spec, e.g. cuebot.spec
#
# The output is an RPM located in
# rpmbuild/RPMS/noarch/opencue-${IMAGE_NAME}-${VERSION}-1.noarch.rpm
#
IMAGE_NAME=$1
VERSION=$2

echo "create_rpm.sh $@"

# Trim any "-xxxx" suffix as it's not a valid RPM version
RPM_VERSION="$(echo $VERSION | cut -f1 -d-)"

mkdir -p rpmbuild/{RPMS,SOURCES,SPECS,SRPMS}
mkdir -p rpmbuild/RPMS/noarch

cp ${IMAGE_NAME}.spec rpmbuild/SPECS

sed -i s/%version%/${VERSION}/g rpmbuild/SPECS/${IMAGE_NAME}.spec
sed -i s/%rpm_version%/${RPM_VERSION}/g rpmbuild/SPECS/${IMAGE_NAME}.spec

rpmbuild --target noarch -bb rpmbuild/SPECS/${IMAGE_NAME}.spec

if [ "$RPM_VERSION" != "$VERSION" ]; then
    # Rename the RPM using the input version so it can be references externally
    mv rpmbuild/RPMS/noarch/opencue-${IMAGE_NAME}-${RPM_VERSION}-1.noarch.rpm \
        rpmbuild/RPMS/noarch/opencue-${IMAGE_NAME}-${VERSION}-1.noarch.rpm
fi
