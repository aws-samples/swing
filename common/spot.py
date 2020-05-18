# THIS FILE IS USELESS UNDER CURRENT IMPLEMENT, BACKUP PURPOSE ONLY

import datetime

# spot instance request will under "open" state when holding happens
# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-bid-status.html
__holding_status_codes = [
    "capacity-not-available",
    "price-too-low",
    "not-scheduled-yet",
    "launch-group-constraint",
    "az-group-constraint",
    "placement-group-constraint",
    "constraint-not-fulfillable",
]


def spot_requests(stop_flag, log, aws_session, image_id, spot_sg_id,
                  spot_request_state, spot_request_status_list):
    ec2 = aws_session.client("ec2")
    paginator = ec2.get_paginator('describe_spot_instance_requests')

    filters = [
        {
            "Name": "launch.image-id",
            "Values": [
                image_id,
            ]
        },
        {
            "Name": "launch.group-id",
            "Values": [
                spot_sg_id,
            ]
        },
        {
            "Name": "state",
            "Values": [
                spot_request_state,
            ]
        },
        {
            "Name": "status-code",
            "Values": spot_request_status_list,
        },
        {
            "Name": "type",  # ASG leverage one-time spot instance
            "Values": [
                "one-time",
            ]
        },
    ]

    config = {
        'MaxItems': 1000,  # FIXME(zhiyan): seems like 1000 is enough
        'PageSize': 1000,
    }

    page_iter = paginator.paginate(Filters=filters, PaginationConfig=config)

    result = []
    for page in page_iter:
        if "SpotInstanceRequests" not in page:
            log.error("invalid spot instance requests description response, skip: {}".format(page))
            raise Exception("invalid spot instance requests describe_spot_instance_requests response")
        elif len(page["SpotInstanceRequests"]) < 1:
            log.debug("not found any spot instance request with image id '{}' and security group id '{}' "
                      "under state '{}' and status in ['{}']".
                      format(image_id, spot_sg_id, spot_request_state, "', '".join(spot_request_status_list)))
        result += page["SpotInstanceRequests"]

    return result


def spot_request_hold_count(stop_flag, log, aws_session, image_id, spot_sg_id, wait_seconds):
    requests = spot_requests(stop_flag, log, aws_session, image_id, spot_sg_id, "open", __holding_status_codes)

    log.info("found {} spot instance request(s) under state 'open' and hold status".format(len(requests)))
    log.debug(requests)

    count = 0
    for request in requests:
        hold_start_time = request["Status"]["UpdateTime"]
        # hold_start_time = request["CreateTime"]
        hold_time_seconds = datetime.datetime.now(tz=hold_start_time.tzinfo) - hold_start_time

        log.debug("spot instance request '{}' is under hold status in {}s".format(
            request["SpotInstanceRequestId"], hold_time_seconds.seconds))

        if hold_time_seconds.seconds > wait_seconds:
            log.info("found an on-hold spot instance request, request: '{}', hold duration: {}s".
                     format(request["SpotInstanceRequestId"], hold_time_seconds.seconds))
            count += 1

    return count
