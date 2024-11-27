from oslo_log import log as logging
from tempest import config, test

LOG = logging.getLogger(__name__)
CONF = config.CONF


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
    def setup_clients(cls):
        super().setup_clients()
        cls.client = cls.os_primary.reservation.ReservationClient()

    def setUp(self):
        return super().setUp()
