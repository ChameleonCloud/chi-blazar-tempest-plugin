import time

from oslo_log import log as logging
from tempest import config
from tempest.common import waiters
from tempest.lib import exceptions as lib_exc
from tempest.lib.common.utils import data_utils, test_utils
from tempest.scenario import manager

from blazar_tempest_plugin.common import utils, waiters

CONF = config.CONF
LOG = logging.getLogger(__name__)


class ReservationScenarioTest(manager.ScenarioTest):
    """Base class for scenario tests focused on reservable resources."""

    credentials = ["primary"]

    @classmethod
    def skip_checks(cls):
        super().skip_checks()
        if not CONF.service_available.blazar:
            skip_msg = "Blazar is disabled"
            raise cls.skipException(skip_msg)

    @classmethod
    def setup_credentials(cls):
        cls.set_network_resources()
        super().setup_credentials()

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
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

    # def setUp(self):
    #     super().setUp()
    #     self.run_ssh = CONF.validation.run_validation
    #     self.ssh_user = CONF.validation.image_ssh_user

    # def verify_ssh(self, keypair):
    #     if self.run_ssh:
    #         # Obtain server IP
    #         self.ip = self.get_server_ip(self.instance)
    #         # Check ssh
    #         self.ssh_client = self.get_remote_client(
    #             ip_address=self.ip,
    #             username=self.ssh_user,
    #             private_key=keypair["private_key"],
    #             server=self.instance,
    #         )

    # def reserve_one_resource(self, resource_type, resource_properties, **kwargs):
    #     """Create a lease for quantity one of a resource, and return the reservation ID."""

    #     reservation_kwargs = {
    #         "min": "1",
    #         "max": "1",
    #         "resource_type": resource_type,
    #         "resource_properties": resource_properties,
    #         **kwargs,
    #     }

    #     lease = self.get_lease_now(hours=1, reservations=[reservation_kwargs])
    #     return self.wait_for_lease_status(lease_id=lease["id"], status="ACTIVE")

    #     # for res in lease["reservations"]:
    #     #     if res["resource_type"] == resource_type:
    #     #         return res["id"]

    # def reserve_node(self, resource_properties="", hypervisor_properties=""):
    #     return self.reserve_one_resource(
    #         resource_type="physical:host",
    #         resource_properties=resource_properties,
    #         hypervisor_properties=hypervisor_properties,
    #     )


class ReservableNetworkScenarioTest(
    ReservationScenarioTest, manager.NetworkScenarioTest
):
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
        """Wait for network lease to become active.

        Returns a list of networks that were reserved.
        """

        def is_active(network: dict):
            return network.get("status") == "ACTIVE"

        start_time = time.time()
        while time.time() - start_time <= network_client.build_timeout:
            networks = self.networks_client.list_networks(name=network_name)["networks"]
            if len(networks) > 0 and all(is_active(net) for net in networks):
                return networks
            time.sleep(network_client.build_interval)
        raise lib_exc.TimeoutException

    def create_subnet_on_isolated_network(self, network):
        """Re-implement create subnet helper,
        assumption that network has no other subnets.

        """

        client = self.subnets_client

        subnet_name = self._get_name_prefix("-subnet")
        subnet = client.create_subnet(
            network_id=network["id"],
            ip_version=4,
            cidr="10.20.30.40/28",
            name=subnet_name,
        )["subnet"]

        self.addCleanup(
            test_utils.call_and_ignore_notfound_exc,
            client.delete_subnet,
            subnet["id"],
        )
        return subnet

    def create_new_router_for_subnet(self, subnet):
        client = self.routers_client

        public_network_id = CONF.network.public_network_id
        router_name = self._get_name_prefix("-router")

        router = client.create_router(
            name=router_name,
            external_gateway_info={"network_id": public_network_id},
        )["router"]

        self.addCleanup(
            test_utils.call_and_ignore_notfound_exc,
            client.delete_router,
            router["id"],
        )

        client.add_router_interface(router["id"], subnet_id=subnet["id"])
        self.addCleanup(
            test_utils.call_and_ignore_notfound_exc,
            client.remove_router_interface,
            router["id"],
            subnet_id=subnet["id"],
        )
        return router

    def get_server_port_id_and_ip4(self, server, ip_addr=None, **kwargs):
        """Override parent class to avoid needing os_admin."""

        if ip_addr and not kwargs.get("fixed_ips"):
            kwargs["fixed_ips"] = "ip_address=%s" % ip_addr

        # A port can have more than one IP address in some cases.
        # If the network is dual-stack (IPv4 + IPv6), this port is associated
        # with 2 subnets

        def _is_active(port):
            return port["status"] == "ACTIVE"

        # Wait for all compute ports to be ACTIVE.
        # This will raise a TimeoutException if that does not happen.
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
        inactive = [p for p in ports if p["status"] != "ACTIVE"]
        if inactive:
            # This should just be Ironic ports, see _is_active() above
            LOG.debug("Instance has ports that are not ACTIVE: %s", inactive)

        self.assertNotEmpty(port_map, "No IPv4 addresses found in: %s" % ports)
        self.assertEqual(
            len(port_map),
            1,
            "Found multiple IPv4 addresses: %s. "
            "Unable to determine which port to target." % port_map,
        )
        return port_map[0]
