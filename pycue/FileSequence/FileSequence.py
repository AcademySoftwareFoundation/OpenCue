
import re
from .FrameSet import FrameSet


class FileSequence:
    __filepath = None
    frameSet = None
    __basename = None
    __prefix = None
    __suffix = None
    __dirname = ""
    __padSize = 1

    def __init__(self, filepath):
        filePathMatch = re.match(r"^(?P<prefix>.*\.)(?P<framespec>[\d#,\-@x]+)(?P<suffix>\.[.\w]+)$", filepath)
        if filePathMatch is not None:
            self.__filepath = filepath
            self.__prefix = filePathMatch.group('prefix')
            self.__suffix = filePathMatch.group('suffix')
            dirmatch = re.match(r"^(?P<dirname>.*/)(?P<basename>.*)$", self.__prefix)
            if dirmatch is not None:
                self.__dirname = dirmatch.group("dirname")
                self.__basename = dirmatch.group("basename")
            else:
                self.__basename = self.__prefix
            framerangematch = re.match(r"^([\d\-x,]+)", filePathMatch.group("framespec"))
            if framerangematch is not None:
                self.frameSet = FrameSet(framerangematch.group(1))
                if self.frameSet.get(0) > self.frameSet.get(-1):
                    raise ValueError('invalid filesequence range : ' + framerangematch.group(1))
                firstFrameMatch = re.findall(r"^[-0]\d+", framerangematch.group(1))
                if len(firstFrameMatch) > 0:
                    self.__padSize = len(firstFrameMatch[0])

            padmatch = re.findall(r"#+$", filePathMatch.group("framespec"))
            if len(padmatch) > 0:
                self.__padSize = len(padmatch[0])
        else:
            raise ValueError('invalid filesequence path : ' + filepath)

    def getPrefix(self):
        return self.__prefix

    def getSuffix(self):
        return self.__suffix

    def getDirname(self):
        return self.__dirname

    def getBasename(self):
        return self.__basename.rstrip(".")

    def getPadSize(self):
        return self.__padSize
