import time

from oslo_log import log as logging
from tempest import config
from tempest.lib import exceptions as lib_exc
from tempest.scenario import manager

from blazar_tempest_plugin.tests.base import ReservationTestMixin

CONF = config.CONF
LOG = logging.getLogger(__name__)


class ReservationScenarioTest(ReservationTestMixin, manager.NetworkScenarioTest):
    """Base class for scenario tests focused on reservable resources."""

    def setUp(self):
        super().setUp()
        self.run_ssh = CONF.validation.run_validation
        self.ssh_user = CONF.validation.image_ssh_user

    def verify_ssh(self, keypair):
        if self.run_ssh:
            # Obtain server IP
            self.ip = self.get_server_ip(self.instance)
            # Check ssh
            self.ssh_client = self.get_remote_client(
                ip_address=self.ip,
                username=self.ssh_user,
                private_key=keypair["private_key"],
                server=self.instance,
            )

    def reserve_one_resource(self, resource_type, resource_properties, **kwargs):
        """Create a lease for quantity one of a resource, and return the reservation ID."""

        reservation_kwargs = {
            "min": "1",
            "max": "1",
            "resource_type": resource_type,
            "resource_properties": resource_properties,
            **kwargs,
        }

        lease = self.get_lease_now(hours=1, reservations=[reservation_kwargs])
        return self.wait_for_lease_status(lease_id=lease["id"], status="ACTIVE")

        # for res in lease["reservations"]:
        #     if res["resource_type"] == resource_type:
        #         return res["id"]

    def reserve_node(self, resource_properties="", hypervisor_properties=""):
        return self.reserve_one_resource(
            resource_type="physical:host",
            resource_properties=resource_properties,
            hypervisor_properties=hypervisor_properties,
        )

    def reserve_network(
        self, resource_properties="", network_properties="", network_name=None
    ):
        return self.reserve_one_resource(
            resource_type="network",
            network_name=network_name,
            network_properties=network_properties,
            resource_properties=resource_properties,
        )

    def wait_for_reservable_network(self, network_client, network_name):
        def is_active(network: dict):
            return network.get("status") == "ACTIVE"

        start_time = time.time()
        while time.time() - start_time <= network_client.build_timeout:
            networks = self.networks_client.list_networks(name=network_name)["networks"]
            if len(networks) > 0 and all(is_active(net) for net in networks):
                return networks
            time.sleep(network_client.build_interval)
        raise lib_exc.TimeoutException
