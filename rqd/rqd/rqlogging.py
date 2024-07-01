
import time
import os
import tempfile
import datetime


def createLogger(filepath):
    f = RQDLogger(filepath)
    return f


class RQDLogger(tempfile.SpooledTemporaryFile):

    filepath = None
    fd = None

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
        self.fd = open(self.filepath, "w+", 1)

    def write(self, string, prependTimestamp=False):
        if prependTimestamp is True:
            lines = string.splitlines()
            curr_line_timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            for line in lines:
                print("[%s] %s" % (curr_line_timestamp, line), file=self)
        else:
            self.fd.write(string)

    def writelines(self, __lines):
        for line in __lines:
            self.write(line)

    def close(self):
        self.fd.close()

    def waitForFile(self, maxTries=5):
        """Waits for a file to exist."""
        tries = 0
        while tries < maxTries:
            if os.path.exists(self.filepath):
                return
            tries += 1
            time.sleep(0.5 * tries)
        raise IOError("Failed to create %s" % self.filepath)
