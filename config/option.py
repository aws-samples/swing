import argparse
import sys

import common
import common.asg


class _MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n\n" % message)
        self.print_help()
        sys.exit(2)


class _Option(argparse.Namespace):
    def __init__(self, stop_flag, log, aws_session, **kwargs):
        super().__init__(**kwargs)
        self.__stop_flag = stop_flag
        self.__log = log
        self.__session = aws_session

        self.__spot_asg_name = None
        self.__ondemand_asg_name = None
        self.__interval = 0
        self.__run_once = False

        self.__ec2 = aws_session.resource("ec2")
        self.__asg = aws_session.client("autoscaling")

    @property
    def spot_asg_name(self):
        return self.__spot_asg_name

    @spot_asg_name.setter
    def spot_asg_name(self, spot_asg_name):
        common.asg.get_asg(self.__stop_flag, self.__log, self.__session, spot_asg_name)
        self.__spot_asg_name = spot_asg_name

    @property
    def ondemand_asg_name(self):
        return self.__ondemand_asg_name

    @ondemand_asg_name.setter
    def ondemand_asg_name(self, ondemand_asg_name):
        common.asg.get_asg(self.__stop_flag, self.__log, self.__session, ondemand_asg_name)
        self.__ondemand_asg_name = ondemand_asg_name

    @property
    def interval(self):
        if self.__run_once:
            return self.wait_time
        else:
            return self.__interval

    @interval.setter
    def interval(self, interval):
        if 0 == interval:
            self.__run_once = True
        self.__interval = interval

    @property
    def run_once(self):
        return self.__run_once


def _ratio_argument_type(str_arg):
    ratio = float(str_arg)
    if ratio > 0 or ratio <= 1:
        return ratio
    else:
        msg = "%r is not a valid ratio, data range is (0, 1]" % str_arg
        raise argparse.ArgumentTypeError(msg)


def _second_argument_type(str_arg):
    second = int(str_arg)
    if second >= 0:
        return second
    else:
        msg = "%r is not a valid second, data range is [0, +inf)" % str_arg
        raise argparse.ArgumentTypeError(msg)


def prepare_args(stop_flag, aws_session):
    log = common.logger("option")

    parser = _MyParser(description="Make up and down AWS EC2 instance between "
                                   "Spot and On-Demand two AutoScaling groups.",
                       prog="swing.py",
                       epilog="Failover the un-fulfilled Spot instance by On-Demand instance, "
                              "to balance cost and availability for your EC2 instance fleet.")
    parser.add_argument("-v", "--version", action="version", version="%(prog)s 0.1")

    # required options
    required_group = parser.add_argument_group('required arguments')

    # option "spot-asg-name" indicates the spot autoscaling group for checking if need to make up
    required_group.add_argument("-s", "--spot-asg-name", required=True,
                                help="the Spot AutoScaling group name")
    # option "ondemand-asg-name" indicates the on-demand autoscaling group for executing make up and down
    required_group.add_argument("-o", "--ondemand-asg-name", required=True,
                                help="the On-Demand AutoScaling group name")

    parser.add_argument("-b", "--max-shortage-ratio", required=False, type=_ratio_argument_type, default=0,
                        help="the maximum ratio of un-fulfilled Spot instance in the "
                             "desired capability of the Spot AutoScaling group. It will be used to "
                             "calculate the lowest acceptable capacity of your EC2 instance fleet for "
                             "provision or de-provision On-Demand instance. "
                             "The default value is 0 (do not tolerate any bias on the desired capacity)")
    parser.add_argument("-w", "--wait-time", required=False, type=_second_argument_type, default=180,
                        help="the time in second to wait the Spot or On-Demand instance to be fulfilled or "
                             "stopped before to fix the bias by provisioning or de-provisioning On-Demand instance. "
                             "The default value is 180 (3 minutes)")
    parser.add_argument("-i", "--interval", required=False, type=_second_argument_type, default=60,
                        help="the time in second between each check and each step of bias fixing by "
                             "provisioning or de-provisioning On-Demand instance if needed. "
                             "The default value is 60 (1 minute). "
                             "Value zero means do that only once")
    parser.add_argument("-t", "--step-ratio", required=False, type=_ratio_argument_type, default=1,
                        help="the ratio of number of increased or decreased On-Demand instance about the "
                             "total bias in each time. The default value is 1 "
                             "(to fix 100%% bias in once time)")

    try:
        return parser.parse_args(namespace=_Option(stop_flag, log, aws_session))
    except Exception as e:
        parser.error(str(e))
