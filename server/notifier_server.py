import datetime
import os
import time

import common.asg
import common.aws_client
import common.logger
import notify
import server.base_server


class StableEnoughNotifyServer(server.base_server.Server):
    def __init__(self, name, option,
                 make_up_stable_enough_event_pipe_w, make_up_stable_enough_event_ack_pipe_r,
                 make_down_stable_enough_event_pipe_w, make_down_stable_enough_event_ack_pipe_r):
        super(StableEnoughNotifyServer, self).__init__(common.logger(name), name, option)
        if make_up_stable_enough_event_pipe_w is None:
            raise Exception("make up stable enough event pipe writer is None")
        if make_down_stable_enough_event_pipe_w is None:
            raise Exception("make down stable enough event pipe writer is None")
        self._make_up_stable_enough_event_pipe_w = make_up_stable_enough_event_pipe_w
        self._make_down_stable_enough_event_pipe_w = make_down_stable_enough_event_pipe_w
        self._make_up_stable_enough_watcher = notify.MakeUpStableEnoughWatcher(self._log)
        self._make_down_stable_enough_watcher = notify.MakeDownStableEnoughWatcher(self._log)
        self._epoch = 0
        self._aws_session = common.aws_client.new_session(self._option)

    def serve(self):
        start_time = datetime.datetime.now()

        while not self._stop_flag.is_set():
            self._epoch += 1

            try:
                # query desired capacity and the number of instances from both autoscaling groups
                try:
                    spot_asg_desired_capacity, spot_asg_instance_count, spot_asg_instances = \
                        common.asg.get_asg_counts_instances(self._stop_flag, self._log,
                                                            self._aws_session, self._option.spot_asg_name,
                                                            logging=True)
                except Exception as e:
                    self._log.error("failed to query the spot autoscaling group '{}', ignore: {}".format(
                        self._option.spot_asg_name, str(e)))
                    continue

                self._make_up_stable_enough_watcher.watch(spot_asg_desired_capacity, spot_asg_instances)
                self._make_down_stable_enough_watcher.watch(spot_asg_desired_capacity, spot_asg_instances)

                # can happen either make up or down
                if self._make_up_stable_enough_watcher.is_stable_enough(self._option.wait_time):
                    try:
                        self._make_up_stable_enough_event_pipe_w.send(
                            notify.StableEnoughEvent(spot_asg_desired_capacity, spot_asg_instance_count))
                        self._log.info("a make up stable enough event has been sent ({}, {} at epoch {})".format(
                            spot_asg_desired_capacity, spot_asg_instance_count, self._epoch))
                    except ValueError as e:  # failed to write pipe connection
                        self._log.warn("failed to send the stable enough event to "
                                       "'make_up_stable_enough_event_pipe_w' pipe: %s" % str(e))

                # can happen either make up or down
                if self._make_down_stable_enough_watcher.is_stable_enough(self._option.wait_time):
                    try:
                        self._make_down_stable_enough_event_pipe_w.send(
                            notify.StableEnoughEvent(spot_asg_desired_capacity, spot_asg_instance_count))
                        self._log.info("a make down stable enough event has been sent ({}, {} at epoch {})".format(
                            spot_asg_desired_capacity, spot_asg_instance_count, self._epoch))
                    except ValueError as e:  # failed to write pipe connection
                        self._log.warn("failed to send the stable enough event to "
                                       "'make_down_stable_enough_event_pipe_w' pipe: %s" % str(e))

                if self._option.run_once and (datetime.datetime.now() - start_time).seconds > self._option.wait_time:
                    # check once, at least
                    self.stop()
                    # dismiss handler servers
                    self._make_up_stable_enough_event_pipe_w.send(notify.NoneStableEnoughEvent)
                    self._make_down_stable_enough_event_pipe_w.send(notify.NoneStableEnoughEvent)
                else:
                    self._log.debug("wait to watch the spot autoscaling group '{}' for next around, interval: {}".
                                    format(self._option.spot_asg_name, self._option.interval))

                    # FIXME(zhiyan): this method blocks self._stop_flag.set() calls from signal handler
                    #  _server_process_signal_handler() in Server.stop(), so using polling instead:
                    #  self._stop_flag.wait(timeout=self._option.interval)
                    sec_elapsed = 0
                    while not self._stop_flag.is_set() and sec_elapsed < self._option.interval:
                        time.sleep(1)
                        sec_elapsed += 1
            except Exception as e:
                self._log.error("failure in the server '{}', ignore: {}".format(self._name, str(e)), exc_info=True)
                continue

    def release(self):
        super(StableEnoughNotifyServer, self).release()
        self._log.info("the server '{}' has been released at epoch {}, pid = {}".format(
            self._name, self._epoch, os.getpid()))
