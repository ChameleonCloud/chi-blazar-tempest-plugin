from tempest.lib import exceptions
from tempest.lib import decorators

from blazar_tempest_plugin.common import utils
from blazar_tempest_plugin.tests.api.base import ContainerApiBase


class TestReservationContainerApi(ContainerApiBase):
    """Test containers API on CHI@Edge."""

    def setUp(self):
        super(TestReservationContainerApi, self).setUp()
        self.lease = self._reserve_device()
        self.hints = {"reservation": utils.get_device_reservation_from_lease(self.lease)}
        self.container = self._create_reserved_container("reservation-container", self.hints)

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

    @decorators.attr(type="smoke")
    def test_get_container_logs(self):
        """Test get logs from a container."""
        resp, logs = self.container_client.get(f"/containers/{self.container.uuid}/logs")
        self.assertEqual(200, resp.status)
        output = logs.decode('utf-8')
        self.assertIn('hello-from-container', output)
