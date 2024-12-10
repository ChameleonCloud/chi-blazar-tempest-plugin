from tempest.lib.exceptions import NotImplemented

from blazar_tempest_plugin.tests.base import ReservationTestCase


class TestNetworks(ReservationTestCase):
    """Basic CRUD ops for reservable networks API."""

    def test_list_networks(self):
        networks = self.reservation_client.list_network()

    def test_get_network(self):
        network = self.reservation_client.get_network(
            network_id="8919a9bb-93c7-4843-9642-74b1099d1325"
        )

    # def test_create_network(self):
    #     raise NotImplemented

    # def test_update_network(self):
    #     raise NotImplemented

    # def test_delete_network(self):
    #     raise NotImplemented


class TestNetworkAllocations(ReservationTestCase):
    def test_list_network_allocations(self):
        allocations = self.reservation_client.list_network_allocation()

    def test_show_network_allocations(self):
        allocation = self.reservation_client.get_network_allocation(
            "6ecbff11-dc50-4794-b1e9-9bb09a462d5f"
        )

    # def test_create_network_allocation(self):
    #     raise NotImplemented

    # def test_update_network_allocation(self):
    #     raise NotImplemented

    # def test_delete_network_allocation(self):
    #     raise NotImplemented
