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


class BaseReservationTest(test.BaseTestCase):
    credentials = ["primary"]

    @classmethod
    def skip_checks(cls):
        super().skip_checks()

        if not CONF.service_available.blazar:
            raise cls.skipException("blazar is not enabled.")

    @classmethod
    def setup_credentials(cls):
        return super().setup_credentials()

    @classmethod
    def resource_setup(cls):
        super().resource_setup()
        cls.created_leases = []

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_primary.reservation.ReservationClient()

    @classmethod
    def create_lease(cls, body: dict = {}):
        """Wrapper that returns a test lease."""

        body.setdefault(
            "name",
            data_utils.rand_name(
                prefix=CONF.resource_name_prefix, name=cls.__name__ + "-lease"
            ),
        )
        body.setdefault("start_date", "2050-12-26 12:00")
        body.setdefault("end_date", "2050-12-27 12:00")

        _, resp_body = cls.client.create_lease(body)

        lease = resp_body["lease"]

        cls.created_leases.append(lease["id"])
        cls.addClassResourceCleanup(
            test_utils.call_and_ignore_notfound_exc,
            cls.client.delete_lease,
            lease["id"],
        )

    @classmethod
    def get_1h_lease_args(cls):
        current_time = datetime.datetime.now(datetime.timezone.utc)
        end_time = current_time + datetime.timedelta(hours=1)
        return {
            "start_date": "now",
            "end_date": end_time.strftime("%Y-%m-%d %H:%M"),
        }

    def wait_for_lease_status(self, lease_id, status):
        client = self.client

        if isinstance(status, str):
            terminal_status = [status]
        else:
            terminal_status = status

        current_status = "An unknown status"
        start = int(time.time())
        while int(time.time()) - start < client.build_timeout:
            _, lease_body = client.get_lease(lease_id)
            lease = lease_body["lease"]
            current_status = lease["status"]
            if current_status in terminal_status:
                return current_status
            if current_status in ["ERROR"]:
                raise LeaseErrorException(lease_id)

            time.sleep(client.build_interval)
