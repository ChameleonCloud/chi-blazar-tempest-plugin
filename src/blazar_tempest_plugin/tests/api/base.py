import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from oslo_log import log as logging
from tempest import config, test
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from tempest.lib.common.utils import data_utils, test_utils

CONF = config.CONF
LOG = logging.getLogger(__name__)


class LeaseErrorException(lib_exc.TempestException):
    message = "Lease %(lease_id)s failed to start and is in ERROR status"


class ReservationApiTest(test.BaseTestCase):
    credentials = ["primary"]

    @classmethod
    def _get_name_prefix(cls, prefix):
        return data_utils.rand_name(
            prefix=CONF.resource_name_prefix,
            name=cls.__name__ + prefix,
        )

    @classmethod
    def skip_checks(cls):
        super(ReservationApiTest, cls).skip_checks()
        if not CONF.service_available.blazar:
            skip_msg = "Blazar is disabled"
            raise cls.skipException(skip_msg)

    @classmethod
    def setup_credentials(cls):
        cls.set_network_resources()
        super(ReservationApiTest, cls).setup_credentials()

    @classmethod
    def setup_clients(cls):
        super(ReservationApiTest, cls).setup_clients()
        cls.leases_client = cls.os_primary.reservation.LeasesClient()

    @classmethod
    def create_test_lease(cls, **kwargs):
        """Create a test lease with sane defaults for name and dates.
        Lease will be in the far future to ensure no conflicts."""

        kwargs.setdefault("name", cls._get_name_prefix("-lease"))
        kwargs.setdefault("start_date", "2050-12-26 12:00")
        kwargs.setdefault("end_date", "2050-12-27 12:00")

        lease_body = cls.leases_client.create_lease(**kwargs)

        lease = lease_body["lease"]

        cls.addClassResourceCleanup(
            test_utils.call_and_ignore_notfound_exc,
            cls.leases_client.delete_lease,
            lease["id"],
        )

        return lease

    @classmethod
    def _get_time_now(cls) -> datetime:
        time_now = datetime.now(timezone.utc)
        return time_now

    @classmethod
    def _get_blazar_time_offset(cls, time_now: Optional[datetime] = None, **kwargs):
        """Get timestamp with offset from `now` and format for blazar api."""

        if not time_now:
            time_now = cls._get_time_now()
        time_offset = time_now + timedelta(**kwargs)

        return time_offset.strftime("%Y-%m-%d %H:%M")

    @classmethod
    def _blazar_time_req_from_output(cls, iso8601_timestring: str):
        """Convert openstack standard datetime string to blazar request format."""
        result = datetime.fromisoformat(iso8601_timestring)
        output_string = result.strftime("%Y-%m-%d %H:%M")
        return output_string

    @classmethod
    def _blazar_time_req_to_iso8601(cls, date_string: str):
        parsed_datetime = datetime.strptime(date_string, "%Y-%m-%d %H:%M")
        return parsed_datetime.isoformat(timespec="microseconds")

    @classmethod
    def wait_for_lease_status(cls, lease_id, status):
        if isinstance(status, str):
            terminal_status = [status]
        else:
            terminal_status = status

        start = int(time.time())
        while int(time.time()) - start < cls.leases_client.build_timeout:
            lease_body = cls.leases_client.show_lease(lease_id)
            lease = lease_body["lease"]
            current_status = lease["status"]
            if current_status in terminal_status:
                return lease
            if current_status in ["ERROR"]:
                raise LeaseErrorException(lease_id)

            time.sleep(cls.leases_client.build_interval)
