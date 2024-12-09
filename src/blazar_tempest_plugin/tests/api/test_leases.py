import json

from oslo_log import log as logging
from tempest.lib import decorators
from tempest.lib.common.utils import data_utils, test_utils

from blazar_tempest_plugin.tests.base import ReservationAPITest

LOG = logging.getLogger(__name__)


class TestLeases(ReservationAPITest):
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

    @decorators.idempotent_id("72b56b0e-8856-4660-92fa-7058eac9998b")
    def test_show_lease(self):
        pass

    @decorators.idempotent_id("ad3b8e8e-55c7-4ff3-a85d-b491edc0adbe")
    def test_update_lease(self):
        pass

    @decorators.idempotent_id("994fc7fc-9252-42fe-a157-08ef456f1a17")
    def test_delete_lease(self):
        lease = self.create_lease()

        lease_id = lease["id"]
        resp, body = self.reservation_client.delete_lease(lease_id)


class TestReservableNetwork(ReservationAPITest):
    """Test reserving a network and using it."""

    credentials = ["primary"]

    @classmethod
    def resource_setup(cls):
        super().resource_setup()

        lease_args = cls.get_1h_lease_args()
        reservation_args = {
            "resource_type": "network",
            "network_name": "my-network",
        }
        lease_args["reservations"] = [reservation_args]
        print(json.dumps(lease_args, indent=2))

        my_lease = cls.create_lease(body=lease_args)
        cls.wait_for_lease_status(my_lease["id"], "ACTIVE")
        cls.lease = my_lease

    def test_verify_network_details(self):
        print(self.lease)
