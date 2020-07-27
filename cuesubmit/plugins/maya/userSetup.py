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

import maya.mel
import maya.utils

import CueMayaSubmit

SHELF_NAME = 'OpenCue'

def create_opencue_shelf():
    maya.mel.eval('if (`shelfLayout -exists {shelf} `) deleteUI {shelf};'.format(shelf=SHELF_NAME))
    shelfTab = maya.mel.eval('global string $gShelfTopLevel;')
    maya.mel.eval('global string $scriptsShelf;')
    maya.mel.eval('$scriptsShelf = `shelfLayout -p $gShelfTopLevel {}`;'.format(SHELF_NAME))
    maya.mel.eval(
        'shelfButton -parent $scriptsShelf -annotation "Render on OpenCue" '
        '-label "Render on OpenCue" -image "opencue_logo_small.png" -sourceType "python" '
        '-command ("CueMayaSubmit.main()") -width 34 -height 34 -style "iconOnly";')

maya.utils.executeDeferred(create_opencue_shelf)

