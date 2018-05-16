#!/usr/bin/env python


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


import sys
import socket
import os

try:
    host = sys.argv[1]
    object = sys.argv[2]
    port = sys.argv[3]
except:
    print "usage: check_ice.py host object port"
    sys.exit(1)

import Ice

try:
    ic = Ice.initialize(["--Ice.ImplicitContext=Shared", "--Ice.MessageSizeMax=10240"])
    implicit_context = ic.getImplicitContext()
    implicit_context.put('argv', 'xyzzy')
    implicit_context.put('hostname', str(socket.gethostname()))
    implicit_context.put('pid', str(os.getpid()))
    implicit_context.put('username', 'nagios')
    proxy = ic.stringToProxy("%s:default -h %s -p %s" % (object, host, port))
    proxy.ice_ping()
except Exception, e:
    print e
    sys.exit(1)
finally:
    ic.destroy()


print "%s ice object is available" % object
