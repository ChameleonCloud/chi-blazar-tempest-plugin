from tempest import config
from tempest.lib import exceptions
from tempest.lib import decorators
from tempest.lib.common.utils import data_utils, test_utils
from zun_tempest_plugin.tests.tempest.api.clients import (
    ZunClient,
    set_container_service_api_microversion,
)
from zun_tempest_plugin.tests.tempest.api.common import datagen

from blazar_tempest_plugin.common import utils, waiters
from blazar_tempest_plugin.tests.api.base import ReservationApiTest


CONF = config.CONF


class TestReservationContainerApi(ReservationApiTest):
    """Test containers API on CHI@Edge."""

    @classmethod
    def skip_checks(cls):
        super(TestReservationContainerApi, cls).skip_checks()
        if not CONF.service_available.zun:
            raise cls.skipException("Zun service is not available.")

    @classmethod
    def setup_clients(cls):
        super(TestReservationContainerApi, cls).setup_clients()
        cls.floating_ips_client = cls.os_primary.floating_ips_client
        cls.container_client = ZunClient(cls.os_primary.auth_provider)
        cls.request_microversion = CONF.container_service.min_microversion
        set_container_service_api_microversion(cls.request_microversion)

    def _create_container(self, **kwargs):
        gen_model = datagen.container_data(default_data={}, **kwargs)
        resp, model = self.container_client.post_container(gen_model)

        self.addCleanup(
            test_utils.call_and_ignore_notfound_exc,
            self.container_client.delete_container,
            model.uuid,
            {"stop": True},
        )

        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(model.uuid, "Running")
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
            start_date="now",
            end_date=end_date,
            reservations=[device_reservation_request],
        )

        active_lease = waiters.wait_for_lease_status(
            leases_client, lease["id"], "ACTIVE"
        )

        return active_lease

    def _create_reserved_container(self):
        _, container = self._create_container(
            name=data_utils.rand_name("reservation-container"),
            hints=self.hints,
            image="busybox",
            command="sleep 60",
        )
        return container

    def setUp(self):
        super(TestReservationContainerApi, self).setUp()
        self.lease = self._reserve_device()
        self.hints = {"reservation": utils.get_device_reservation_from_lease(self.lease)}
        self.container = self._create_reserved_container()

    @decorators.attr(type="smoke")
    def test_launch_reserved_container(self):
        """Test launching a container."""
        resp, container = self.container_client.get_container(self.container.uuid)
        self.assertEqual("Running", container.status)

    @decorators.attr(type="smoke")
    def test_list_container(self):
        """Test listing containers."""
        resp, containers = self.container_client.list_containers()
        self.assertEqual(200, resp.status)

        data = containers.to_dict()
        for c in data.get('containers', []):
            self.assertIn('uuid', c)
        uuids = [c['uuid'] for c in data['containers']]
        self.assertEqual(len(uuids), len(set(uuids)))
        self.assertEqual(1, len(uuids))
        self.assertIn(self.container.uuid, uuids)

    @decorators.attr(type="smoke")
    def test_delete_container(self):
        """Test deleting a container."""
        del_resp = self.container_client.delete_container(
            self.container.uuid,
            {"stop": True}
        )
        self.assertIn(del_resp[0].status, (202, 204))
        try:
            self.container_client.ensure_container_in_desired_state(
                self.container.uuid, "Deleted"
            )
        except exceptions.NotFound:
            pass
