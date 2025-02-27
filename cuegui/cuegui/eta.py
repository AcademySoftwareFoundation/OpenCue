#! /usr/local/bin/python

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


"""Functions for estimating time remaining on a frame."""


from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from builtins import object
import datetime
import functools
import linecache
import os
import re
import time
import xml.dom.minidom

import opencue


class FrameEtaGenerator(object):
    """Parses log files and job data for ETC info."""

    def __init__(self):
        self.buildTimeCache = {}
        self.startTimeCache = {}
        self.frame_results = {'time_left': 0, 'total_completion': 0}
        self.time_left = 0
        self.total_completion = 0
        self.scene_build_time = 0
        self.scene_build_seconds = 0
        self.percents = []
        self.simTimes = []
        self.log = ''
        self.log_lines = 0

    # pylint: disable=bare-except
    def GetFrameEta(self, job, frame):
        """Gets ETA for the given frame."""
        self.log = opencue.util.logPath(job, frame)
        if os.path.isfile(self.log):
            with open(self.log, encoding='utf-8') as fp:
                self.log_lines = len(fp.readlines())
            self.GetFrameBuildTime(frame)
        try:
            layer = opencue.api.findLayer(job.data.name, frame.data.layer_name)
            if 'tango' in layer.data.services:
                self.Tango(frame)
            elif 'svea' in layer.data.services:
                self.Svea(frame)
            elif 'arnold' in layer.data.services:
                self.Arnold(frame)
        except:
            pass
        self.frame_results['time_left'] = self.time_left
        self.frame_results['total_completion'] = self.total_completion
        self.frame_results['scene_build_time'] = self.scene_build_time
        self.frame_results['scene_build_seconds'] = self.scene_build_seconds
        try:
            self.frame_results['percent_complete'] = self.percents[0][0]
        except:
            self.frame_results['percent_complete'] = 0
        linecache.clearcache()
        return self.frame_results

    def Tango(self, frame):
        """Calculates ETA for a Tango frame."""
        del frame

        simTimes = []
        if os.path.isfile(self.log):
            line = ''
            line_counter = 0
            while 'Done with Frame' not in line:
                line = linecache.getline(self.log, self.log_lines-line_counter)
                line_counter += 1
                if line_counter == self.log_lines:
                    break
            frameTime = line.split("=")[1].split(",")[0].strip(" ") # Extract frame time
            if float(frameTime) > 0:
                simTimes.append(float(frameTime))
                lastFrame = line.split('#')[1].split(".")[0].strip(" ") # Extract the last frame
            line_counter = 100
            line = ''
            while 'Loading XML file:' not in line:
                line = linecache.getline(self.log, line_counter)
                line_counter += 1
                if line_counter == self.log_lines:
                    break
            xml_loc = line.split(":")[1].strip(" ").rstrip("\n") # Extract the XML from the line
            start_frame, end_frame = self.GetSimFrameRange(xml_loc) # Get the start and end points
            simTimes = sorted(simTimes, reverse=True)
            framesLeft = int(end_frame) - int(lastFrame)
            self.time_left = float(simTimes[0]) * float(framesLeft)
            self.percents.append(((float(start_frame) / int(end_frame)) * 100, self.time_left))
            self.percents.append((0, 0))
            self.percents = sorted(self.percents, reverse=True)
            if len(self.percents) > 1:
                self.total_completion = (
                        (self.percents[0][1] - self.percents[-1][1]) *
                        (100 / (self.percents[0][0] - self.percents[-1][0])))

    def Svea(self, frame):
        """Calculates ETA for a Svea frame."""
        del frame
        if os.path.isfile(self.log):
            line = ''
            with open(self.log, encoding='utf-8') as fp:
                for line in reversed(fp.readlines()):
                    # Checks log directory for a percentage complete in reverse to limit time in log
                    if 'Running generator batch' in line:
                        # pylint: disable=bare-except
                        try:
                            time_on_log = self.GetSeconds(line)
                            line = line.split(' ')
                            current = float(line[16])
                            total = float(line[18].split('\n')[0])
                            percent = float(current / total) * 100
                            self.percents.append((percent, time_on_log))
                            if len(self.percents) > 1:
                                break
                        except:
                            pass
            if len(self.percents) > 1:
                self.percents = sorted(self.percents, reverse=True)
                self.total_completion = (
                        (self.percents[0][1] - self.percents[-1][1]) *
                        (100 / (self.percents[0][0] - self.percents[-1][0])))
                self.time_left = self.total_completion * ((100-self.percents[0][0]) / 100)
            else:
                self.percents.append((0, 0))

    def Arnold(self, frame):
        """Calculates ETA for an Arnold frame."""
        if os.path.isfile(self.log):
            buildTime = self.GetFrameBuildTime(frame)
            self.scene_build_seconds = buildTime['scene_build_seconds']
            self.scene_build_time = buildTime['scene_build_time']
            if self.scene_build_seconds != 0:
                # Doesn't look for percentages if it can't find a scenebuild.
                line = self.GetFrameStartTime(frame)
                if line != '':
                    # Doesn't look for anything else if it can't find a first %.
                    self.GetPercent(line)
                    line_counter = 0
                    line = ''
                    while '% done' not in line:
                        line = linecache.getline(self.log,self.log_lines-line_counter)
                        line_counter += 1
                        if line_counter == self.log_lines:
                            break
                    if line_counter != self.log_lines:
                        self.GetPercent(line)
            if len(self.percents) > 1:
                self.percents = sorted(self.percents, reverse=True)
                if len(self.percents) == 1 and self.percents[0][0] % 5 == 0:
                    self.total_completion = self.percents[0][1] * 20
                else:
                    if self.percents[0][0] == self.percents[-1][0]:
                        self.percents[-1]=(self.percents[0][0]-5,self.scene_build_seconds)
                    self.total_completion = (
                            (self.percents[0][1] - self.percents[-1][1]) *
                            (100 / (self.percents[0][0] - self.percents[-1][0])))
                self.time_left = self.total_completion * ((100 - self.percents[0][0]) / 100)
            else:
                self.percents.append((0, 0))

    def GetFrameStartTime(self, frame):
        """Gets a frame start time."""
        key = (frame, frame.data.start_time)
        if key in self.startTimeCache:
            return self.startTimeCache[key]
        # Read the logFile here for time.
        result = ''
        with open(self.log, encoding='utf-8') as fp:
            for line in fp:
                if '% done' in line:
                    result = line
                    break
        if not result:
            return result
        self.startTimeCache[key] = result
        return result

    def GetFrameBuildTime(self, frame):
        """Gets a frame build time."""
        key = (frame, frame.data.start_time)
        if key in self.buildTimeCache:
            return self.buildTimeCache[key]
        # Read the logFile here for time.
        result_line = None
        with open(self.log, encoding='utf-8') as fp:
            for line in fp:
                if 'Building scene done' in line:
                    result_line = line
                    break
        if result_line is not None:
            result = {
                'scene_build_seconds': self.GetSeconds(result_line),
                'scene_build_time': result_line.split(' ')[3]}
        else:
            result = {'scene_build_seconds': 0, 'scene_build_time': 0}
            return result
        if not result:
            return result
        self.buildTimeCache[key] = result
        return result

    def GetPercent(self, line):
        """Gets a percentage from a given log line."""
        # pylint: disable=bare-except
        try:
            percent_location = line.find('%')
            percent = float(
                line[percent_location-3] + line[percent_location-2] + line[percent_location-1])
            time_on_log = self.GetSeconds(line)
            self.percents.append((percent, time_on_log))
        except:
            pass

    @staticmethod
    def GetSeconds(line):
        """Gets a number of seconds from a timestamp found in a log line."""
        time_str = re.search('([0-9]+):([0-9]{2}):([0-9]{2})', line)
        hour = int(time_str.group(1))
        minute = int(time_str.group(2))
        second = int(time_str.group(3))
        seconds = (hour * 3600) + (minute * 60) + second
        return seconds

    @staticmethod
    def GetSimFrameRange(xml_loc):
        """Reads the SimRender XML to get the frame range."""
        try:
            name = xml.dom.minidom.parse(xml_loc)
        except IOError:
            raise IOError("Unable to find xml file to parse at %s" % xml_loc)

        global_tag = name.getElementsByTagName('SimGlobals')[0]
        start_frame = global_tag.getElementsByTagName('start')[0].childNodes[0].nodeValue
        end_frame = global_tag.getElementsByTagName('end')[0].childNodes[0].nodeValue
        return start_frame, end_frame


