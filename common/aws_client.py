import boto3


def new_session(option=None):
    return boto3.session.Session()
