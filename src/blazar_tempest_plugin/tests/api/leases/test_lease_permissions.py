from tempest.lib import decorators
from tempest.lib.exceptions import Forbidden

from blazar_tempest_plugin.tests.api.base import ReservationApiTest


class TestLeasesMultiUser(ReservationApiTest):
    """Test cases for what users should be able to see about each others stuff"""

    credentials = ["primary", "alt"]

    @classmethod
    def setup_credentials(cls):
        super().setup_credentials()

        cls.alt_lease_client = cls.os_alt.reservation.LeasesClient()

    @decorators.attr(type=["negative"])
    def test_show_other_project_lease(self):
        lease_name = self.get_resource_name("-lease")
        lease = self.create_test_lease(name=lease_name)

        self.assertRaises(
            Forbidden,
            self.alt_lease_client.show_lease,
            lease["id"],
        )

    @decorators.attr(type=["negative"])
    def test_list_other_project_lease(self):
        """Listing should NOT show the lease, restricted to current project."""
        lease_name = self.get_resource_name("-lease")
        lease = self.create_test_lease(name=lease_name)

        user2_leases = self.alt_lease_client.list_leases()["leases"]
        self.assertEmpty(user2_leases)

    @decorators.attr(type=["negative"])
    def test_update_other_project_lease(self):
        lease_name = self.get_resource_name("-lease")
        lease_name2 = self.get_resource_name("-user2lease")
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
        lease_name = self.get_resource_name("-lease")
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
