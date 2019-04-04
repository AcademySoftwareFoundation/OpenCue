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


"""A simple python thread pool."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
from builtins import range
from builtins import object
import queue
import threading
import logging


__all__ = ["TaskExecutor"]

logger = logging.getLogger("outline.executor")


class TaskExecutor(object):
    def __init__(self, threads):
        self.__queue = queue.Queue()

        for i in range(0, threads):
            logger.debug("executor creating thread #%d" % i)
            t = threading.Thread(target=self.worker)
            t.setDaemon(True)
            t.start()

    def execute(self, callable_, *args):
        """
        Queue up a function for execution by the thread pool.
        """
        self.__queue.put((callable_, args))

    def wait(self):
        """
        Wait until all work in the pool is complete and then
        return. Optionally stop the thread pool.
        """
        self.__queue.join()

    def worker(self):
        """
        Code that gets executed by the worker thread
        run() function.
        """
        while True:
            item = self.__queue.get()
            try:
                if item[1]:
                    item[0](*item[1])
                else:
                    item[0]()
            except Exception as e:
                logger.warn("Worker thread exception: %s" % e)
            self.__queue.task_done()
