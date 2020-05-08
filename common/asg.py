def get_asg(stop_flag, log, aws_session, asg_name):
    client = aws_session.client("autoscaling")
    asgs = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[asg_name],
        MaxRecords=1
    )

    if "AutoScalingGroups" not in asgs:
        raise Exception("invalid autoscaling group describe_auto_scaling_groups response")
    elif len(asgs["AutoScalingGroups"]) < 1:
        raise Exception("the autoscaling group '{}' does not exist".format(asg_name))

    return asgs["AutoScalingGroups"][0]


def set_asg_desired_capacity(stop_flag, log, aws_session, asg_name, old_desired_capacity, new_desired_capacity):
    client = aws_session.client("autoscaling")
    response = client.set_desired_capacity(
        AutoScalingGroupName=asg_name,
        DesiredCapacity=new_desired_capacity,
        HonorCooldown=False
    )

    if "ResponseMetadata" not in response:
        raise Exception("invalid autoscaling group set_desired_capacity response")
    elif response["ResponseMetadata"]["HTTPStatusCode"] != 200:
        raise Exception("failed to update desired capacity from {} to {} on the autoscaling group '{}'".format(
            old_desired_capacity, new_desired_capacity, asg_name))


def get_asg_counts_instances(stop_flag, log, aws_session, asg_name, logging=False):
    asg = get_asg(stop_flag, log, aws_session, asg_name)
    asg_desired_capacity = asg["DesiredCapacity"]

    asg_instance_count = len(asg["Instances"])
    if logging:
        log.info("the autoscaling group '{}': MinSize={}, MaxSize={}, DesiredCapacity={}, InstancesCount={}".
                 format(asg_name, asg["MinSize"], asg["MaxSize"], asg_desired_capacity, asg_instance_count))

    return asg_desired_capacity, asg_instance_count, asg["Instances"]


def up_asg_desired_capacity(stop_flag, log, aws_session, asg_name, plus_count):
    try:
        asg = get_asg(stop_flag, log, aws_session, asg_name)
    except Exception as e:
        log.error("failed to describe autoscaling group '{}', skip make up the desired capacity: {}".format(
            asg_name, str(e)))
        raise e

    new_desired_capacity = asg["DesiredCapacity"] + plus_count

    if new_desired_capacity > asg["MaxSize"]:
        log.warn("cannot to make up {} instance(s) to the autoscaling group '{}' from {}, "
                 "due to the new desired capacity {} is greater than the max size {}, "
                 "you might need to increase the max size of it".
                 format(plus_count, asg_name, asg["DesiredCapacity"], new_desired_capacity, asg["MaxSize"]))
        new_desired_capacity = asg["MaxSize"]
        plus_count = new_desired_capacity - asg["DesiredCapacity"]

    if plus_count == 0:
        return

    set_asg_desired_capacity(stop_flag, log, aws_session, asg_name, asg["DesiredCapacity"], new_desired_capacity)

    log.info("the desired capacity of the autoscaling group '{}' has been updated to {}, {} instances made up".format(
        asg_name, new_desired_capacity, plus_count))


def down_asg_desired_capacity(stop_flag, log, aws_session, asg_name, minus_count):
    try:
        asg = get_asg(stop_flag, log, aws_session, asg_name)
    except Exception as e:
        log.error("failed to describe autoscaling group '{}', skip make up the desired capacity: {}".format(
            asg_name, str(e)))
        raise e

    new_desired_capacity = asg["DesiredCapacity"] - minus_count

    if new_desired_capacity < asg["MinSize"]:
        log.warn("cannot to make down {} instance(s) to the autoscaling group '{}' from {}, "
                 "due to the new desired capacity {} is less than the min size {}, "
                 "you might need to decrease the min size of it".
                 format(minus_count, asg_name, asg["DesiredCapacity"], new_desired_capacity, asg["MinSize"]))
        new_desired_capacity = asg["MinSize"]
        minus_count = asg["DesiredCapacity"] - new_desired_capacity

        if minus_count == 0:
            return

    set_asg_desired_capacity(stop_flag, log, aws_session, asg_name, asg["DesiredCapacity"], new_desired_capacity)

    log.info("the desired capacity of the autoscaling group '{}' has been updated to {}, {} instances made down".format(
        asg_name, new_desired_capacity, minus_count))
