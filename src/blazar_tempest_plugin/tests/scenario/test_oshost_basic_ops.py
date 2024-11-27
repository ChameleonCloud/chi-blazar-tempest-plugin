from oslo_log import log as logging
from tempest import config
from tempest.lib.common.utils import data_utils, test_utils
from tempest.scenario import manager

from blazar_tempest_plugin.tests.scenario.base import BlazarScenarioTest

CONF = config.CONF
LOG = logging.getLogger(__name__)


class TestOshostBasicOps(BlazarScenarioTest):
    """Test suite for basic operations involving a lease and a baremetal node.

    * Create a lease for a baremetal node
    * wait for lease to become active
    * launch an instance using the lease
    * perform ssh to the instance
    """

    def setUp(self):
        super().setUp()
        self.run_ssh = CONF.validation.run_validation
        self.ssh_user = CONF.validation.image_ssh_user

    @classmethod
    def resource_setup(cls):
        super().resource_setup()

        lease_body = cls.get_1h_lease_args()
        lease_body["reservations"] = [
            {
                "min": "1",
                "max": "1",
                "resource_type": "physical:host",
                "hypervisor_properties": "",
                "resource_properties": "",
            }
        ]
        cls.create_lease(lease_body)

    def test_oshost_basic_ops(self):
        lease_id = self.created_leases[0]

        self.wait_for_lease_status(lease_id, "ACTIVE")
        LOG.info("lease %s started", lease_id)

        resp, body = self.client.get_lease(lease_id)
        lease = body["lease"]

        reservations = lease["reservations"]

        # response may contain multiple reservations, of variety of types. We need just hosts here.
        oshost_res_ids = [
            res["id"] for res in reservations if res["resource_type"] == "physical:host"
        ]
        reservation_id = oshost_res_ids[0]

        self.create_server(
            wait_until="SSHABLE",
            scheduler_hints={"reservation": reservation_id},
            image_id=CONF.compute.image_ref,
        )
