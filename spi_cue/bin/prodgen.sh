#!/bin/sh

export prodice="/shots/spi/home/cue3/lib/Cue3/v1"
export slice="/shots/spi/home/cue3/lib/slice"

rm -rf ${prodice}/libice/*

/usr/local/ice/3.3-gcc34/bin/slice2py --all --output-dir ${prodice}/libice -I${slice}/cue -I${slice}/spi \
${slice}/cue/cue_client.ice ${slice}/cue/cue_types.ice ${slice}/spi/*.ice
