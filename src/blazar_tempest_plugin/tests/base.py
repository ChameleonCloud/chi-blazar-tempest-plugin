import datetime

from oslo_log import log as logging
from tempest import config, test
from tempest.lib import exceptions
from tempest.lib.common.utils import data_utils, test_utils

LOG = logging.getLogger(__name__)
CONF = config.CONF


class LeaseErrorException(exceptions.TempestException):
    message = "Lease %(lease_id)s failed to start and is in ERROR status"


class ReservationAPITest(test.BaseTestCase):
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

    def create_lease(self, body: dict = {}):
        """Wrapper around blazar.create_lease with sane defaults."""

        # Generate a unique lease name for potential debugging
        body.setdefault(
            "name",
            data_utils.rand_name(
                prefix=CONF.resource_name_prefix,
                name=self.__class__.__name__ + "-lease",
            ),
        )

        # set start and end date well in the future, to avoid any possible conflicts
        body.setdefault("start_date", "2050-12-26 12:00")
        body.setdefault("end_date", "2050-12-27 12:00")

        # actually create the lease, ignoring the request status code
        _, resp_body = self.reservation_client.create_lease(body)

        lease = resp_body["lease"]

        # automatically clean the lease up, and don't fail if we happen to clean it up earlier
        self.addClassResourceCleanup(
            test_utils.call_and_ignore_notfound_exc,
            self.reservation_client.delete_lease,
            lease["id"],
        )

        # return the lease as a dict
        return lease

    def get_lease_args_from_duraton(self, hours):
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

    def get_lease_now(self, hours, reservations):
        """Create a lease starting now, lasting for for #hours, for reservations in the reservations array."""

        # get start and end dates for the lease, will be passed as kwargs
        lease_body = self.get_lease_args_from_duraton(hours=hours)
        lease_body["reservations"] = reservations

        lease = self.create_lease(lease_body)
        return lease
