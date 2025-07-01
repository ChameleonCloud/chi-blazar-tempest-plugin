import re
import subprocess
import time

from datetime import datetime, timedelta, timezone
from typing import Optional

from tempest import config
from tempest.lib import exceptions

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


def get_device_reservation_from_lease(lease):
        for res in lease["reservations"]:
            if res["resource_type"] == "device":
                return res["id"]


def wait_for_fip_on_container(
        container_client,
        floating_ips_client,
        container_uuid,
        expected_fip,
        timeout=60,
        interval=5
    ):
    """Poll until the container’s port shows the expected floating IP."""
    start = time.time()
    _, container = container_client.get_container(container_uuid)
    addrs = container.to_dict().get("addresses", {})
    _, entries = next(iter(addrs.items()))
    if not entries:
        raise ValueError(f"Container {container_uuid} has no addresses to check for floating IP.")

    port_id = entries[0].get("port")

    while time.time() - start < timeout:
        body = floating_ips_client.list_floatingips(port_id=port_id)
        for fip in body.get("floatingips", []):
            if fip.get("floating_ip_address") == expected_fip:
                return
        time.sleep(interval)

    raise exceptions.TimeoutException(
        f"Floating IP {expected_fip} did not appear on container "
        f"{container_uuid} within {timeout} seconds"
    )


def ping_ip(ip, timeout=60, sleep_interval=1):
    """Ping an IP address.

    Raise an exception if the ping fails within the timeout.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            subprocess.check_output(
                ["ping", "-c", "1", "-W", "1", ip]
            )
            return
        except subprocess.CalledProcessError:
            time.sleep(sleep_interval)
    raise exceptions.TimeoutException(f"Ping to {ip} failed after {timeout} seconds.")


def attach_floating_ip_to_container(
        container_client,
        floating_ips_client,
        container,
        fip_id
    ):
    """Attach a floating IP to a container."""
    _, container = container_client.get_container(container)
    addrs = container.to_dict().get("addresses", {})
    _, entries = next(iter(addrs.items()))
    if not entries:
        raise ValueError(f"Container {container['uuid']} has no addresses to attach floating IP.")

    port_id = entries[0].get("port")
    if not port_id:
        raise ValueError(f"Container {container['uuid']} has no port ID to attach floating IP.")

    return floating_ips_client.update_floatingip(fip_id, port_id=port_id)


def get_container_floating_ip(floating_ips_client, container):
    """Get the floating IP associated with a container."""
    entries = next(iter(container.to_dict().get("addresses", {}).values()))
    port_id = entries[0].get("port")

    body = floating_ips_client.list_floatingips(port_id=port_id)
    for fip in body.get("floatingips", []):
        return fip["floating_ip_address"]
    return None


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
