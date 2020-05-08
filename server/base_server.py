import multiprocessing


class Server:
    def __init__(self, log, name, option):
        self._log = log
        self._name = name
        self._option = option
        self._stop_flag = multiprocessing.Event()

    def name(self):
        return self._name

    def stop(self):
        self._stop_flag.set()

    def release(self):
        pass
