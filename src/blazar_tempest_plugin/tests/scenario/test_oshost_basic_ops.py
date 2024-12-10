import json
import time

import netaddr
from oslo_log import log as logging
from tempest import config
from tempest.common import compute, waiters
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from tempest.lib.common.utils import data_utils, test_utils

from blazar_tempest_plugin.tests.scenario.base import ReservationScenarioTest

CONF = config.CONF
LOG = logging.getLogger(__name__)


def pp(data):
    print(json.dumps(data, indent=2))


class TestReservableBaremetalNode(ReservationScenarioTest):
    """Basic existence test, we will test the following

    1. make a reservation for any one baremetal host
    2. wait for it to start
    3. create an instance using the reservation
    4. ensure we can ssh to it using a floating ip
    5. verify the contents of the vendordata endpoint

    Much of the logic is copied from tempest.scenario.test_server_basic_ops
    """

    def _reserve_physical_host(self):
        """Create a lease for a physical host and wait for it to become active.
        Returns the reservation to be used for scheduling.
        """

        host_reservation_request = {
            "min": "1",
            "max": "1",
            "resource_type": "physical:host",
            "hypervisor_properties": "",
            "resource_properties": "",
        }

        lease = self.get_lease_now(hours=1, reservations=[host_reservation_request])
        self.wait_for_lease_status(lease_id=lease["id"], status="ACTIVE")

        for res in lease["reservations"]:
            if res["resource_type"] == "physical:host":
                return res["id"]

    @decorators.attr(type="smoke")
    def test_reservable_server_basic_ops(self):
        keypair = self.create_keypair()
        reservation_id = self._reserve_physical_host()
        self.instance = self.create_server(
            keypair=keypair,
            wait_until="SSHABLE",
            scheduler_hints={"reservation": reservation_id},
            flavor=CONF.reservation.reservable_flavor_ref,
        )


class TestReservableNetwork(ReservationScenarioTest):
    @classmethod
    def setup_credentials(cls):
        # Do not setup network resources for this test
        cls.set_network_resources()
        super().setup_credentials()

    def _get_name_prefix(self, prefix):
        return data_utils.rand_name(
            prefix=CONF.resource_name_prefix,
            name=self.__class__.__name__ + prefix,
        )

    def setup_subnet_and_router_isolated(self, network):
        subnet_name = self._get_name_prefix("-subnet")
        subnet = self.subnets_client.create_subnet(
            network_id=network["id"],
            ip_version=4,
            cidr="10.20.30.40/28",
            name=subnet_name,
        )["subnet"]

        router = self.get_router()
        self.routers_client.add_router_interface(router["id"], subnet_id=subnet["id"])
        LOG.debug("Attached router %s to subnet %s", router["id"], subnet["id"])

        # save a cleanup job to remove this association between
        # router and subnet
        self.addCleanup(
            test_utils.call_and_ignore_notfound_exc,
            self.routers_client.remove_router_interface,
            router["id"],
            subnet_id=subnet["id"],
        )

        return subnet, router

    def get_server_port_id_and_ip4(self, server, ip_addr=None, **kwargs):
        """Override parent implementation to avoid admin client"""

        def _is_active(port):
            return port["status"] == "ACTIVE"

        client = self.ports_client
        try:
            ports = waiters.wait_for_server_ports_active(
                client=client, server_id=server["id"], is_active=_is_active, **kwargs
            )
        except lib_exc.TimeoutException:
            LOG.error(
                "Server ports failed transitioning to ACTIVE for " "server: %s", server
            )
            raise

        port_map = [
            (p["id"], fxip["ip_address"])
            for p in ports
            for fxip in p["fixed_ips"]
            if _is_active(p)
        ]

        self.assertNotEmpty(port_map, "No IPv4 addresses found in: %s" % ports)
        self.assertEqual(
            len(port_map),
            1,
            "Found multiple IPv4 addresses: %s. "
            "Unable to determine which port to target." % port_map,
        )
        return port_map[0]

    def test_reserve_network(self):
        # ensure we have a unique name, it is the only way to later reference the network
        network_name = self._get_name_prefix("-network")
        network_lease = self.reserve_network(network_name=network_name)
        reserved_networks = self.wait_for_reservable_network(
            self.networks_client, network_name
        )

        network = reserved_networks[0]
        subnet, router = self.setup_subnet_and_router_isolated(network)

        validation_resources = self.get_test_validation_resources(self.os_primary)

        server = compute.create_test_server(
            clients=self.os_primary,
            tenant_network=network,
            wait_until="SSHABLE",
            validatable=True,
            validation_resources=validation_resources,
        )

    # def test_reserve_stitchable_network(self):
    #     network = self.reserve_network()

    # def test_reserve_storage_network(self):
    #     network = self.reserve_network()
