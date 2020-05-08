import datetime


class _WatchRecord:
    def __init__(self, desired_capacity, ec2_instances):
        self.__desired_capacity = desired_capacity
        self.__instances = ec2_instances
        self.__timestamp = datetime.datetime.now()

    @property
    def desired_capacity(self):
        return self.__desired_capacity

    @property
    def ec2_instances(self):
        return self.__instances

    @property
    def timestamp(self):
        return self.__timestamp


class _Watcher:
    def __init__(self, log):
        self.__log = log
        self._last_record = None
        self._stable_start_time = None

    def _if_reset_stable_timer(self, desired_capacity, ec2_instances):
        raise Exception("not implemented")

    def watch(self, desired_capacity, ec2_instances):
        if self._last_record is None:
            self._last_record = _WatchRecord(desired_capacity, ec2_instances)
            self._stable_start_time = self._last_record.timestamp
            return

        if self._if_reset_stable_timer(desired_capacity, ec2_instances):
            self._stable_start_time = datetime.datetime.now()
            self.__log.info("reset stable start time to {}".format(self._stable_start_time))
        else:
            now = datetime.datetime.now(tz=self._stable_start_time.tzinfo)
            self.__log.info("keep stable start time {}, stable duration {}s".format(
                self._stable_start_time, (now - self._stable_start_time).seconds))

        self.__log.debug("last watch record updated")
        self._last_record = _WatchRecord(desired_capacity, ec2_instances)

    def is_stable_enough(self, duration):
        if self._last_record is None:
            return False

        now = datetime.datetime.now(tz=self._stable_start_time.tzinfo)
        stable_time_seconds = (now - self._stable_start_time).seconds
        return stable_time_seconds > duration


class MakeUpStableEnoughWatcher(_Watcher):
    def __init__(self, log):
        super().__init__(log)

    def _if_reset_stable_timer(self, desired_capacity, ec2_instances):
        if desired_capacity != self._last_record.desired_capacity:
            return True

        return len(ec2_instances) > len(self._last_record.ec2_instances)


class MakeDownStableEnoughWatcher(_Watcher):
    def __init__(self, log):
        super().__init__(log)

    def _if_reset_stable_timer(self, desired_capacity, ec2_instances):
        if desired_capacity != self._last_record.desired_capacity:
            return True

        return len(ec2_instances) < len(self._last_record.ec2_instances)
