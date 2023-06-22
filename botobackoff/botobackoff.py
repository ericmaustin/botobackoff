from __future__ import annotations, absolute_import

import boto3
import time
import random

from functools import wraps
from boto3.session import Session
from typing import Optional, Union
from botocore.exceptions import ClientError
from botocore.client import BaseClient

DEFAULT_RETRY_ERROR_CODES = [
    "ThrottlingException",
    "TooManyRequestsException",
    "ServiceUnavailableException",
    "RequestLimitExceeded",
    "RequestThrottled",
    "RequestThrottledException",
    "ProvisionedThroughputExceededException",
    "LimitExceededException",
    "EndpointConnectionError",
    "ConnectTimeoutError",
    "Unavailable",
    "InternalFailure",
    "InternalError",
]


class BotoBackoff:
    def __init__(
            self,
            client: Union[str, BaseClient] = None,
            *,
            interval_seconds=0.2,
            max_retries=3,
            backoff_rate=2,
            jitter=0.5,
            max_retries_before_backoff=0,
            added_error_codes: list = None,
            ignore_error_codes: list = None,
            boto_session: Session = None,
    ):
        """
        :param client: the boto3 client to wrap or the service name to create a client for
        :param interval_seconds: the initial number of seconds to wait between retries
        :param max_retries: the maximum number of retries to attempt
        :param backoff_rate: the rate at which the interval increases
        :param jitter: the amount of jitter to add to the interval
        :param max_retries_before_backoff: maximum number of retries before applying backoff
        :param added_error_codes: additional error codes to retry on
        :param ignore_error_codes: error codes to ignore, and return `None` for
        :param boto_session: the boto3 session to use. If not provided, the default session will be used.
            Ignored if a client is provided.
        """
        _boto_client = client

        if isinstance(client, str):
            # if we weren't provided a verbose client, create one
            # use the session if provided, otherwise use default session
            _boto_client = boto_session.client(client) \
                if boto_session \
                else boto3.client(client)

        self._client: BaseClient = _boto_client

        # if no backoff error codes are provided, use the default list
        self._added_backoff_error_codes = added_error_codes or []
        self._ignore_errors = ignore_error_codes or []
        self._backoff_rate = backoff_rate
        self._interval_seconds = interval_seconds
        self._max_retries = max_retries
        self._jitter = jitter
        self._max_retries_before_backoff = max_retries_before_backoff

    def with_options(
            self,
            *,
            interval_seconds=None,
            max_retries=None,
            backoff_rate=None,
            jitter=None,
            max_retries_before_backoff=None,
            ignore_error_codes: list = None,
            added_error_codes: list = None,
    ):
        """
        get a child BotoErrorHandler with the same boto session and client but different options
        :return: a new `BotoErrorHandler`
        """
        return BotoBackoff(
            self._client,
            interval_seconds=interval_seconds or self._interval_seconds,
            max_retries=max_retries or self._max_retries,
            backoff_rate=backoff_rate or self._backoff_rate,
            jitter=jitter or self._jitter,
            max_retries_before_backoff=max_retries_before_backoff or self._max_retries_before_backoff,
            ignore_error_codes=ignore_error_codes or self._ignore_errors,
            added_error_codes=added_error_codes or self._added_backoff_error_codes,
        )

    def __getattr__(self, item):
        """
        :return: a Callable wrapper for the underlying account and:
            automatically add the account id
            allows for missing_ok kwarg to return None instead of raising an exception
        """
        fn = getattr(self._client, item)
        if not callable(fn):
            return fn

        # add the backoff decorator to the function
        @botobackoff(
            interval_seconds=self._interval_seconds,
            max_retries=self._max_retries,
            backoff_rate=self._backoff_rate,
            jitter=self._jitter,
            max_retries_before_backoff=self._max_retries_before_backoff,
            added_error_codes=self._added_backoff_error_codes,
            ignore_error_codes=self._ignore_errors,
        )
        def call(**api_kwargs) -> Optional[any]:
            return fn(**api_kwargs)

        return call

    def __enter__(self):
        """
        allow context manager usage
        useful when using with_options() method
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """ allow context manager usage """
        pass


def botobackoff(
        *,
        interval_seconds=0.2,
        max_retries=3,
        backoff_rate=2,
        jitter=0.5,
        max_retries_before_backoff=0,
        ignore_error_codes: list = None,
        added_error_codes: list = None,
):
    """
    retry a function call on boto3 client errors
    :param interval_seconds: the initial interval between retries
    :param max_retries: the maximum number of retries
    :param backoff_rate: the rate at which the interval increases
    :param jitter:  the amount of jitter to add to the interval
    :param max_retries_before_backoff: the number of retries before applying backoff logic
    :param ignore_error_codes: list of error codes to ignore
    :param added_error_codes: list of error codes to retry on in addition to the default list
    :return: decorated function
    """
    def deco(f):
        retry_on = added_error_codes or []
        retry_on.extend(DEFAULT_RETRY_ERROR_CODES)
        ignore_on = ignore_error_codes or []

        @wraps(f)
        def retry_func(*args, **kwargs):
            _attempts = 0
            while True:
                # keep looping until we get a response, or we hit max retries
                try:
                    return f(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code in ignore_on:
                        # if error is an ignored error code just return None
                        return None
                    if error_code in retry_on and not _attempts > max_retries:
                        if _attempts > max_retries_before_backoff:
                            # apply backoff logic after the specified retries allowed before backing off
                            sleep_time = interval_seconds * backoff_rate ** \
                                         (_attempts - max_retries_before_backoff) * \
                                         (1 + random.uniform(-jitter, jitter))
                            time.sleep(sleep_time)
                        _attempts += 1
                    else:
                        # raise the original exception
                        raise e

        return retry_func

    return deco
