from oslo_serialization import jsonutils as json
from tempest.lib import decorators
from tempest.lib.exceptions import Forbidden, NotFound

from blazar_tempest_plugin.tests.api.base import ReservationApiTest

BLAZAR_POLICY_PROJECT_BUG = 123456789


class TestLeasesBasic(ReservationApiTest):
    @classmethod
    def resource_setup(cls):
        super().resource_setup()
        cls.lease = cls.create_test_lease()

    def test_show_lease(self):
        """Test to see that a user can look up their own lease by ID."""

        leases_body = self.leases_client.show_lease(self.lease["id"])
        self.assertIn("lease", leases_body)
        shown_lease = leases_body["lease"]

        self.assertEqual(self.lease["name"], shown_lease["name"])
        self.assertEqual(self.lease["id"], shown_lease["id"])

    def test_list_leases(self):
        leases_body = self.leases_client.list_leases()
        self.assertIn("leases", leases_body)
        leases = leases_body["leases"]
        self.assertEqual(1, len(leases))

        found_lease = leases[0]
        self.assertEqual(self.lease["id"], found_lease["id"])
        self.assertEqual(self.lease["name"], found_lease["name"])


class TestLeasesStatus(ReservationApiTest):
    """Tests to ensure that lease state transitions work as expected.

    Valid states are:
    - PENDING
    - ACTIVE
    - TERMINATING
    - TERMINATED
    - ERROR

    show, list, and delete should work on leases in any of these states.
    update is unclear.
    """

    def test_create_show_delete_lease_pending(self):
        """Create a lease with no resouces, well in the future.
        Ensure that create,show,delete works.
        """
        lease_name = self._get_name_prefix("-lease")
        lease = self.create_test_lease(name=lease_name)
        self.assertEqual(lease_name, lease["name"])

        # lease initial state should be PENDING
        self.assertEqual("PENDING", lease["status"])

        shown_lease_body = self.leases_client.show_lease(lease["id"])
        self.assertIn("lease", shown_lease_body)
        shown_lease = shown_lease_body["lease"]

        # lease should start only in the far future, should still be PENDING
        self.assertEqual("PENDING", shown_lease["status"])

        self.assertEqual(lease["id"], shown_lease["id"])
        self.assertEqual(lease["name"], shown_lease["name"])

        self.leases_client.delete_lease(lease["id"])

        # we've deleted the lease, attempting to show it now should be a 404
        self.assertRaises(NotFound, self.leases_client.show_lease, lease["id"])

    def test_create_show_delete_lease_active(self):
        lease_name = self._get_name_prefix("-lease")
        start_date = "now"
        end_date = self._get_blazar_time_offset(minutes=10)
        lease = self.create_test_lease(
            name=lease_name,
            start_date=start_date,
            end_date=end_date,
        )

        # lease initial state should be PENDING
        self.assertEquals("PENDING", lease["status"])

        active_lease = self.wait_for_lease_status(lease["id"], "ACTIVE")
        self.assertIsNotNone(active_lease)
        self.assertIn("status", active_lease)
        self.assertEqual("ACTIVE", active_lease["status"])

        self.leases_client.delete_lease(lease["id"])
        # we've deleted the lease, attempting to show it now should be a 404
        self.assertRaises(NotFound, self.leases_client.show_lease, lease["id"])

    def test_create_show_delete_lease_terminated(self):
        lease_name = self._get_name_prefix("-lease")
        start_date = "now"
        end_date = self._get_blazar_time_offset(minutes=1)

        lease = self.create_test_lease(
            name=lease_name,
            start_date=start_date,
            end_date=end_date,
        )

        terminated_lease = self.wait_for_lease_status(lease["id"], "TERMINATED")
        self.assertIsNotNone(terminated_lease)
        self.assertIn("status", terminated_lease)
        self.assertEqual("TERMINATED", terminated_lease["status"])

        self.leases_client.delete_lease(lease["id"])
        # we've deleted the lease, attempting to show it now should be a 404
        self.assertRaises(NotFound, self.leases_client.show_lease, lease["id"])


class TestLeasesMultiUser(ReservationApiTest):
    """Test cases for what users should be able to see about each others stuff"""

    credentials = ["primary", "alt"]

    @classmethod
    def setup_credentials(cls):
        super().setup_credentials()

        cls.alt_lease_client = cls.os_alt.reservation.LeasesClient()

    @decorators.attr(type=["negative"])
    def test_show_other_project_lease(self):
        lease_name = self._get_name_prefix("-lease")
        lease = self.create_test_lease(name=lease_name)

        self.assertRaises(
            Forbidden,
            self.alt_lease_client.show_lease,
            lease["id"],
        )

    @decorators.attr(type=["negative"])
    def test_list_other_project_lease(self):
        """Listing should NOT show the lease, restricted to current project."""
        lease_name = self._get_name_prefix("-lease")
        lease = self.create_test_lease(name=lease_name)

        user2_leases = self.alt_lease_client.list_leases()["leases"]
        self.assertEmpty(user2_leases)

    @decorators.attr(type=["negative"])
    def test_update_other_project_lease(self):
        lease_name = self._get_name_prefix("-lease")
        lease_name2 = self._get_name_prefix("-user2lease")
        lease = self.create_test_lease(name=lease_name)

        # ensure user2 gets a 403 when attempting to update the lease
        self.assertRaises(
            Forbidden,
            self.alt_lease_client.update_lease,
            lease["id"],
            name=lease_name2,
        )

        # ensure the lease name didn't change
        get_lease_again = self.lease_client.show_lease(lease["id"])["lease"]
        self.assertEqual(lease_name, get_lease_again["name"])
        self.assertEqual(lease["id"], get_lease_again["id"])
        self.assertEqual(lease["status"], get_lease_again["status"])
        self.assertEqual(lease["user_id"], get_lease_again["user_id"])
        self.assertEqual(lease["project_id"], get_lease_again["project_id"])

    @decorators.attr(type=["negative"])
    def test_delete_other_project_lease(self):
        lease_name = self._get_name_prefix("-lease")
        lease = self.create_test_lease(name=lease_name)

        self.assertRaises(
            Forbidden,
            self.alt_lease_client.delete_lease,
            lease["id"],
        )
        get_lease_again = self.lease_client.show_lease(lease["id"])["lease"]
        self.assertEqual(lease_name, get_lease_again["name"])
        self.assertEqual(lease["id"], get_lease_again["id"])
        self.assertEqual(lease["status"], get_lease_again["status"])
        self.assertEqual(lease["user_id"], get_lease_again["user_id"])
        self.assertEqual(lease["project_id"], get_lease_again["project_id"])
