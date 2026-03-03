import logging
from PySide6.QtCore import QObject, Signal

class QtSignalingHandler(logging.Handler, QObject):
    """
    Custom logging handler that emits a Signal when a log message is received.
    Allows UI components to listen to logs safely.
    """
    log_signal = Signal(str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.log_signal.emit(msg)
