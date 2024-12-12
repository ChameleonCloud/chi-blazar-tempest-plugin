from oslo_log import log as logging
from tempest import config
from tempest.lib.common import validation_resources as vr
from tempest.scenario import manager

from blazar_tempest_plugin.tests.scenario.base import ReservableNetworkScenarioTest

CONF = config.CONF
LOG = logging.getLogger(__name__)


class TestReservableVlans(ReservableNetworkScenarioTest):
    """This test case executes the common pattern of

    1. reserve a network with some parameters
    2. create a subnet on said network
    3. attach a router to said network
    4. use an instance to verify the functionality of said network
    """

    @classmethod
    def setup_credentials(cls):
        # Create no network resources for these tests.
        cls.set_network_resources()
        super().setup_credentials()

    def _test_isolated_network(
        self,
        resource_properties="",
    ):
        network_name = self._get_name_prefix("-network")
        network_lease = self.reserve_one_resource(
            resource_type="network",
            network_name=network_name,
            network_properties="",
            resource_properties=resource_properties,
        )
        networks = self.wait_for_reservable_network(self.networks_client, network_name)

        # we should have exactly one network which matches our reserved network name
        self.assertEqual(1, len(networks))
        reserved_network = networks[0]

        # add subnet to network
        subnet = self.create_subnet_on_isolated_network(reserved_network)

        # create router w. external connectivity
        # add router port to network
        router = self.create_new_router_for_subnet(subnet)

        keypair = self.create_keypair()

        # defaults to including rules to allow ssh
        security_groups = [{"name": self.create_security_group()["name"]}]

        # launch instance on network
        server = self.create_server(
            name=self._get_name_prefix("-server"),
            wait_until="ACTIVE",
            keypair=keypair,
            networks=[{"uuid": reserved_network["id"]}],
            security_groups=security_groups,
        )

        # associate floating IP to instance
        fip = self.create_floating_ip(server=server)

        # verify connectivty to instance via floating IP
        result = self.check_vm_connectivity(
            ip_address=fip["floating_ip_address"],
            username=self.ssh_user,
            private_key=keypair["private_key"],
        )

        return result

    def test_isolated_network(self):
        result = self._test_isolated_network()


class TestStitchableNetwork(TestReservableVlans):
    def test_isolated_network(self):
        result = self._test_isolated_network(
            resource_properties='["==","$stitch_provider","fabric"]'
        )


class TestStorageNetwork(ReservableNetworkScenarioTest):
    @classmethod
    def setup_credentials(cls):
        # Create no network resources for these tests.
        cls.set_network_resources()
        super().setup_credentials()

    def test_storage_network(self):
        network_name = self._get_name_prefix("-network")
        network_lease = self.reserve_one_resource(
            resource_type="network",
            network_name=network_name,
            network_properties="",
            resource_properties='["==","$usage_type","storage"]',
        )
        networks = self.wait_for_reservable_network(self.networks_client, network_name)

        # we should have exactly one network which matches our reserved network name
        self.assertEqual(1, len(networks))
        reserved_network = networks[0]

        keypair = self.create_keypair()

        # defaults to including rules to allow ssh
        security_groups = [{"name": self.create_security_group()["name"]}]

        # launch instance on network
        server = self.create_server(
            name=self._get_name_prefix("-server"),
            wait_until="ACTIVE",
            keypair=keypair,
            networks=[{"uuid": reserved_network["id"]}],
            security_groups=security_groups,
        )

        # associate floating IP to instance
        fip = self.create_floating_ip(server=server)

        # verify connectivty to instance via floating IP
        result = self.check_vm_connectivity(
            ip_address=fip["floating_ip_address"],
            username=self.ssh_user,
            private_key=keypair["private_key"],
        )

        # test that we can ping router gw

        # test that we can ping nfs mount
