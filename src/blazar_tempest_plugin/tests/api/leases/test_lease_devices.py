from datetime import datetime
from datetime import timedelta

from tempest.lib import exceptions
from tempest.lib import decorators

from blazar_tempest_plugin.common import utils
from blazar_tempest_plugin.common import waiters
from blazar_tempest_plugin.tests.api.base import ContainerApiBase


class TestLeaseContainers(ContainerApiBase):
    """Test leases for containers on chi@edge."""

    def setUp(self):
        super(TestLeaseContainers, self).setUp()
        self.lease = self._reserve_device()
        self.hints = {"reservation": utils.get_device_reservation_from_lease(self.lease)}
        self.container = self._create_reserved_container("reservation-container", self.hints)
        _, container = self.container_client.get_container(self.container.uuid)
        self.assertEqual("Running", container.status)

    @decorators.attr(type="smoke")
    def test_extend_lease_for_reserved_container(self):
        """Test extending a lease that has a reserved container."""

        old_end = datetime.strptime(self.lease["end_date"], "%Y-%m-%dT%H:%M:%S.%f")
        new_end = (old_end + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")

        updated_lease = self.leases_client.update_lease(self.lease["id"], end_date=new_end)

        final_lease = waiters.wait_for_lease_status(
            self.leases_client, self.lease["id"], "ACTIVE"
        )

        expected_end_date = datetime.strptime(new_end, "%Y-%m-%d %H:%M")
        actual_end_date = datetime.fromisoformat(final_lease["end_date"])

        actual_end_date = actual_end_date.replace(microsecond=0)

        self.assertEqual(
            expected_end_date,
            actual_end_date,
            f"Expected end date {expected_end_date}, got {actual_end_date}"
        )

    @decorators.attr(type="smoke")
    def test_delete_lease_with_container(self):
        """Test deleting a lease with an associated container also deletes the container."""

        _, container = self.container_client.get_container(self.container.uuid)
        self.assertEqual("Running", container.status)

        resp = self.leases_client.delete_lease(self.lease["id"])
        self.assertEquals(200, resp.response.status)

        waiters.wait_for_lease_termination(self.leases_client, self.lease["id"])

        try:
            self.container_client.ensure_container_in_desired_state(
                self.container.uuid, "Deleted"
            )
        except exceptions.NotFound:
            container_deleted = True
        else:
            container_deleted = False
            _, container = self.container_client.get_container(self.container.uuid)
            self.assertEqual("Deleted", container.status)

        self.assertTrue(container_deleted or container.status == "Deleted",
                        "Container was not deleted after lease deletion")

    @decorators.attr(type="smoke")
    def test_device_not_in_multiple_leases(self):
        """Test that the same device cannot be used by two overlapping leases."""

        start = (datetime.utcnow() + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
        end = (datetime.utcnow() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M")

        device_id = utils.get_device_reservation_from_lease(self.lease)
        device_reservation_request = {
            "resource_type": "device",
            "min": "1",
            "max": "1",
            "resource_properties": f'["and", ["==", "$machine_name", "raspberrypi4-64"], ["==", "$uid", "{device_id}"]]',
        }

        exc = self.assertRaises(
            exceptions.ServerFault,
            self.create_test_lease,
            start_date=start,
            end_date=end,
            reservations=[device_reservation_request],
        )

        self.assertIn(
            "not enough resources available",
            str(exc).lower(),
            "Expected 'not enough resources available' error not found in exception message"
        )

    @decorators.attr(type="smoke")
    def test_device_in_lease(self):
        """Test that the device is listed in the lease details."""

        lease = self.leases_client.show_lease(self.lease["id"])["lease"]
        reservations = lease["reservations"]
        device_ids = [
            r.get("id")
            for r in reservations
            if r.get("resource_type") == "device" and r.get("id") is not None
        ]

        expected_device_id = utils.get_device_reservation_from_lease(self.lease)
        self.assertIn(
            expected_device_id,
            device_ids,
            f"Device ID {expected_device_id} not found in lease reservations with IDs: {device_ids}"
        )
