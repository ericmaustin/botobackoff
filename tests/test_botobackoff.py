import boto3

from botocore.stub import Stubber
from botocore.exceptions import ClientError

from botobackoff import BotoBackoff, botobackoff


def test__botobackoff_no_error():
    client = boto3.client("s3")
    stubber = Stubber(client)
    stubber.add_response("list_buckets", {"Buckets": []})
    stubber.activate()

    client_with_backoff = BotoBackoff(client)
    response = client_with_backoff.list_buckets()
    assert response == {"Buckets": []}


def test__botobackoff_retry_once():
    count = 0

    @botobackoff(max_retries=1)
    def retry_once():
        nonlocal count
        count += 1
        if count < 2:
            raise ClientError(
                operation_name="list_buckets",
                error_response={
                    "Error": {"Code": "RequestLimitExceeded", "Message": "The specified bucket does not exist"}}
            )
        return {"Buckets": []}

    retry_once()
    assert(count == 2)


def test_botobackoff_ignore_errors():
    # test the decorator
    @botobackoff(ignore_error_codes=["RequestLimitExceeded"])
    def ignore_error():
        raise ClientError(
            operation_name="list_buckets",
            error_response={
                "Error": {"Code": "RequestLimitExceeded", "Message": "The specified bucket does not exist"}}
        )

    assert ignore_error() is None
    client = boto3.client("s3")
    stubber = Stubber(client)
    stubber.add_client_error("list_buckets", "RequestLimitExceeded")
    stubber.activate()

    # test the class
    client_with_backoff = BotoBackoff(client, ignore_error_codes=["RequestLimitExceeded"])
    response = client_with_backoff.list_buckets()
    assert response is None


def test__unhandled_error():
    count = 0

    @botobackoff(max_retries=1)
    def retry_once():
        nonlocal count
        count += 1
        if count < 2:
            raise ClientError(
                operation_name="list_buckets",
                error_response={
                    "Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
            )
        return {"Buckets": []}

    try:
        retry_once()
    except ClientError as e:
        assert e.response["Error"]["Code"] == "AccessDenied"

    assert(count == 1)

    client = boto3.client("s3")
    stubber = Stubber(client)
    stubber.add_client_error("list_buckets", "AccessDenied")
    stubber.activate()

    client_with_backoff = BotoBackoff(client, ignore_error_codes=["RequestLimitExceeded"])

    try:
        client_with_backoff.list_buckets()
    except ClientError as e:
        assert e.response["Error"]["Code"] == "AccessDenied"

