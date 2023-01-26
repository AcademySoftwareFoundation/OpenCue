#!/bin/sh

set -e

short_sha=LOCALTEST

mkdir -p tmp

rpmbuild \
    --define "_gitdir ${PWD}/../../.." \
    --define "_topdir ${PWD}"  \
    --define "revision ${short_sha}" \
    -bb SPECS/spi-openrqd.spec
