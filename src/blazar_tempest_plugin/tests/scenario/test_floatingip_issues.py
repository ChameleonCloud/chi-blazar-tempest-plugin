import time

from oslo_log import log as logging
from tempest import config
from tempest.common import waiters as waiters
from tempest.lib import exceptions as lib_exc
from tempest.lib.common.utils import data_utils
from tempest.scenario.manager import NetworkScenarioTest

CONF = config.CONF
LOG = logging.getLogger(__name__)


class BaseTestFloatingIpIssues(NetworkScenarioTest):
    def setUp(self):
        super().setUp()
        self.run_ssh = CONF.validation.run_validation
        self.ssh_user = CONF.validation.image_ssh_user

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


class TestFloatingIpIssues(BaseTestFloatingIpIssues):
    credentials = ["primary"]

    def _time_ssh_connection(
        self, ip_address, username, private_key, should_connect=True
    ):
        start = time.perf_counter()
        self.check_vm_connectivity(
            ip_address=ip_address,
            username=username,
            private_key=private_key,
            should_connect=should_connect,
        )
        end = time.perf_counter()
        duration = end - start
        LOG.info(f"connection to {ip_address} took {duration}s")
        return duration

    def test_floatingip_association(self):
        keypair = self.create_keypair()
        security_groups = [{"name": self.create_security_group()["name"]}]

        server_name = data_utils.rand_name(
            prefix=CONF.resource_name_prefix,
            name=__name__ + "-server",
        )

        server = self.create_server(
            name=server_name,
            wait_until="ACTIVE",
            keypair=keypair,
            security_groups=security_groups,
        )

        fip1 = self.create_floating_ip(server=server)
        # duration of first connection, includes time for server to boot
        duration = self._time_ssh_connection(
            ip_address=fip1["floating_ip_address"],
            username=self.ssh_user,
            private_key=keypair["private_key"],
        )
        print(f"connection to {fip1["floating_ip_address"]} took {duration}s")

        # Try again, without any changes, to find minimum time.
        duration = self._time_ssh_connection(
            ip_address=fip1["floating_ip_address"],
            username=self.ssh_user,
            private_key=keypair["private_key"],
        )
        print(f"connection to {fip1["floating_ip_address"]} took {duration}s")

        # dissasociate the first IP and connect a second one
        self.disassociate_floating_ip(fip1)
        fip2 = self.create_floating_ip(server=server)
        # time how long it takes to connect to the new IP
        # Try again, without any changes, to find minimum time.
        duration = self._time_ssh_connection(
            ip_address=fip2["floating_ip_address"],
            username=self.ssh_user,
            private_key=keypair["private_key"],
        )
        print(f"connection to {fip2["floating_ip_address"]} took {duration}s")

        # once more
        self.disassociate_floating_ip(fip2)
        fip3 = self.create_floating_ip(server=server)
        # time how long it takes to connect to the new IP
        # Try again, without any changes, to find minimum time.
        duration = self._time_ssh_connection(
            ip_address=fip3["floating_ip_address"],
            username=self.ssh_user,
            private_key=keypair["private_key"],
        )
        print(f"connection to {fip3["floating_ip_address"]} took {duration}s")
