from tempest.lib import decorators
from tempest.lib.exceptions import Forbidden

from blazar_tempest_plugin.services.reservation.floatingip_client import (
    ReservableFloatingIPsClient,
)
from blazar_tempest_plugin.tests.api.base import ReservationApiTest


class TestReservationFloatingIPsApi(ReservationApiTest):
    """Non admin tests for API! That means that these are read-only."""

    @classmethod
    def setup_clients(cls):
        super().setup_clients()

        cls.client: ReservableFloatingIPsClient
        cls.client = cls.os_primary.reservation.ReservableFloatingIPsClient()

    @decorators.attr(type=["negative"])
    def test_user_list_floatingips(self):
        """Users should not be permitted to list reservable floating IPs?"""
        self.assertRaises(Forbidden, self.client.list_floatingips)
