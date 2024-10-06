#!/usr/bin/env python
#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Blender job structure with a single layer and a single frame.

The frames just print out the current frame number."""


import getpass
import argparse
import outline
import outline.cuerun
import outline.modules.shell

parser = argparse.ArgumentParser(description="Simple Blender job")

parser.add_argument('-b', '--blendfile', type=str, help='Path to the .blend file source')

args = parser.parse_args()

ol = outline.Outline(
    'blender_job', shot='shot02', show='testing', user=getpass.getuser())
layer = outline.modules.shell.Shell(
    'blender_layer', command=['blender', '-b', args.blendfile,
                              '-F', 'PNG',
                              '-f', '1'
                              '-E', 'CYCLES', '--', '--cycles-device', 'CPU'], chunk=1, threads=1)
ol.add_layer(layer)
outline.cuerun.launch(ol, use_pycuerun=False)