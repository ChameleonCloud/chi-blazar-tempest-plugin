import json

from oslo_log import log as logging
from tempest.lib import decorators
from tempest.lib.exceptions import NotFound, NotImplemented

from blazar_tempest_plugin.tests.base import ReservationTestCase

LOG = logging.getLogger(__name__)


class TestLeases(ReservationTestCase):
    """Basic CRUD ops for lease API."""

    @decorators.idempotent_id("4df952e5-0a4e-402a-a2f2-502e34be72a4")
    def test_create_lease(self):
        lease = self.create_lease()

    @decorators.idempotent_id("14099a25-f1d7-475b-942c-2775b0bb764a")
    def test_list_leases(self):
        new_lease = self.create_lease()

        _, body = self.reservation_client.list_lease()

        # get lease ID for every lease this test user can see via list_leases
        lease_ids_present = [lease.get("id") for lease in body["leases"]]

        # ensure the lease we created above is present
        self.assertIn(new_lease["id"], lease_ids_present)

    # @decorators.idempotent_id("72b56b0e-8856-4660-92fa-7058eac9998b")
    # def test_show_lease(self):
    #     raise NotImplemented

    # @decorators.idempotent_id("ad3b8e8e-55c7-4ff3-a85d-b491edc0adbe")
    # def test_update_lease(self):
    #     raise NotImplemented

    @decorators.idempotent_id("994fc7fc-9252-42fe-a157-08ef456f1a17")
    def test_delete_lease(self):
        lease = self.create_lease()

        lease_id = lease["id"]
        resp, body = self.reservation_client.delete_lease(lease_id)


class TestReservableNetwork(ReservationTestCase):
    """Test reserving a network and using it."""

    credentials = ["primary"]

    @classmethod
    def resource_setup(cls):
        super().resource_setup()

        reservation_args = {
            "resource_type": "network",
            "network_name": "my-network",
            "network_properties": "",
            "resource_properties": "",
        }
        my_lease = cls.get_lease_now(hours=1, reservations=[reservation_args])
        cls.lease = cls.wait_for_lease_status(my_lease["id"], "ACTIVE")

    def test_verify_network_details(self):
        client = self.reservation_client
        lease = self.lease

        reservations = lease.get("reservations")
        reserved_networks = [
            res for res in reservations if res.get("resource_type") == "network"
        ]

        reserved_network = reserved_networks[0]
        LOG.debug(json.dumps(reserved_network, indent=2))

        # ensure lease started
        self.assertEqual("ACTIVE", lease.get("status"))

        # ensure reservation active
        self.assertEqual("active", reserved_network.get("status"))
        self.assertEqual("network", reserved_network.get("resource_type"))

        # the resource ID does not refer to a reservable network OR to a network allocation.
        # FYI
        reservation_id = reserved_network.get("id")
        resource_id = reserved_network.get("resource_id")
        self.assertRaises(NotFound, client.get_network, resource_id)
        self.assertRaises(NotFound, client.get_network_allocation, resource_id)

        reserved_allocation_id = None

        _, body = client.list_network_allocation()
        allocations = body["allocations"]

        for alloc in allocations:
            for reservation in alloc.get("reservations", []):
                if reservation_id == reservation.get("id"):
                    # THIS ISN'T the resource_id found in the reservation!!!
                    LOG.debug(json.dumps(alloc, indent=2))
                    reserved_allocation_id = alloc.get("resource_id")
                    break
            if reserved_allocation_id:
                # break out of nested loop
                break

        # get the allocation to find the vlan it corresponds to
        _, reserved_allocation = client.get_network_allocation(reserved_allocation_id)
        _, reserved_blazar_net = client.get_network(reserved_allocation_id)
