import datetime
import json
import time

from oslo_log import log as logging
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from tempest.lib.common import fixed_network
from tempest.lib.exceptions import NotFound, NotImplemented

from blazar_tempest_plugin.tests.base import ReservationTestCase

LOG = logging.getLogger(__name__)


class BasicOperationsLeasesTest(ReservationTestCase):
    """Test basic operations on blazar leases."""

    @decorators.attr(type="smoke")
    def test_create_lease_active(self):
        """Create an empty lease, wait for it to become active."""
        lease_name = self._get_name_prefix("-lease")
        # Create a lease to start ASAP
        lease_body = {
            "name": lease_name,
            "start_date": "now",
            "end_date": self._get_blazar_time_offset(minutes=10),
        }
        initial_lease = self.create_lease(lease_body)
        self.assertEqual(lease_name, initial_lease["name"])
        self.assertEqual("PENDING", initial_lease["status"])

        # Wait for it to become active
        active_lease = self.wait_for_lease_status(initial_lease["id"], "ACTIVE")

        self.assertEqual(lease_name, active_lease["name"])
        self.assertEqual("ACTIVE", active_lease["status"])

    @decorators.attr(type="smoke")
    def test_extend_lease(self):
        """Create an empty lease, wait for it to become active, then update its expiry time."""
        lease_name = self._get_name_prefix("-lease")
        lease_expiry = self._get_blazar_time_offset(minutes=10)
        updated_lease_expiry = self._get_blazar_time_offset(minutes=60)

        # Create a lease to start ASAP
        lease_body = {
            "name": lease_name,
            "start_date": "now",
            "end_date": lease_expiry,
        }
        lease = self.create_lease(lease_body)
        active_lease = self.wait_for_lease_status(lease["id"], "ACTIVE")

        self.assertEqual("ACTIVE", active_lease["status"])

        # blazar returns the start and end dates in iso8601 format with microseconds
        # convert so we can compare
        lease_expiry_iso8601 = self._blazar_time_req_to_iso8601(lease_expiry)
        self.assertEquals(lease_expiry_iso8601, active_lease["end_date"])

        # extend the lease
        _, body = self.reservation_client.update_lease(
            active_lease["id"],
            {"end_date": updated_lease_expiry},
        )
        updated_lease = body["lease"]

        lease_expiry_iso8601 = self._blazar_time_req_to_iso8601(updated_lease_expiry)
        self.assertEquals(lease_expiry_iso8601, updated_lease["end_date"])

    @decorators.idempotent_id("14099a25-f1d7-475b-942c-2775b0bb764a")
    def test_list_leases(self):
        new_lease = self.create_lease()

        _, body = self.reservation_client.list_lease()

        # get lease ID for every lease this test user can see via list_leases
        lease_ids_present = [lease.get("id") for lease in body["leases"]]

        # ensure the lease we created above is present
        self.assertIn(new_lease["id"], lease_ids_present)

    @decorators.idempotent_id("72b56b0e-8856-4660-92fa-7058eac9998b")
    def test_show_lease(self):
        lease_name = self._get_name_prefix("-lease")
        lease = self.create_lease({"name": lease_name})

        _, show_lease_body = self.reservation_client.get_lease(lease["id"])
        shown_lease = show_lease_body["lease"]

        self.assertEquals(lease_name, shown_lease["name"])
        self.assertEquals(lease["id"], shown_lease["id"])

    @decorators.idempotent_id("ad3b8e8e-55c7-4ff3-a85d-b491edc0adbe")
    def test_update_lease(self):
        """Basic test, just update a parameter on a lease, then see if it worked."""

        lease_name_1 = self._get_name_prefix("-lease")
        lease_name_2 = self._get_name_prefix("-lease")
        lease = self.create_lease({"name": lease_name_1})

        self.assertEquals(lease_name_1, lease["name"])

        _, updated_lease_body = self.reservation_client.update_lease(
            lease["id"],
            {"name": lease_name_2},
        )
        updated_lease = updated_lease_body["lease"]
        self.assertEquals(lease_name_2, updated_lease["name"])

    @decorators.idempotent_id("994fc7fc-9252-42fe-a157-08ef456f1a17")
    def test_delete_lease(self):
        lease = self.create_lease()

        lease_id = lease["id"]
        resp, body = self.reservation_client.delete_lease(lease_id)


