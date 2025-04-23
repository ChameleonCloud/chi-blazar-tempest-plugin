import json

from manila_tempest_tests.common import waiters as share_waiters
from manila_tempest_tests.tests.scenario.manager_share import ShareScenarioTest
from oslo_log import log as logging
from tempest import config
from tempest.lib import decorators
from tempest.lib.common.utils import data_utils, test_utils

from blazar_tempest_plugin.common import exceptions, utils, waiters
from blazar_tempest_plugin.tests.scenario.base import ReservationScenarioTest

CONF = config.CONF
LOG = logging.getLogger(__name__)


def pp(data):
    LOG.info(json.dumps(data, indent=2))


class SharedFilesystemTest(ReservationScenarioTest):
    """Basic existence test for blazar shared filesystem reservation.

    This smoke test case follows this basic set of operations:
    * Create share
    * Reserve host and storage network
      * Blazar will create network,subnet,router, and set access rules
    * Launch an instance
    * Perform ssh to instance
    * Mount share
    * Terminate the instance
    """

    @classmethod
    def skip_checks(cls):
        super(SharedFilesystemTest, cls).skip_checks()
        if not CONF.service_available.manila:
            raise cls.skipException("Manila support is required")

    @classmethod
    def setup_credentials(cls):
        # Create no network resources for these tests.
        cls.set_network_resources()
        super().setup_credentials()

    @classmethod
    def setup_clients(cls):
        super().setup_clients()

        cls.shares_client = cls.os_primary.share_v2.SharesV2Client()

    def _reserve_host_and_storage(self, network_name):
        lease_name = self.get_resource_name(prefix="lease")
        host_reservation_request = {
            "min": "1",
            "max": "1",
            "resource_type": "physical:host",
            "hypervisor_properties": "",
            "resource_properties": "",
        }

        network_reservation_request = {
            "network_name": network_name,
            "resource_type": "network",
            "network_properties": "",
            "resource_properties": '["==","$usage_type","storage"]',
        }

        lease = self.create_test_lease(
            leases_client=self.leases_client,
            lease_name=lease_name,
            start_date="now",
            end_date=utils.time_offset_to_blazar_string(hours=1),
            reservations=[
                host_reservation_request,
                network_reservation_request,
            ],
        )

        active_lease = waiters.wait_for_lease_status(
            self.leases_client, lease["id"], "ACTIVE"
        )
        return active_lease

    def _validate_storage_nets(self, network_name):
        # ensure blazar created network we expect
        networks_body = self.networks_client.list_networks(name=network_name)
        networks = networks_body.get("networks")
        self.assertEqual(
            len(networks),
            1,
            "0, or more than 1 network found matching supplied name",
        )
        reserved_network = networks[0]

        subnets_body = self.subnets_client.list_subnets(
            name=f"{network_name}-subnet"
        )
        subnets = subnets_body.get("subnets")

        subnet_id = reserved_network["subnets"][0]
        reserved_subnet = subnets[0]

        self.assertEqual(
            subnet_id,
            reserved_subnet["id"],
            "subnet matching reserved name doesn't match network ID",
        )

        ports_body = self.ports_client.list_ports(
            network_id=reserved_network["id"],
            device_owner="network:router_interface",
        )
        ports = ports_body.get("ports")
        self.assertNotEmpty(ports, "no router ports found")

    def create_share(
        self,
        share_protocol=None,
        size=None,
        name=None,
        snapshot_id=None,
        description=None,
        metadata=None,
        share_network_id=None,
        share_type_id=None,
        client=None,
        cleanup=True,
    ):
        """Create a share.

        :param share_protocol: NFS or CIFS
        :param size: size in GB
        :param name: name of the share (otherwise random)
        :param snapshot_id: snapshot as basis for the share
        :param description: description of the share
        :param metadata: adds additional metadata
        :param share_network_id: id of network to be used
        :param share_type_id: type of the share to be created
        :param client: client object
        :param cleanup: default: True
        :returns: a created share
        """
        client = client or self.shares_client
        description = description or "Tempest's share"
        if not name:
            name = data_utils.rand_name("manila-scenario")
        if CONF.share.multitenancy_enabled:
            share_network_id = share_network_id or client.share_network_id
        else:
            share_network_id = None
        metadata = metadata or {}
        kwargs = {
            "share_protocol": share_protocol,
            "size": size or CONF.share.share_size,
            "name": name,
            "snapshot_id": snapshot_id,
            "description": description,
            "metadata": metadata,
            "share_network_id": share_network_id,
            "share_type_id": share_type_id,
        }
        share = self.shares_client.create_share(**kwargs)["share"]

        if cleanup:
            self.addCleanup(
                client.wait_for_resource_deletion, share_id=share["id"]
            )
            self.addCleanup(client.delete_share, share["id"])

        share_waiters.wait_for_resource_status(
            client, share["id"], "available"
        )
        return share

    @decorators.attr(type="smoke")
    @decorators.attr(type="slow")
    def test_shared_filesystem_basic(self):
        """End-to-end test of shared-filesystem flow.

        This should ensure that:
        1. a host and storage network are reserved
        2. blazar creates the network, subnet, routers for the tenant
        3. launching a host on this network allows:
           a. connectivity to internet
           b. connectivity to manila share
        4. mounting manila share works
        """
        share = self.create_share(share_protocol="NFS")
        pp(share)

        network_name = self.get_resource_name(prefix="network")
        storage_lease = self._reserve_host_and_storage(
            network_name=network_name
        )

        self.assertEqual(
            storage_lease["status"],
            "ACTIVE",
            "storage lease was not active",
        )
        self._validate_storage_nets(network_name=network_name)

        updated_share_body = self.shares_client.get_share(share["id"])
        updated_share = updated_share_body.get("share")
        pp(updated_share)

        self.assertEqual(
            updated_share["status"],
            "available",
            "share not in state available",
        )

        # ensure share has at least 1 export
        exports = self.shares_client.list_share_export_locations(share["id"])
        pp(exports)
        self.assertNotEmpty(exports.get("export_locations"))

        # ensure share has at least 1 access rule
        access_rules = self.shares_client.list_access_rules(share["id"])
        pp(access_rules)
        self.assertNotEmpty(access_rules.get("access_list"))
