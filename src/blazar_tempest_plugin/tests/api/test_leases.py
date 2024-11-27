from tempest.lib import decorators
from tempest.lib.common.utils import data_utils, test_utils

from blazar_tempest_plugin.tests.api import base


class TestLeases(base.BaseReservationTest):
    """Basic CRUD ops for lease API."""

    def test_create_lease(self):
        _, lease = self.client.create_lease(
            {
                "name": "my_lease",
                "start_date": "2050-12-26 12:00",
                "end_date": "2050-12-27 12:00",
            }
        )

        self.addCleanup(
            test_utils.call_and_ignore_notfound_exc,
            self.client.delete_lease,
            lease["lease_id"],
        )

    def test_list_leases(self):
        self.create_lease()

        _, body = self.client.list_lease()

        # get lease ID for every lease this test user can see via list_leases
        lease_ids_present = [lease.get("id") for lease in body["leases"]]

        # ensure the lease we created above is present
        self.assertIn(self.created_leases[0], lease_ids_present)

    def test_show_lease(self):
        pass

    def test_update_lease(self):
        pass

    def test_delete_lease(self):
        self.create_lease()

        lease_id = self.created_leases[0]
        resp, body = self.client.delete_lease(lease_id)
