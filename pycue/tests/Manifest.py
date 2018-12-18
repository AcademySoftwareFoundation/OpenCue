#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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


import os
import sys
import unittest

# All tests modules support an optional <username> and <version> argument
# This load a specific /net/soft_scratch/users/<username>/spimport/v<version>
# Otherwise it imports Cue3 from /shots/spi/home/python2.4/common/

if len(sys.argv) > 1:
    if sys.argv[1].find("-h") != -1:
        print "\nUsage: %s <username> <version>" % sys.argv[0]
        print " Loads from: /net/soft_scratch/users/<username>/spimport/v<version>"
        print " Version defaults to 0\n"
        sys.exit()

options = [item for item in sys.argv[1:] if not item.startswith("-")]
if options:
    version = 0
    if len(options) > 1:
        version = options[1]
        sys.argv.remove(version)
    name = options[0]
    sys.argv.remove(name)

    os.environ["SPIMPORT_PACKAGES"] = "/net/soft_scratch/users/%s/spimport" % name
    import SpImport
    Cue3 = SpImport.Package("Cue3", int(version))
    Cue3.Cuebot.setHosts(["cue3test01"])
    print "Setting test proxy: %s" % Cue3.Cuebot.Proxy
else:
    import Cue3
