import json
from contextlib import contextmanager

try:
    from urlparse import parse_qs, urlparse
except ImportError:
    from urllib.parse import parse_qs, urlparse


def assert_urls_equivalent(actual, expected, assert_equal_fn):
    """
    Checks if the the two URLs are funcationally equivalent,
    forwarding to the provided assert_equal_fn if they are not
    """
    actual_path = actual.split("?")[0]
    expected_path = expected.split("?")[0]
    actual_params = parse_qs(urlparse(actual).query)
    expected_params = parse_qs(urlparse(expected).query)
    if actual_path != expected_path or actual_params != expected_params:
        assert_equal_fn(actual, expected)


def pretty_str(list_or_dict):
    """
    Returns a string for the provided list or dict
    that looks good when printed to the console
    """
    return json.dumps(list_or_dict, indent=2)
