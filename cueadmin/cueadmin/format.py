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


import time


def formatTime(epoch, time_format="%m/%d %H:%M", default="--/-- --:--"):
    """Formats time using time formatting standards
    see: http://docs.python.org/library/time.html"""
    if not epoch:
        return default
    return time.strftime(time_format, time.localtime(epoch))


def findDuration(start, stop):
    if stop < 1:
        stop = int(time.time())
    return stop - start


def formatDuration(sec):
    def splitTime(seconds):
        minutes, seconds = divmod(seconds, 60)
        hour, minutes = divmod(minutes, 60)
        return hour, minutes, seconds
    return "%02d:%02d:%02d" % splitTime(sec)


def formatLongDuration(sec):
    def splitTime(seconds):
        minutes, seconds = divmod(seconds, 60)
        hour, minutes = divmod(minutes, 60)
        days, hour = divmod(hour, 24)
        return days, hour
    return "%02d:%02d" % splitTime(sec)


def formatMem(kmem, unit=None):
    k = 1024
    if unit == "K" or not unit and kmem < k:
        return "%dK" % kmem
    if unit == "M" or not unit and kmem < pow(k, 2):
        return "%dM" % (kmem / k)
    if unit == "G" or not unit and kmem < pow(k, 3):
        return "%.01fG" % (float(kmem) / pow(k, 2))


def cutoff(s, length):
    if len(s) < length-2:
        return s
    else:
        return "%s.." % s[0:length-2]
