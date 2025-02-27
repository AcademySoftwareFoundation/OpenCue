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

"""
Helper class for representing a frame seqeunce path.

It supports a complex syntax implementing features such as comma-separated frame ranges,
stepped frame ranges and more. See the FileSequence class for more detail.
"""

import re
from .FrameSet import FrameSet


class FileSequence:
    """Represents a file path to a frame sequence"""
    __filepath = None
    frameSet = None
    __basename = None
    __prefix = None
    __suffix = None
    __dirname = ""
    __padSize = 1
    __iter_index = 0

    def __init__(self, filepath):
        """
        Construct a FileSequence object by parsing a filepath.
        Details on how to specify a frame range can be seen in the FrameRange class
        """

        filePathMatch = re.match(r"^(?P<pf>.*\.)(?P<fspec>[\d#,\-@x]+)(?P<sf>\.[.\w]+)$", filepath)
        if filePathMatch is not None:
            self.__filepath = filepath
            self.__prefix = filePathMatch.group('pf')
            self.__suffix = filePathMatch.group('sf')
            dirmatch = re.match(r"^(?P<dirname>.*/)(?P<basename>.*)$", self.__prefix)
            if dirmatch is not None:
                self.__dirname = dirmatch.group("dirname")
                self.__basename = dirmatch.group("basename")
            else:
                self.__basename = self.__prefix
            framerangematch = re.match(r"^([\d\-x,]+)", filePathMatch.group("fspec"))
            if framerangematch is not None:
                self.frameSet = FrameSet(framerangematch.group(1))
                if self.frameSet.get(0) > self.frameSet.get(-1):
                    raise ValueError('invalid filesequence range : ' + framerangematch.group(1))
                firstFrameMatch = re.findall(r"^[-0]\d+", framerangematch.group(1))
                if len(firstFrameMatch) > 0:
                    self.__padSize = len(firstFrameMatch[0])

            padmatch = re.findall(r"#+$", filePathMatch.group("fspec"))
            if len(padmatch) > 0:
                self.__padSize = len(padmatch[0])
        else:
            raise ValueError('invalid filesequence path : ' + filepath)

    def getPrefix(self):
        """Returns the prefix of the file sequence"""
        return self.__prefix

    def getSuffix(self):
        """Returns the suffix of the file sequence"""
        return self.__suffix

    def getDirname(self):
        """Returns the dirname of the file sequence, if given otherwise returns empty an string"""
        return self.__dirname

    def getBasename(self):
        """Returns the base name of the file sequence"""
        return self.__basename.rstrip(".")

    def getPadSize(self):
        """Returns the size of the frame padding. It defaults to 1 if none is detected"""
        return self.__padSize

    def getFileList(self, frameSet=None):
        """ Returns the file list of the sequence """
        filelist = []
        paddingString = "%%0%dd" % self.getPadSize()
        if self.frameSet:
            for frame in self.frameSet.getAll():
                if (frameSet is None or
                        (isinstance(frameSet, FrameSet) and frame in frameSet.getAll())):
                    framepath = self.getPrefix() + paddingString % frame + self.getSuffix()
                    filelist.append(framepath)
        else:
            for frame in frameSet.getAll():
                framepath = self.getPrefix() + paddingString % frame + self.getSuffix()
                filelist.append(framepath)
        return filelist

    def getOpenRVPath(self, frameSet=None):
        """ Returns a string specific for the OpenRV player"""
        frameRange = ""
        curFrameSet = frameSet or self.frameSet
        if isinstance(curFrameSet, FrameSet):
            frameRange = "%d-%d" % (curFrameSet.get(0), curFrameSet.get(-1))
        framepath = self.getPrefix() + frameRange + "@"*self.__padSize + self.getSuffix()
        return framepath

    def __getitem__(self, index):
        return self.getFileList()[index]

    def __next__(self):
        self.__iter_index += 1
        if self.__iter_index <= len(self):
            return self.getFileList()[self.__iter_index - 1]
        raise StopIteration

    def __iter__(self):
        self.__iter_index = 0
        return self

    def __len__(self):
        return len(self.getFileList())

    def __call__(self, frame):
        paddingString = "%%0%dd" % self.getPadSize()
        framepath = self.getPrefix() + paddingString % frame + self.getSuffix()
        return framepath

    def __str__(self):
        return self.__filepath
