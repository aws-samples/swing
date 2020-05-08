class StableEnoughEvent:
    def __init__(self, spot_asg_desired_capacity, spot_asg_instance_count):
        self.spot_asg_desired_capacity = spot_asg_desired_capacity
        self.spot_asg_instance_count = spot_asg_instance_count

    def is_none(self):
        return False

    def validate(self, spot_asg_desired_capacity, spot_asg_instance_count):
        return (self.spot_asg_desired_capacity == spot_asg_desired_capacity and
                self.spot_asg_instance_count == spot_asg_instance_count)


class _NoneStableEnoughEvent(StableEnoughEvent):
    def __init__(self):
        super(_NoneStableEnoughEvent, self).__init__(-1, -1)

    def is_none(self):
        return True

    def validate(self, spot_asg_desired_capacity, spot_asg_instance_count):
        raise Exception("not supported")


NoneStableEnoughEvent = _NoneStableEnoughEvent()
