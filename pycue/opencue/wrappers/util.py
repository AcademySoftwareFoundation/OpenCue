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
Project: opencue Library

Module: util.py - opencue Library utility

"""

import time


def format_time(epoch, format="%m/%d %H:%M", default="--/-- --:--"):
    """Formats time using time formatting standards
    see: http://docs.python.org/library/time.html"""
    if not epoch:
        return default
    return time.strftime(format, time.localtime(epoch))


def dateToMMDDHHMM(sec):
    """Returns date in the format %m/%d %H:%M
    @rtype:  str
    @return: Date in the format %m/%d %H:%M"""
    if sec == 0:
        return "--/-- --:--"
    return time.strftime("%m/%d %H:%M", time.localtime(sec))


def __splitTime(sec):
    """Returns time in the format H:MM:SS
    @rtype:  str
    @return: Time in the format H:MM:SS"""
    min, sec = divmod(sec, 60)
    hour, min = divmod(min, 60)
    return (hour, min, sec)


def secondsToHHMMSS(sec):
    """Returns time in the format HH:MM:SS
    @rtype:  str
    @return: Time in the format HH:MM:SS"""
    return "%02d:%02d:%02d" % __splitTime(sec)


def secondsToHMMSS(sec):
    """Returns time in the format H:MM:SS
    @rtype:  str
    @return: Time in the format H:MM:SS"""
    return "%d:%02d:%02d" % __splitTime(sec)


def secondsToHHHMM(sec):
    """Returns time in the format HHH:MM
    @rtype:  str
    @return: Time in the format HHH:MM"""
    return "%03d:%02d" % __splitTime(sec)[:2]


def secondsDiffToHMMSS(secA, secB):
    """Returns time difference of arguements in the format H:MM:SS
    @type  secA: int or float
    @param secA: Seconds. 0 will be replaced with current time
    @type  secB: int or float
    @param secB: Seconds. 0 will be replaced with current time
    @rtype:  str
    @return: Time difference of arguments in the format H:MM:SS"""
    if secA == 0:
        secA = time.time()
    if secB == 0:
        secB = time.time()
    return secondsToHMMSS(max(secA, secB) - min(secA, secB))


def convert_mem(kmem, unit=None):
    k = 1024
    if unit == 'K' or (unit is None and kmem < k):
        return '%dK' % kmem
    if unit == 'M' or (unit is None and kmem < pow(k, 2)):
        return '%dM' % (kmem / k)
    if unit == 'G' or (unit is None and kmem < pow(k, 3)):
        return '%.01fG' % (float(kmem) / pow(k, 2))