class EnforcementLeasesTest(ReservationTestCase):
    """Class to test enforcement of lease length, extensions, and other policies."""

    @decorators.attr(type=["negative"])
    def test_lease_create_max_duration(self):
        """Try to create a lease that exceeds the enforcement length limit."""
        lease_name = self._get_name_prefix("-lease")

        # TODO get max lease duration from config
        lease_expiry = self._get_blazar_time_offset(days=300)
        # Create a lease to start ASAP
        lease_body = {"name": lease_name, "start_date": "now", "end_date": lease_expiry}

        self.assertRaises(
            lib_exc.Forbidden,
            self.create_lease,
            lease_body,
        )

    @decorators.attr(type=["negative"])
    def test_lease_extend_max_duration(self):
        """Try to create a lease that exceeds the enforcement length limit."""
        lease_name = self._get_name_prefix("-lease")

        # TODO get lease update window from config
        lease_expiry = self._get_blazar_time_offset(days=7)
        # Create a lease to start ASAP
        lease_body = {"name": lease_name, "start_date": "now", "end_date": lease_expiry}

        lease = self.create_lease(lease_body)

        # TODO get max lease duration from config
        new_end_date = self._get_blazar_time_offset(days=300)
        lease_update_body = {"end_date": new_end_date}

        self.assertRaises(
            lib_exc.Forbidden,
            self.reservation_client.update_lease,
            lease["id"],
            lease_update_body,
        )

    @decorators.attr(type=["negative"])
    def test_lease_update_before_allowed(self):
        """Create a maximum length lease, and try to extend it before it would be allowed."""
        lease_name = self._get_name_prefix("-lease")
        lease_expiry = self._get_blazar_time_offset(days=7)
        # Create a lease to start ASAP
        lease_body = {"name": lease_name, "start_date": "now", "end_date": lease_expiry}

        self.assertRaises(lib_exc.Forbidden, self.create_lease, lease_body)