def ETAString(job, frame):
    """Calculates ETA and returns it as a formatted string."""
    eta = FrameEtaGenerator()
    time_left = eta.GetFrameEta(job, frame)['time_left']
    t = datetime.datetime.now()
    now_epoch = time.mktime(t.timetuple())
    time_left = datetime.datetime.fromtimestamp(time_left+now_epoch).strftime('%m/%d %H:%M:%S')
    return time_left


def ETADateTime(job, frame):
    """Calculates ETA and returns it as a datetime."""
    eta = FrameEtaGenerator()
    time_left = eta.GetFrameEta(job, frame)['time_left']
    t = datetime.datetime.now()
    now_epoch = time.mktime(t.timetuple())
    time_left = datetime.datetime.fromtimestamp(time_left + now_epoch)
    return time_left


def ETASeconds(job, frame):
    """Calculates ETA and returns it as a number of seconds."""
    eta = FrameEtaGenerator()
    time_left = eta.GetFrameEta(job, frame)['time_left']
    return time_left


class Memoize(object):
    """From: https://gist.github.com/267733/8f5d2e3576b6a6f221f6fb7e2e10d395ad7303f9"""
    def __init__(self, func):
        self.func = func
        self.memoized = {}
        self.method_cache = {}

    def __call__(self, *args):
        return self.__cache_get(self.memoized, args, lambda: self.func(*args))

    def __get__(self, obj, objtype):
        return self.__cache_get(
            self.method_cache, obj, lambda: self.__class__(functools.partial(self.func, obj)))

    @staticmethod
    def __cache_get(cache, key, func):
        try:
            return cache[key]
        except KeyError:
            result = func()
            cache[key] = result
            return result
