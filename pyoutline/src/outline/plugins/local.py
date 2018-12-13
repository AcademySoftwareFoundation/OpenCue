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


"""Plugin for booking local cores after a job is launched."""
import os
import logging
import subprocess

from socket import gethostname

from outline import event

logger = logging.getLogger("outline.plugins.local")

USE_LOCAL_CORES = 1
USE_LOCAL_THREADS = 0

def init_cuerun_plugin(cuerun):
    cuerun.get_parser().add_plugin_option("-L", "--run-local",
                                          action="callback",
                                          type="int",
                                          nargs=1,
                                          help="Run local cores",
                                          callback=setup_event,
                                          callback_args=(cuerun,))

    cuerun.get_parser().add_plugin_option("-T", "--run-local-threads",
                                          action="callback",
                                          type="int",
                                          nargs=1,
                                          help="Set number of threads for local cores to run per frame.",
                                          callback=setup_local_threads,
                                          callback_args=(cuerun,))


def setup_event(option, opt, value, parser, *args, **kwargs):
    # Don't have a way to pass this to the event but
    # a global will do.
    global USE_LOCAL_CORES
    USE_LOCAL_CORES = value

    args[0].add_event_listener(event.BEFORE_LAUNCH, setup_local_cores)


def setup_local_threads(option, opt, value, parser, *args, **kwargs):
    global USE_LOCAL_THREADS
    USE_LOCAL_THREADS = value

def deed_local_machine():
    import Cue3

    user = os.environ.get("USER")
    show = Cue3.findShow(os.environ.get("SHOW", "pipe"))
    try:
        owner = Cue3.getOwner(user)
    except Cue3.CueException, e:
        owner = show.createOwner(user)

    owner.takeOwnership(gethostname())

def setup_local_cores(e):

    deed_local_machine()

    threads = USE_LOCAL_THREADS or USE_LOCAL_CORES
    outline = e.outline
    outline.set_arg("localbook", { "host": gethostname(),
                                   "cores": str(USE_LOCAL_CORES),
                                   "memory": get_half_host_memory(),
                                   "threads": str(threads),
                                   "gpu": str(0) })

def get_half_host_memory():
    pipe = subprocess.Popen("vmstat -s",
                            shell=True, bufsize=1000, stdout=subprocess.PIPE).stdout
    data = pipe.read().strip()
    data = int(data[0:data.find(" ")])
    data = data / 2
    return str(data)

