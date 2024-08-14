
import logging
import os
import platform
import datetime
import time

log = logging.getLogger(__name__)

MODE_READ = 0
MODE_WRITE = 1

class CueLogger(object):
    """Class to abstract file logging, this class tries to act as a file object"""
    filepath = None
    fd = None
    type = 0
    mode = 0  # 0 for read, 1 for write

    def __init__(self, filepath, mode, maxLogFiles=1):
        """RQDLogger class initialization
           @type    filepath: string
           @param   filepath: The filepath to log to
        """

        self.filepath = filepath
        self.mode = mode
        if self.mode == MODE_WRITE:
            log_dir = os.path.dirname(self.filepath)
            if not os.access(log_dir, os.F_OK):
                # Attempting mkdir for missing logdir
                msg = "No Error"
                try:
                    os.makedirs(log_dir)
                    os.chmod(log_dir, 0o777)
                # pylint: disable=broad-except
                except Exception as e:
                    # This is expected to fail when called in abq
                    # But the directory should now be visible
                    msg = e

                if not os.access(log_dir, os.F_OK):
                    err = "Unable to see log directory: %s, mkdir failed with: %s" % (
                        log_dir, msg)
                    raise RuntimeError(err)

            if not os.access(log_dir, os.W_OK):
                err = "Unable to write to log directory %s" % log_dir
                raise RuntimeError(err)

            try:
                # Rotate any old logs to a max of MAX_LOG_FILES:
                if os.path.isfile(self.filepath):
                    rotateCount = 1
                    while (os.path.isfile("%s.%s" % (self.filepath, rotateCount))
                           and rotateCount < maxLogFiles):
                        rotateCount += 1
                    os.rename(self.filepath,
                              "%s.%s" % (self.filepath, rotateCount))
            # pylint: disable=broad-except
            except Exception as e:
                err = "Unable to rotate previous log file due to %s" % e
                # Windows might fail while trying to rotate logs for checking if file is
                # being used by another process. Frame execution doesn't need to
                # be halted for this.
                if platform.system() == "Windows":
                    log.warning(err)
                else:
                    raise RuntimeError(err)
            # pylint: disable=consider-using-with
            self.fd = open(self.filepath, "w+", 1, encoding='utf-8')
            try:
                os.chmod(self.filepath, 0o666)
            # pylint: disable=broad-except
            except Exception as e:
                err = "Failed to chmod log file! %s due to %s" % (self.filepath, e)
                log.warning(err)
        elif mode == MODE_READ:
            self.fd = open(self.filepath, "r", encoding='utf-8')
        else:
            log.error("Unknown mode for log file!")

    # pylint: disable=arguments-differ
    def write(self, data, prependTimestamp=False):
        """Abstract write function that will write to the correct backend"""
        # Only work if in write mode, otherwise ignore
        if self.mode == MODE_WRITE:
            # Convert data to unicode
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
            if prependTimestamp is True:
                lines = data.splitlines()
                curr_line_timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                for line in lines:
                    print("[%s] %s" % (curr_line_timestamp, line), file=self)
            else:
                self.fd.write(data)

    def writelines(self, __lines):
        """Provides support for writing mutliple lines at a time"""
        for line in __lines:
            self.write(line)

    def close(self):
        """Closes the file if the backend is file based"""
        self.fd.close()

    def waitForFile(self, maxTries=5):
        """Waits for the file to exist before continuing when using a file backend"""
        # Waits for a file to exist
        tries = 0
        while tries < maxTries:
            if os.path.exists(self.filepath):
                return
            tries += 1
            time.sleep(0.5 * tries)
        raise IOError("Failed to create %s" % self.filepath)

    def size(self):
        """Return the size of the file"""
        return int(os.stat(self.filepath).st_size)

    def getMtime(self):
        """Return modification time of the file"""
        return os.path.getmtime(self.filepath)

    def exists(self):
        """Check if the file exists"""
        return os.path.exists(self.filepath)

    def read(self):
        """Read the data from the backend"""
        # Only allow reading when in read mode
        if self.mode == MODE_READ:
            content = None
            if self.exists() is True:
                with open(self.filepath, "r", encoding='utf-8') as fp:
                    content = fp.read()

            return content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
