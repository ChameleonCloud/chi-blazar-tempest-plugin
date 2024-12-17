"""Module of ways for a resource to reach a status."""

import time

from oslo_log import log as logging
from tempest.lib import exceptions as lib_exc

from blazar_tempest_plugin.common import exceptions as blazar_exceptions

LOG = logging.getLogger(__name__)


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


def wait_for_lease_termination(client, lease_id, ignore_error=False):
    """Waits for lease to reach termination.

    This can happen either because the lease ended, and moved to status TERMINATED
    or if the lease was deleted before that.
    """
    try:
        body = client.show_lease(lease_id)["lease"]
    except lib_exc.NotFound:
        return
    old_status = body["status"]

    start_time = int(time.time())
    while True:
        time.sleep(client.build_interval)
        try:
            body = client.show_server(lease_id)["server"]
        except lib_exc.NotFound:
            return
        lease_status = body["status"]

        if lease_status != old_status:
            LOG.info(
                'State transition "%s" ==> "%s" after %d second wait',
                old_status,
                lease_status,
                time.time() - start_time,
            )
        if lease_status == "ERROR" and not ignore_error:
            details = "Lease %s failed to delete and is in ERROR status." % lease_id

            raise lib_exc.DeleteErrorException(details, lease_id=lease_id)

        if int(time.time()) - start_time >= client.build_timeout:
            raise lib_exc.TimeoutException
        old_status = lease_status


def _wait_for_server_scheduling(client, server_id: str):
    """Wait for server to finish scheduling, but not active."""

    body = client.show_server(server_id)["server"]
    # store previous state for logging
    old_status = server_status = body.get("status")
    old_task = server_task = body.get("OS-EXT-STS:task_state")
    start_time = int(time.time())
    timeout = client.build_timeout

    while True:
        if server_status == "BUILD":
            if server_task == None:
                pass
            if server_task == "networking":
                pass
            if server_task == "spawning":
                return body

        time.sleep(client.build_interval)

        body = client.show_server(server_id)["server"]
        server_status = body.get("status")
        server_task = body.get("OS-EXT-STS:task_state")
        if (server_status != old_status) or (server_task != old_task):
            LOG.info(
                'State transition "%s" ==> "%s" after %d second wait',
                "/".join((old_status, str(old_task))),
                "/".join((server_status, str(server_task))),
                time.time() - start_time,
            )

        if server_status == "ERROR":
            return body
            # # Fault: {'code': 500, 'created': '2024-12-17T17:55:36Z', 'message': 'No valid host was found. '}.
            # kwargs = {}
            # details = ""
            # if "fault" in body:
            #     details += "Fault: %s." % body["fault"]
            #     kwargs["fault"] = body["fault"]
            # raise blazar_exceptions.BuildErrorException(
            #     details, server_id=server_id, **kwargs
            # )

        timed_out = int(time.time()) - start_time >= timeout
        if timed_out:
            raise lib_exc.TimeoutException()

        old_status = server_status
        old_task = server_task
