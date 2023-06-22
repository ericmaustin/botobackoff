# botobackoff

botobackoff provides a boto3 client wrapper and function decorator that automatically retries failed boto3 calls
with exponential backoff and jitter. 

The decorator and client wrapper include options to add additional error codes to catch and retry on and
error codes to ignore and fail silently returning `None`.


## Motivation

Boto3 provides limited retry functionality for failed calls. I wanted to create a simple way to retry boto3 calls
with exponential backoff and jitter as well as more flexibility as to what errors can be retried or ignored without
needing to add additional try/except blocks around boto3 calls.

## Installation
install from PyPI: `pip install botobackoff`

## Usage

Example with the client wrapper:

```python
from botobackoff import BotoBackoff

import boto3

wrapped_client = BotoBackoff(
    boto3.client("s3"),
    max_retries=5,
)

print(wrapped_client.list_objects(Bucket="my-bucket"))
```

Example with the decorator:
```python
from botobackoff import botobackoff

import boto3

@botobackoff(max_retries=5)
def list_objects():
    return boto3.client("s3").list_objects(Bucket="my-bucket")

print(list_objects())
```

The boto3 errors that are retried by default are:
- ThrottlingException
- TooManyRequestsException
- ServiceUnavailableException
- RequestLimitExceeded
- RequestThrottled
- RequestThrottledException
- ProvisionedThroughputExceededException
- LimitExceededException
- EndpointConnectionError
- ConnectTimeoutError
- Unavailable
- InternalFailure
- InternalError

to add additional errors to retry on use the `added_error_codes` parameter:
```python
from botobackoff import botobackoff

import boto3

@botobackoff(added_error_codes=["NoSuchBucket"])
def list_objects():
    return boto3.client("s3").list_objects(Bucket="my-bucket")
```