import datetime
import time

from oslo_log import log as logging
from tempest import config, test
from tempest.lib import exceptions
from tempest.lib.common.utils import data_utils, test_utils

LOG = logging.getLogger(__name__)
CONF = config.CONF


class LeaseErrorException(exceptions.TempestException):
    message = "Lease %(lease_id)s failed to start and is in ERROR status"


class ReservationTestCase(test.BaseTestCase):
    """Base class for scenario tests focused on reservable resources."""

    credentials = ["primary"]

    @classmethod
    def skip_checks(cls):
        super().skip_checks()
        if not CONF.service_available.blazar:
            raise cls.skipException("blazar is not enabled.")

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.reservation_client = cls.os_primary.reservation.ReservationClient()

    @classmethod
    def create_lease(cls, body: dict = {}):
        """Wrapper around blazar.create_lease with sane defaults."""

        # Generate a unique lease name for potential debugging
        body.setdefault(
            "name",
            data_utils.rand_name(
                prefix=CONF.resource_name_prefix,
                name=cls.__name__ + "-lease",
            ),
        )

        # set start and end date well in the future, to avoid any possible conflicts
        body.setdefault("start_date", "2050-12-26 12:00")
        body.setdefault("end_date", "2050-12-27 12:00")

        # actually create the lease, ignoring the request status code
        _, resp_body = cls.reservation_client.create_lease(body)

        lease = resp_body["lease"]

        # automatically clean the lease up, and don't fail if we happen to clean it up earlier
        cls.addClassResourceCleanup(
            test_utils.call_and_ignore_notfound_exc,
            cls.reservation_client.delete_lease,
            lease["id"],
        )

        # return the lease as a dict
        return lease

    @classmethod
    def get_lease_args_from_duration(cls, hours):
        """Generate arguments for blazar lease create.

        returns a dict containing:
        `start_date`:`now`, to have the lease start immediately
        `end_date`: utc datetime of lease end date.
        """

        time_now = datetime.datetime.now(datetime.timezone.utc)
        end_time = time_now + datetime.timedelta(hours=hours)
        return {
            "start_date": "now",
            "end_date": end_time.strftime("%Y-%m-%d %H:%M"),
        }

    @classmethod
    def get_lease_now(cls, hours, reservations):
        """Create a lease starting now, lasting for for #hours, for reservations in the reservations array."""

        # get start and end dates for the lease, will be passed as kwargs
        lease_body = cls.get_lease_args_from_duration(hours=hours)
        lease_body["reservations"] = reservations

        lease = cls.create_lease(lease_body)
        return lease

    @classmethod
    def wait_for_lease_status(cls, lease_id, status):
        if isinstance(status, str):
            terminal_status = [status]
        else:
            terminal_status = status

        start = int(time.time())
        while int(time.time()) - start < cls.reservation_client.build_timeout:
            _, lease_body = cls.reservation_client.get_lease(lease_id)
            lease = lease_body["lease"]
            current_status = lease["status"]
            if current_status in terminal_status:
                return lease
            if current_status in ["ERROR"]:
                raise LeaseErrorException(lease_id)

            time.sleep(cls.reservation_client.build_interval)
