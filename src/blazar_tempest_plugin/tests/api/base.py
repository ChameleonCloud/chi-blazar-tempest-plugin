# tempest.lib.*
# tempest.config
# tempest.test_discover.plugins
# tempest.common.credentials_factory
# tempest.clients
# tempest.test
# tempest.scenario.manager


from oslo_log import log as logging
from tempest import config, test
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from tempest.lib.common.utils import data_utils, test_utils

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
