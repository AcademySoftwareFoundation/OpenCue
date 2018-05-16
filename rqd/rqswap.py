#!/usr/bin/python


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




"""
Utility classes and functions to get virtual memory page out number.
"""
from __future__ import with_statement
import logging as log
import re
import threading
import time


class VmStatException(Exception):
    """
    Something for clients to catch if something
    goes wrong in here.
    """

    pass


class SampleData(object):
    """
    Sample data container.
    """

    def __init__(self, epoch_time, pgout_num):
        """
        Constructor.
        """

        self.__epoch_time_in_second = epoch_time
        self.__pgpgout = pgout_num

    def __repr__(self):
        """
        Return string representation.
        """

        return "(" + str(self.__epoch_time_in_second) + ", " + \
            str(self.__pgpgout) + ")"

    def get_epoch_time(self):
        """
        Return the sample's epoch time.
        """
        return self.__epoch_time_in_second

    def get_pgout_number(self):
        """
        Return the sample's page out number.
        """
        return self.__pgpgout


class RepeatedTimer(threading.Thread):
    """
    A repeated timer.
    """

    def __init__(self, interval, function, *args, **kwargs):
        """
        Constructor.
        """

        threading.Thread.__init__(self)
        self.__interval = interval
        self.__callable = function
        self.__args = args
        self.__kwargs = kwargs
        self.__event = threading.Event()
        self.__event.set()

    def run(self):
        """
        Override run() method in threading.Thread class.
        """

        while self.__event.is_set():
            try:
                timer = threading.Timer(self.__interval,
                                        self.__callable,
                                        self.__args,
                                        self.__kwargs)
                timer.start()
                timer.join()
            except Exception:
                # Catch all exceptions here.
                pass

    def cancel(self):
        """
        Cancel the repeated timer.
        """
        self.__event.clear()


PGPGOUT_RE = re.compile(r"^pgpgout (\d+)")
class VmStat(object):
    """
    A simple class to return pgpgout number from /proc/vmstat.
    """

    def __init__(self):
        """
        Constructor.
        """

        self.__interval = 15
        self.__sample_size = 10
        self.__lock = threading.Lock()
        self.__sample_data = []
        self.__repeated_timer = RepeatedTimer(
            self.__interval,
            self.__get_pgout_num)
        self.__repeated_timer.setDaemon(True)
        self.__repeated_timer.start()

    def __get_sample_data_copy(self):
        """
        Return a copy of self.__sample_data.
        """

        with self.__lock:
            current_sample_data = list(self.__sample_data)
        return current_sample_data

    def __get_pgout_num(self):
        """
        Read /proc/vmstat file and get pgpgout number.
        """

        found_pgpgout = False
        pgpgout_num = 0
        try:
            with open("/proc/vmstat") as vm_stat_file:
                for line in vm_stat_file.readlines():
                    match_obj = PGPGOUT_RE.match(line)
                    if match_obj:
                        found_pgpgout = True
                        pgpgout_num = int(match_obj.group(1))
                        break
        except IOError:
            log.warn("Failed to open /proc/vmstat file.")

        if found_pgpgout:
            with self.__lock:
                self.__sample_data.append(SampleData(time.time(),
                                                     pgpgout_num))
                del self.__sample_data[:-self.__sample_size]
        else:
            log.warn("Could not get pgpgout number.")

    def get_pgout_rate(self):
        """
        Return page out rate.
        """

        current_sample_data = self.__get_sample_data_copy()
        current_time = time.time()
        sample_data_len = len(current_sample_data)
        if sample_data_len < 5:
            return 0

        weight = 1
        total_weight = weight
        weighted_sum = 0
        for i in range(1, sample_data_len):
            if (current_sample_data[i].get_epoch_time() <
                    current_time - self.__sample_size * self.__interval - 2):
                continue
            weighted_sum += \
                   weight * (current_sample_data[i].get_pgout_number() - \
                       current_sample_data[i - 1].get_pgout_number()) / \
                   (current_sample_data[i].get_epoch_time() - \
                        current_sample_data[i - 1].get_epoch_time())
            total_weight += weight
            weight += 1

        return weighted_sum / (total_weight * self.__interval)

    def get_recent_pgout_rate(self):
        """
        Return the most recent page out rate.
        """

        current_sample_data = self.__get_sample_data_copy()
        sample_data_len = len(current_sample_data)
        if sample_data_len < 2:
            return 0

        index = sample_data_len - 1
        return (current_sample_data[index].get_pgout_number() - \
                   current_sample_data[index - 1].get_pgout_number()) / \
               (current_sample_data[index].get_epoch_time() - \
                   current_sample_data[index - 1].get_epoch_time()) / \
               self.__interval

    def stop_sample(self):
        """
        Stop the repeated timer.
        """

        self.__repeated_timer.cancel()

if __name__ == "__main__":
    vmstat = VmStat()
    while 1:
        time.sleep(2)
        print vmstat.get_pgout_rate(), vmstat.get_recent_pgout_rate()

