#!/bin/sh

set -e

short_sha=${GITHUB_SHA:0:8}

# Update VERSION in rqconstants.py.
commit_time=$(git show -s --format=%ct ${GITHUB_SHA})

perl -MPOSIX -i -pe 'BEGIN { $version = sprintf("'"'"'%s-%s'"'"'", POSIX::strftime("%Y%m%d", localtime('${commit_time}')), "'${short_sha}'")}; s/^VERSION =.*/VERSION = $version/' ${CI_PROJECT_DIR}/rqd/rqd/rqconstants.py

mkdir -p tmp

rpmbuild \
    --define "_gitdir ${GITHUB_WORKSPACE}" \
    --define "_topdir ${PWD}"  \
    --define "revision ${short_sha}" \
    -bb SPECS/spi-openrqd.spec
