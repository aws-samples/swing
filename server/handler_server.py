import os

import common.asg
import common.aws_client
import common.logger
import handle
import server.base_server


class _CompensationServer(server.base_server.Server):
    def __init__(self, log, name, option, stable_enough_event_pipe_r, stable_enough_event_ack_pipe_w, evaluator_class):
        super(_CompensationServer, self).__init__(log, name, option)
        if stable_enough_event_pipe_r is None:
            raise Exception("stable enough event pipe reader is None")
        self._stable_enough_event_pipe_r = stable_enough_event_pipe_r
        self._aws_session = common.aws_client.new_session(self._option)
        self._evaluator = evaluator_class(self._stop_flag, self._log, self._aws_session, self._option)

    def _handle(self, instances_count_gap):
        raise Exception("not implemented")

    def serve(self):
        while not self._stop_flag.is_set():
            try:
                # poll with timeout for server stop checking
                ret = self._stable_enough_event_pipe_r.poll(1)
                if not ret:  # no more event
                    continue

                event = self._stable_enough_event_pipe_r.recv()

                if event.is_none():
                    return  # dismiss, no more notify event

                self._log.debug("a stable enough event received ({}, {})".format(
                    event.spot_asg_desired_capacity, event.spot_asg_instance_count))

                if not self._evaluator.if_event_is_valid(event):
                    self._log.warn("the desired capacity or the number of the instances of the "
                                   "spot autoscaling group '{}' has been updated during the handling, skip".
                                   format(self._option.spot_asg_name))
                    continue

                need_handle, ondemand_asg_desired_capacity, watermark = self._evaluator.if_need_handle(event)
                if not need_handle:
                    self._log.info("autoscaling groups ['{}', '{}'] do not need to handle, "
                                   "the number of the instances for each is [{}, {}], total is {}, watermark is {}".
                                   format(self._option.spot_asg_name, self._option.ondemand_asg_name,
                                          event.spot_asg_instance_count, ondemand_asg_desired_capacity,
                                          event.spot_asg_instance_count + ondemand_asg_desired_capacity,
                                          watermark))
                    continue

                instances_count_gap = self._evaluator.calc_instances_count_gap(event, ondemand_asg_desired_capacity)

                if 0 == instances_count_gap:
                    continue

                self._handle(instances_count_gap)
            except EOFError:  # write pipe connection closed
                self._log.info("the server running stable enough notify existed, "
                               "the compensation handling server exits")
                return  # no more event need to handle
            except Exception as e:
                self._log.error("failure in the server '{}', ignore: %s".format(self._name, str(e)), exc_info=True)
                continue

    def release(self):
        super(_CompensationServer, self).release()
        self._log.info("the server '{}' has been released, pid = {}".format(self._name, os.getpid()))


class MakeUpServer(_CompensationServer):
    def __init__(self, name, option, make_up_stable_enough_event_pipe_r, make_up_stable_enough_event_ack_pipe_w):
        super(MakeUpServer, self).__init__(common.logger(name), name, option,
                                           make_up_stable_enough_event_pipe_r,
                                           make_up_stable_enough_event_ack_pipe_w,
                                           handle.MakeUpEvaluator)

    def _handle(self, make_up_instance_count):
        self._log.info("need to increase {} on-demand instance(s) to the autoscaling group '{}'".format(
            make_up_instance_count, self._option.ondemand_asg_name))

        try:
            common.asg.up_asg_desired_capacity(self._stop_flag, self._log, self._aws_session,
                                               self._option.ondemand_asg_name, make_up_instance_count)
        except Exception as e:
            self._log.error("failed to make up on-demand instance by increasing the desired capability of "
                            "the autoscaling group '{}': {}".format(self._option.ondemand_asg_name, str(e)),
                            exc_info=True)


class MakeDownServer(_CompensationServer):
    def __init__(self, name, option, make_down_stable_enough_event_pipe_r, make_down_stable_enough_event_ack_pipe_w):
        super(MakeDownServer, self).__init__(common.logger(name), name, option,
                                             make_down_stable_enough_event_pipe_r,
                                             make_down_stable_enough_event_ack_pipe_w,
                                             handle.MakeDownEvaluator)

    def _handle(self, make_down_instance_count):
        self._log.info("need to decrease {} on-demand instance(s) from the autoscaling group '{}'".format(
            make_down_instance_count, self._option.ondemand_asg_name))

        try:
            common.asg.down_asg_desired_capacity(self._stop_flag, self._log, self._aws_session,
                                                 self._option.ondemand_asg_name, make_down_instance_count)
        except Exception as e:
            self._log.error("failed to make down on-demand instance by decreasing the desired capability of "
                            "the autoscaling group '{}': {}".format(self._option.ondemand_asg_name, str(e)),
                            exc_info=True)
