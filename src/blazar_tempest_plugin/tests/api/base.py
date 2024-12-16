from oslo_log import log as logging
from tempest import config, test
from tempest.lib.common.utils import data_utils, test_utils

from blazar_tempest_plugin.common import utils

CONF = config.CONF
LOG = logging.getLogger(__name__)


class ReservationApiTest(test.BaseTestCase):
    credentials = ["primary"]

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
    def create_test_lease(cls, lease_name=None, **kwargs):
        """Create a test lease with sane defaults for name and dates.
        Lease will be in the far future to ensure no conflicts."""

        if not lease_name:
            lease_name = data_utils.rand_name(
                prefix=CONF.resource_name_prefix,
                name=__name__ + "-lease",
            )

        kwargs.setdefault("name", lease_name)
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
    def get_resource_name(cls, prefix):
        return data_utils.rand_name(
            prefix=CONF.resource_name_prefix,
            name=cls.__name__ + prefix,
        )
