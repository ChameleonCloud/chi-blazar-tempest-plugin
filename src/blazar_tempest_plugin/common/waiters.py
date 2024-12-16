"""Module of ways for a resource to reach a status."""

import time

from blazar_tempest_plugin.common import exceptions as blazar_exceptions


def wait_for_lease_status(leases_client, lease_id, status):
    if isinstance(status, str):
        terminal_status = [status]
    else:
        terminal_status = status

    start = int(time.time())
    while int(time.time()) - start < leases_client.build_timeout:
        lease_body = leases_client.show_lease(lease_id)
        lease = lease_body["lease"]
        current_status = lease["status"]
        if current_status in terminal_status:
            return lease
        if current_status in ["ERROR"]:
            raise blazar_exceptions.LeaseErrorException(lease_id)

        time.sleep(leases_client.build_interval)
