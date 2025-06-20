from datetime import datetime, timedelta

from tempest.lib import decorators

from blazar_tempest_plugin.common import utils
from blazar_tempest_plugin.tests.api.base import ContainerApiBase


class TestReservationContainerApiFailures(ContainerApiBase):
    """Test containers API for failures on CHI@Edge."""

    def setUp(self):
        super(TestReservationContainerApiFailures, self).setUp()

    @decorators.attr(type="smoke")
    def test_launch_unreserved_container_fails(self):
        """Test launching an unreserved container fails."""
        self.container = self._create_reserved_container("unreserved-container", {}, "Error")
        _, container = self.container_client.get_container(self.container.uuid)
        self.assertEqual("Error", container.status)

    @decorators.attr(type="smoke")
    def test_launch_container_with_expired_lease_fails(self):
        """Test launching a container with an expired lease fails."""
        # create a short lease and wait for it to expire
        self.lease = self._reserve_device(
            lease_status="TERMINATED",
            start_date=(datetime.utcnow() + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"),
            end_date=(datetime.utcnow() + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M")
        )
        # now that the lease is expired, try to use it to create a container
        self.hints = {"reservation": utils.get_device_reservation_from_lease(self.lease)}
        self.container = self._create_reserved_container("reservation-container", self.hints, "Error")
        _, container = self.container_client.get_container(self.container.uuid)
        self.assertEqual("Error", container.status)

    @decorators.attr(type="smoke")
    def test_launch_container_with_future_lease_fails(self):
        """Test launching a container with a future lease fails."""
        self.lease = self._reserve_device(
            lease_status="PENDING",
            start_date=(datetime.utcnow() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M"),
            end_date=(datetime.utcnow() + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M")
        )
        self.hints = {"reservation": utils.get_device_reservation_from_lease(self.lease)}
        self.container = self._create_reserved_container("reservation-container", self.hints, "Error")
        _, container = self.container_client.get_container(self.container.uuid)
        self.assertEqual("Error", container.status)
