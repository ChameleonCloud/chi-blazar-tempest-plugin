import re
import time

from datetime import datetime, timedelta, timezone
from typing import Optional

from tempest import config

CONF = config.CONF


def time_offset_to_blazar_string(time_now: Optional[datetime] = None, **kwargs) -> str:
    """Specify offset from now (or time_now), and return blazar formatted string representation."""

    if not time_now:
        time_now = datetime.now(timezone.utc)

    time_offset = time_now + timedelta(**kwargs)
    return time_offset.strftime("%Y-%m-%d %H:%M")


def get_server_floating_ip(server):
    """Utility function to get the floating IP from a server."""

    addresses = server.get("addresses", {})
    for network_name, addr_list in addresses.items():
        for addr in addr_list:
            if addr.get("OS-EXT-IPS:type") == "floating":
                return addr.get("addr")
    return None


def wait_for_remote_file(remote, path, timeout=30, interval=1):
    """Wait for a file to exist on a remote system via SSH."""

    start = time.time()
    while time.time() - start < timeout:
        output = remote.exec_command(f'test -f {path} && echo FOUND || echo MISSING')
        if "FOUND" in output:
            return True
        time.sleep(interval)
    return False


def should_skip(check_name, check_regex):
    """
    Check if a test should be skipped based on the configuration.

    For example, on KVM we want to skip 2 tests:
    cc_image_tests_skip_test_regex = verify_rclone_and_object_store|verify_openrc
    """
    if check_regex and re.fullmatch(check_regex, check_name):
        return True

    return False


# def _get_time_now() -> datetime:
#     time_now = datetime.now(timezone.utc)
#     return time_now


# def _blazar_time_req_from_output(cls, iso8601_timestring: str):
#     """Convert openstack standard datetime string to blazar request format."""
#     result = datetime.fromisoformat(iso8601_timestring)
#     output_string = result.strftime("%Y-%m-%d %H:%M")
#     return output_string


# def _blazar_time_req_to_iso8601(cls, date_string: str):
#     parsed_datetime = datetime.strptime(date_string, "%Y-%m-%d %H:%M")
#     return parsed_datetime.isoformat(timespec="microseconds")
