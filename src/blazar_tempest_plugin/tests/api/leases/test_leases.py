from oslo_log import log as logging
from tempest import config
from tempest.lib import decorators
from tempest.lib.exceptions import NotFound

from blazar_tempest_plugin.common import utils, waiters
from blazar_tempest_plugin.tests.api.base import ReservationApiTest

CONF = config.CONF
LOG = logging.getLogger(__name__)


class TestLeasesBasic(ReservationApiTest):
    @classmethod
    def resource_setup(cls):
        lease_name = cls.get_resource_name("-lease")
        cls.lease = cls.create_test_lease(name=lease_name)

    def test_list_leases(self):
        leases_body = self.leases_client.list_leases()
        self.assertIn("leases", leases_body)
        leases = leases_body["leases"]

        self.assertEqual(1, len(leases))

        found_lease = leases[0]
        self.assertEqual(self.lease["id"], found_lease["id"])
        self.assertEqual(self.lease["name"], found_lease["name"])

    def test_show_lease(self):
        """Test to see that a user can look up their own lease by ID."""

        leases_body = self.leases_client.show_lease(self.lease["id"])
        self.assertIn("lease", leases_body)
        shown_lease = leases_body["lease"]

        self.assertEqual(self.lease["name"], shown_lease["name"])
        self.assertEqual(self.lease["id"], shown_lease["id"])


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
        lease_name = self.get_resource_name("-lease")
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

    @decorators.attr(type="smoke")
    def test_create_show_delete_lease_active(self):
        lease_name = self.get_resource_name("-lease")
        start_date = "now"
        end_date = utils.time_offset_to_blazar_string(minutes=10)
        lease = self.create_test_lease(
            name=lease_name,
            start_date=start_date,
            end_date=end_date,
        )

        # lease initial state should be PENDING
        self.assertEqual("PENDING", lease["status"])

        active_lease = waiters.wait_for_lease_status(
            self.leases_client, lease["id"], "ACTIVE"
        )
        self.assertIsNotNone(active_lease)
        self.assertIn("status", active_lease)
        self.assertEqual("ACTIVE", active_lease["status"])

        self.leases_client.delete_lease(lease["id"])
        # we've deleted the lease, attempting to show it now should be a 404
        self.assertRaises(NotFound, self.leases_client.show_lease, lease["id"])

    def test_create_show_delete_lease_terminated(self):
        lease_name = self.get_resource_name("-lease")
        start_date = "now"
        end_date = utils.time_offset_to_blazar_string(minutes=1)

        lease = self.create_test_lease(
            name=lease_name,
            start_date=start_date,
            end_date=end_date,
        )

        terminated_lease = waiters.wait_for_lease_status(
            self.leases_client, lease["id"], "TERMINATED"
        )
        self.assertIsNotNone(terminated_lease)
        self.assertIn("status", terminated_lease)
        self.assertEqual("TERMINATED", terminated_lease["status"])

        self.leases_client.delete_lease(lease["id"])
        # we've deleted the lease, attempting to show it now should be a 404
        self.assertRaises(NotFound, self.leases_client.show_lease, lease["id"])


class TestLeasesHosts(ReservationApiTest):
    """
    Basic tests that leasing a host behaves as expected.
    """

    @classmethod
    def skip_checks(cls):
        super(TestLeasesHosts, cls).skip_checks()
        if not CONF.reservation_feature_enabled.host_plugin:
            raise cls.skipException("host reservations are not enabled")

    def test_get_reserved_host_single(self):
        """Test that if lease has reservation for hosts, included hosts can be queried."""

        lease_name = self.get_resource_name("-lease")

        reservations = [
            {
                "min": "1",
                "max": "1",
                "resource_type": "physical:host",
                "hypervisor_properties": "",
                "resource_properties": "",
            }
        ]

        lease = self.create_test_lease(
            name=lease_name,
            reservations=reservations,
        )

        leases_hosts_body = self.leases_client.show_hosts_in_lease(lease["id"])
        self.assertIn("hosts", leases_hosts_body)
        hosts = leases_hosts_body["hosts"]

        LOG.info(f"found hosts: {hosts} for lease {lease['id']}")