class TestReservableNetwork(ReservationTestCase):
    """Test reserving a network and using it."""

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.networks_client = cls.os_primary.networks_client
        cls.subnets_client = cls.os_primary.subnets_client

    def _get_lease_body_for_network_res(
        self, lease_name, network_name, resource_properties
    ):
        reservations_dict = {"resource_type": "network"}
        reservations_dict.setdefault("network_properties", "")

        if resource_properties:
            reservations_dict["resource_properties"] = resource_properties
        else:
            reservations_dict["resource_properties"] = ""

        if network_name:
            reservations_dict["network_name"] = network_name

        lease_body = {
            "name": lease_name,
            "start_date": "now",
            "end_date": self._get_blazar_time_offset(minutes=30),
            "reservations": [reservations_dict],
        }
        return lease_body

    def lease_a_network(self, lease_name, network_name=None, resource_properties=None):
        body = self._get_lease_body_for_network_res(
            lease_name, network_name, resource_properties
        )
        lease = self.create_lease(body)
        active_lease = self.wait_for_lease_status(lease["id"], "ACTIVE")
        return active_lease

    def _validate_network_lease(self, active_lease):
        self.assertEqual("ACTIVE", active_lease["status"])
        self.assertIn("reservations", active_lease)
        self.assertNotEmpty(active_lease["reservations"])

        network_reservation = active_lease["reservations"][0]
        self.assertEquals("active", network_reservation["status"])
        self.assertFalse(network_reservation["missing_resources"])
        self.assertFalse(network_reservation["resources_changed"])

    def test_isolated_network(self):
        lease_name = self._get_name_prefix("-lease")
        network_name = self._get_name_prefix("-network")

        active_lease = self.lease_a_network(
            lease_name,
            network_name,
            resource_properties="",
        )
        self._validate_network_lease(active_lease)

        # NOTE! the resource_id returned from the created reservation cannot be used to find the created network.
        # it does NOT correspond to the neutron network, the blazar reservable network, or the blazar network allocation.
        # The only way to find the created network is to look up a network owned by the same project as the lease,
        # with a name matching the one that was passed in the reservation request.
        network = fixed_network.get_network_from_name(
            network_name, self.networks_client
        )

        # we should have a network!
        self.assertIsNotNone(network)
        self.assertEqual(network_name, network["name"])
        self.assertEqual("ACTIVE", network["status"])
        self.assertTrue(network["admin_state_up"])

        # the network should NOT have a subnet, we're creating that ourselves.
        self.assertIn("subnets", network)
        self.assertEmpty(network["subnets"])

    def test_stitchable_network(self):
        lease_name = self._get_name_prefix("-lease")
        network_name = self._get_name_prefix("-network")

        active_lease = self.lease_a_network(
            lease_name,
            network_name,
            resource_properties='["==","$stitch_provider","fabric"]',
        )
        self._validate_network_lease(active_lease)

        network = fixed_network.get_network_from_name(
            network_name, self.networks_client
        )

        # we should have a network!
        self.assertIsNotNone(network)
        self.assertEqual(network_name, network["name"])
        self.assertEqual("ACTIVE", network["status"])
        self.assertTrue(network["admin_state_up"])

        # the network should NOT have a subnet, we're creating that ourselves.
        self.assertIn("subnets", network)
        self.assertEmpty(network["subnets"])

        # ensure we're allowed to see provide network properties for our network
        # if these are not true, then users doing stitching will have problems
        self.assertIn("provider:network_type", network)
        self.assertIn("provider:physical_network", network)
        self.assertIn("provider:segmentation_id", network)

    def test_storage_network(self):
        lease_name = self._get_name_prefix("-lease")
        network_name = self._get_name_prefix("-network")

        active_lease = self.lease_a_network(
            lease_name,
            network_name,
            resource_properties='["==","$usage_type","storage"]',
        )
        self._validate_network_lease(active_lease)

        network = fixed_network.get_network_from_name(
            network_name, self.networks_client
        )

        # we should have a network!
        self.assertIsNotNone(network)
        self.assertEqual(network_name, network["name"])
        self.assertEqual("ACTIVE", network["status"])
        self.assertTrue(network["admin_state_up"])

        # This case is unique from the others, the storage network SHOULD have a subnet
        # the subnet must be from the same subnet pool as the storage router and manila nfs endpoint
        self.assertIn("subnets", network)
        self.assertNotEmpty(network["subnets"])

        storage_subnet = network["subnets"][0]

        print(json.dumps(storage_subnet))

    @decorators.attr(type=["negative"])
    def test_isolated_network_no_name(self):
        """We should get a 400 error if network name is not present."""
        lease_name = self._get_name_prefix("-lease")
        self.assertRaises(
            lib_exc.BadRequest, self.lease_a_network, lease_name, resource_properties=""
        )

    def test_clean_up_network_resources(self):
        def wait_for_lease_deleted(lease_id):
            time.sleep(10)

        lease_name = self._get_name_prefix("-lease")
        network_name = self._get_name_prefix("-network")

        active_lease = self.lease_a_network(
            lease_name, network_name, resource_properties=""
        )

        network = fixed_network.get_network_from_name(
            network_name, self.networks_client
        )

        # the network should NOT have a subnet, we're creating that ourselves.
        self.assertIn("subnets", network)
        self.assertEmpty(network["subnets"])

        # add a subnet to the network, this will make cleanup take longer
        subnet = self.subnets_client.create_subnet(
            network_id=network["id"], ip_version=4, cidr="10.20.30.40/28"
        )

        # by the time lease_delete returns, the network should be deleted!
        # if not the case, closely following reservations will fail
        _, result = self.reservation_client.delete_lease(active_lease["id"])

        # # do we need to poll for the lease to be fully cleaned up?
        # wait_for_lease_deleted(active_lease["id"])

        self.assertRaises(
            lib_exc.NotFound, self.networks_client.show_network, network["id"]
        )
