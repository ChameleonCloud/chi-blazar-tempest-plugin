from tempest import config
from tempest.lib import decorators
from tempest.lib.common.utils import data_utils, test_utils
from zun_tempest_plugin.tests.tempest.api.clients import (
    ZunClient,
    set_container_service_api_microversion,
)
from zun_tempest_plugin.tests.tempest.api.common import datagen

from blazar_tempest_plugin.common import utils, waiters
from blazar_tempest_plugin.tests.scenario.base import ReservationScenarioTest

# Tests for CHI@Edge containers on devices


CONF = config.CONF


class ReservationZunTest(ReservationScenarioTest):
    """Test Zun operations with CHI@Edge reservations."""

    # override so as to not use admin credentials
    credentials = ["primary"]

    @classmethod
    def skip_checks(cls):
        super(ReservationZunTest, cls).skip_checks()
        if not CONF.service_available.zun:
            raise cls.skipException("Zun service is not available.")

    @classmethod
    def setup_clients(cls):
        super(ReservationZunTest, cls).setup_clients()
        cls.floating_ips_client = cls.os_primary.floating_ips_client
        cls.container_client = ZunClient(cls.os_primary.auth_provider)

        # set microversion to 1.12 so we can delete the test containers
        cls.request_microversion = CONF.container_service.min_microversion
        set_container_service_api_microversion(cls.request_microversion)

    def _create_container(self, **kwargs):
        gen_model = datagen.container_data(default_data={}, **kwargs)
        resp, model = self.container_client.post_container(gen_model)

        # specify "stop" so that running containers can be deleted without admin
        self.addCleanup(
            test_utils.call_and_ignore_notfound_exc,
            self.container_client.delete_container,
            model.uuid,
            {"stop": True},
        )

        self.assertEqual(202, resp.status)
        # Wait for container to finish creation
        # In chi@edge, we skip the created state and go directly to Running
        # TODO: need to handle "error" and "deleted" failure states
        self.container_client.ensure_container_in_desired_state(model.uuid, "Running")
        # TODO: log how long it took to get to Running state
        return resp, model

    def _reserve_device(self, leases_client=None):
        """Reserve a device for testing."""
        if not leases_client:
            leases_client = self.leases_client

        device_reservation_request = {
            "resource_type": "device",
            "min": "1",
            "max": "1",
            "resource_properties": '["==", "$machine_name", "raspberrypi4-64"]',
        }

        end_date = utils.time_offset_to_blazar_string(hours=1)
        lease = self.create_test_lease(
            leases_client=leases_client,
            start_date="now",
            end_date=end_date,
            reservations=[device_reservation_request],
        )

        active_lease = waiters.wait_for_lease_status(
            leases_client, lease["id"], "ACTIVE"
        )

        return active_lease

    @decorators.attr(type="smoke")
    def test_container_launch_with_reservation(self):
        """Test launching a container with a reservation."""
        lease = self._reserve_device()

        hints = {}
        hints["reservation"] = utils.get_device_reservation_from_lease(lease)
        _, container = self._create_container(
            name=data_utils.rand_name("reservation-container"),
            hints=hints,
            image="busybox",
            command="sleep 60",
        )

        # get refreshed container info
        resp, container = self.container_client.get_container(container.uuid)
        self.assertEqual("Running", container.status)

        # add a floating IP and verify it's there and usable
        fip = self.floating_ips_client.create_floatingip(
            floating_network_id=CONF.network.public_network_id
        )
        fip_list = self.floating_ips_client.list_floatingips()
        self.assertIn(fip["floatingip"]["id"], [fip["id"] for fip in fip_list["floatingips"]],
                      "Floating IP was not added successfully.")

        fip_addr = fip["floatingip"]["floating_ip_address"]
        self.addCleanup(
            test_utils.call_and_ignore_notfound_exc,
            self.floating_ips_client.delete_floatingip,
            fip["floatingip"]["id"]
        )

        utils.attach_floating_ip_to_container(
            self.container_client,
            self.floating_ips_client,
            container.uuid,
            fip["floatingip"]["id"]
        )
        utils.wait_for_fip_on_container(
            self.container_client,
            self.floating_ips_client,
            container.uuid,
            fip_addr
        )

        _, container = self.container_client.get_container(container.uuid)
        attached = utils.get_container_floating_ip(self.floating_ips_client, container)
        self.assertEqual(
            fip_addr, attached,
            f"Expected floating IP {fip_addr} to be attached to container {container.uuid}, but got {attached}"
        )

        # verify we can ping the floating IP
        utils.ping_ip(fip_addr)

        # verify we can delete the container's floating IP and it goes away
        self.floating_ips_client.delete_floatingip(fip["floatingip"]["id"])
        fip_list = self.floating_ips_client.list_floatingips()
        self.assertNotIn(fip["floatingip"]["id"], [fip["id"] for fip in fip_list["floatingips"]],
                         "Floating IP was not deleted successfully.")
