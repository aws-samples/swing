## What's swing

An operation tool can failover the un-fulfilled Spot instance by On-Demand instance, to balance cost
and availability for your EC2 instance fleet, by make up and down AWS EC2 instance between Spot and On-Demand two AutoScaling
groups.

```
usage: swing.py [-h] [-v] -s SPOT_ASG_NAME -o ONDEMAND_ASG_NAME
                [-b MAX_SHORTAGE_RATIO] [-w WAIT_TIME] [-i INTERVAL]
                [-t STEP_RATIO]

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
  -b MAX_SHORTAGE_RATIO, --max-shortage-ratio MAX_SHORTAGE_RATIO
                        the maximum ratio of un-fulfilled Spot instance in the
                        desired capability of the Spot AutoScaling group. It
                        will be used to calculate the lowest acceptable
                        capacity of your EC2 instance fleet for provision or
                        de-provision On-Demand instance. The default value is
                        0 (do not tolerate any bias on the desired capacity)
  -w WAIT_TIME, --wait-time WAIT_TIME
                        the time in second to wait the Spot or On-Demand
                        instance to be fulfilled or stopped before to fix the
                        bias by provisioning or de-provisioning On-Demand
                        instance. The default value is 180 (3 minutes)
  -i INTERVAL, --interval INTERVAL
                        the time in second between each check and each step of
                        bias fixing by provisioning or de-provisioning On-
                        Demand instance if needed. The default value is 60 (1
                        minute). Value zero means do that only once
  -t STEP_RATIO, --step-ratio STEP_RATIO
                        the ratio of number of increased or decreased On-
                        Demand instance about the total bias in each time. The
                        default value is 1 (to fix 100% bias in once time)

required arguments:
  -s SPOT_ASG_NAME, --spot-asg-name SPOT_ASG_NAME
                        the Spot AutoScaling group name
  -o ONDEMAND_ASG_NAME, --ondemand-asg-name ONDEMAND_ASG_NAME
                        the On-Demand AutoScaling group name
```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
