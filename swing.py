import multiprocessing
import os
import signal
import sys

import common
import common.aws_client
import common.process
import config
import server

stable_enough_notifier_process = None
make_up_handler_process = None
make_down_handler_process = None

make_up_stable_enough_event_send_pipe_r, make_up_stable_enough_event_send_pipe_w = multiprocessing.Pipe(False)
make_up_stable_enough_event_ack_pipe_r, make_up_stable_enough_event_ack_pipe_w = multiprocessing.Pipe(False)
make_down_stable_enough_event_send_pipe_r, make_down_stable_enough_event_send_pipe_w = multiprocessing.Pipe(False)
make_down_stable_enough_event_ack_pipe_r, make_down_stable_enough_event_ack_pipe_w = multiprocessing.Pipe(False)

__done_loop = multiprocessing.Event()


def __signal_handler(sig, frame):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

    print("signal {} received, stopping".format(signal.Signals(sig).name))
    __done_loop.set()

    if stable_enough_notifier_process is not None:
        stable_enough_notifier_process.stop()
    if make_up_handler_process is not None:
        make_up_handler_process.stop()
    if make_down_handler_process is not None:
        make_down_handler_process.stop()

    make_up_stable_enough_event_send_pipe_w.close()
    make_up_stable_enough_event_send_pipe_r.close()
    make_up_stable_enough_event_ack_pipe_w.close()
    make_up_stable_enough_event_ack_pipe_r.close()
    make_down_stable_enough_event_send_pipe_w.close()
    make_down_stable_enough_event_send_pipe_r.close()
    make_down_stable_enough_event_ack_pipe_w.close()
    make_down_stable_enough_event_ack_pipe_r.close()


def __main():
    global stable_enough_notifier_process, make_up_handler_process, make_down_handler_process

    log = common.logger("swing")

    log.info("parse and validate arguments")
    option = config.prepare_args(__done_loop, common.aws_client.new_session())

    stable_enough_notifier_process = common.process.ServerProcess("stable-enough-notifier-process",
                                                                  server.stable_enough_notifier_server_creator,
                                                                  option,
                                                                  make_up_stable_enough_event_send_pipe_w,
                                                                  make_up_stable_enough_event_ack_pipe_r,
                                                                  make_down_stable_enough_event_send_pipe_w,
                                                                  make_down_stable_enough_event_ack_pipe_r)

    make_up_handler_process = common.process.ServerProcess("make-up-handler-process",
                                                           server.make_up_handler_server_creator,
                                                           option,
                                                           make_up_stable_enough_event_send_pipe_r,
                                                           make_up_stable_enough_event_ack_pipe_w)

    make_down_handler_process = common.process.ServerProcess("make-down-handler-process",
                                                             server.make_down_handler_server_creator,
                                                             option,
                                                             make_down_stable_enough_event_send_pipe_r,
                                                             make_down_stable_enough_event_ack_pipe_w)

    ret = stable_enough_notifier_process.start()
    if ret:
        log.debug("%s is running" % stable_enough_notifier_process.name())
    ret = make_up_handler_process.start()
    if ret:
        log.debug("%s is running" % make_up_handler_process.name())
    ret = make_down_handler_process.start()
    if ret:
        log.debug("%s is running" % make_down_handler_process.name())

    log.info("swing is running")

    signal.signal(signal.SIGTERM, __signal_handler)
    signal.signal(signal.SIGINT, __signal_handler)

    stable_enough_notifier_process.join()
    make_up_handler_process.join()
    make_down_handler_process.join()

    log.info("program normally exits")
    sys.exit(0)


try:
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # disable Ctrl+C temporarily
    __main()
except KeyboardInterrupt:
    os.kill(0, signal.SIGINT)
