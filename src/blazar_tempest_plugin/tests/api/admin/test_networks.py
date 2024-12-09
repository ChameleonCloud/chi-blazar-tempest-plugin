from tempest.lib.exceptions import NotImplemented

from blazar_tempest_plugin.tests.base import ReservationAPITest


class TestNetworks(ReservationAPITest):
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
