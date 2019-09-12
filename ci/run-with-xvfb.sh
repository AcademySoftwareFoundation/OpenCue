#!/bin/bash

Xvfb :1 -screen 0 1024x768x16 & bash -c "export DISPLAY=:1.0; $@"

