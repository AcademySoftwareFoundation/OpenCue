from PySide2 import QtCore
import gc

class GarbageCollector(QtCore.QObject):

    '''
    Disable automatic garbage collection and instead collect manually
    every INTERVAL milliseconds.

    This is done to ensure that garbage collection only happens in the GUI
    thread, as otherwise Qt can crash.
    '''

    INTERVAL = 5000

    def __init__(self, parent, debug=False):
        QtCore.QObject.__init__(self, parent)
        self.debug = debug

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check)

        self.threshold = gc.get_threshold()
        gc.disable()
        self.timer.start(self.INTERVAL)

    def check(self):
        gc.collect()
        if self.debug:
            for obj in gc.garbage:
                print (obj, repr(obj), type(obj))
