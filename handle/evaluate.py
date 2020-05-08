import math

import common.asg


class _Evaluator:
    def __init__(self, stop_flag, log, aws_session, option):
        self._stop_flag = stop_flag
        self._log = log
        self._aws_session = aws_session
        self._option = option

    def _get_watermark(self, event):
        return (1 - self._option.max_shortage_ratio) * event.spot_asg_desired_capacity

    def _get_ondemand_asg_desired_capacity(self):
        try:
            # query desired capacity and the number of instances from both autoscaling groups
            ondemand_asg_desired_capacity, _, _ = common.asg.get_asg_counts_instances(
                self._stop_flag, self._log, self._aws_session, self._option.ondemand_asg_name)
            return ondemand_asg_desired_capacity
        except Exception as e:
            self._log.error("failed to query the on-demand autoscaling group '{}', ignore: {}".format(
                self._option.ondemand_asg_name, str(e)))
            return -1

    def if_event_is_valid(self, event):
        try:
            # query desired capacity and the number of instances from both autoscaling groups
            spot_asg_desired_capacity, spot_asg_instance_count, _ = common.asg.get_asg_counts_instances(
                self._stop_flag, self._log, self._aws_session, self._option.spot_asg_name)
            return event.validate(spot_asg_desired_capacity, spot_asg_instance_count)
        except Exception as e:
            self._log.error("failed to query the spot autoscaling group '{}', ignore: {}".format(
                self._option.spot_asg_name, str(e)))
            return False

    def if_need_handle(self, event):
        raise Exception("not implemented")

    def calc_instances_count_gap(self, event, ondemand_asg_desired_capacity):
        raise Exception("not implemented")


class MakeUpEvaluator(_Evaluator):
    def __init__(self, stop_flag, log, aws_session, option):
        super(MakeUpEvaluator, self).__init__(stop_flag, log, aws_session, option)

    def if_need_handle(self, event):
        water_mark = self._get_watermark(event)
        ondemand_asg_desired_capacity = self._get_ondemand_asg_desired_capacity()
        return ((event.spot_asg_instance_count + ondemand_asg_desired_capacity) < water_mark,
                ondemand_asg_desired_capacity, water_mark)

    def calc_instances_count_gap(self, event, ondemand_asg_desired_capacity):
        water_mark = self._get_watermark(event)

        total_instances_count_gap = water_mark - event.spot_asg_instance_count - ondemand_asg_desired_capacity
        if 0 == total_instances_count_gap:
            # defensive
            return 0

        spot_instances_count_gap = water_mark - event.spot_asg_instance_count

        self._log.info("found {} insufficient spot instance(s) in the autoscaling group '{}'".format(
            spot_instances_count_gap, self._option.spot_asg_name))

        self._log.info("found {} insufficient on-demand instance(s) in the autoscaling group '{}'".format(
            total_instances_count_gap, self._option.ondemand_asg_name))

        make_up_count = min(math.ceil(spot_instances_count_gap * self._option.step_ratio),
                            total_instances_count_gap)

        return make_up_count


class MakeDownEvaluator(_Evaluator):
    def __init__(self, stop_flag, log, aws_session, option):
        super(MakeDownEvaluator, self).__init__(stop_flag, log, aws_session, option)

    def if_need_handle(self, event):
        water_mark = self._get_watermark(event)
        ondemand_asg_desired_capacity = self._get_ondemand_asg_desired_capacity()
        return ((event.spot_asg_instance_count + ondemand_asg_desired_capacity) > water_mark,
                ondemand_asg_desired_capacity, water_mark)

    def calc_instances_count_gap(self, event, ondemand_asg_desired_capacity):
        water_mark = self._get_watermark(event)

        total_instances_count_gap = event.spot_asg_instance_count + ondemand_asg_desired_capacity - water_mark
        if 0 == total_instances_count_gap:
            # defensive
            return 0

        make_down_count = min(math.ceil(ondemand_asg_desired_capacity * self._option.step_ratio),
                              total_instances_count_gap)

        return make_down_count
