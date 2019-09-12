#!/bin/bash

Xvfb :1 -screen 0 1024x768x16 &> /tmp/xvfb.log & bash -c "export DISPLAY=:1.0; $@"

