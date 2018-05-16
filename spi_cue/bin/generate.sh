#!/bin/sh

rm -rf ../lib/libice_3.3/*
/usr/bin/slice2py --all --output-dir ../lib/libice_3.3 \
-I../slice/cue -I../slice/spi ../slice/cue/cue_client.ice ../slice/cue/cue_types.ice ../slice/spi/*.ice

