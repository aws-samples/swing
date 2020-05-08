import multiprocessing
import multiprocessing.queues
import os
import signal
import time

import common

# per process
_server_process_server = None


def _server_process_signal_handler(sig, frame):
    global _server_process_server

    if _server_process_server is not None:
        print("%s signal SIGTERM received" % _server_process_server.name())
        print("stop %s" % _server_process_server.name())
        _server_process_server.stop()


def _server_process_watchdog(log, server_creator, server_serving_event, server_released_event,
                             server_creator_args, server_serve_kwargs):
    global _server_process_server

    _server_process_server = server_creator(*server_creator_args)

    log.info("%s is serving, pid = %d" % (_server_process_server.name(), os.getpid()))
    server_serving_event.set()
    _server_process_server.serve(**server_serve_kwargs)
    log.info("%s exits" % _server_process_server.name())
    _server_process_server.release()
    log.info("%s released" % _server_process_server.name())
    server_released_event.set()


class ServerProcess:
    def __init__(self, name, server_creator, *server_creator_args):
        if server_creator is None:
            raise Exception("%s creator is None" % name)
        self._log = common.logger(name)
        self._name = name
        self._server_creator = server_creator
        self._server_creator_args = server_creator_args
        self._pid = None
        self._released_event = multiprocessing.Event()

    def name(self):
        return self._name

    def start(self, **kwargs):
        server_serving_event = multiprocessing.Event()
        default_handler = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, _server_process_signal_handler)
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # disable KeyboardInterrupt
        self._pid = multiprocessing.Process(name=self._name, target=_server_process_watchdog,
                                            args=(self._log, self._server_creator,
                                                  server_serving_event, self._released_event,
                                                  self._server_creator_args, kwargs))
        self._pid.start()
        signal.signal(signal.SIGTERM, default_handler)
        while not server_serving_event.is_set():
            time.sleep(0.2)
        return self._pid.is_alive()

    def join(self):
        if self._pid is not None:
            self._pid.join()

    def stop(self):
        if self._pid is not None and self._pid.is_alive:
            os.kill(self._pid.pid, signal.SIGTERM)
            while not self._released_event.is_set():
                time.sleep(0.2)
            self._pid.join()
            self._pid.close()
            self._pid = None
