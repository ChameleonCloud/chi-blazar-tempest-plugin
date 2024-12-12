from oslo_serialization import jsonutils as json
from tempest.lib import exceptions as lib_exc
from tempest.lib.common import rest_client

from blazar_tempest_plugin.services.reservation.networks_client import (
    ReservableNetworksClient,
)
from blazar_tempest_plugin.tests.api.base import ReservationApiTest


def _pp(data):
    print(json.dumps(data, indent=2))


class TestReservationNetworksApi(ReservationApiTest):
    """Non admin tests for API! That means that these are read-only."""

    @classmethod
    def setup_clients(cls):
        super().setup_clients()

        cls.client: ReservableNetworksClient
        cls.client = cls.os_primary.reservation.ReservableNetworksClient()

    def test_list_networks(self):
        networks = self.client.list_networks()
        self.assertIn("networks", networks)

    def test_show_network(self):
        """We can't create a network without admin api, so can't guarantee this test."""

        networks: rest_client.ResponseBody
        networks = self.client.list_networks()["networks"]

        if not networks:
            raise lib_exc.InvalidConfiguration("no networks available, cannot show.")

        found_network = networks[0]
        network = self.client.show_network(network_id=found_network["id"])

    def test_list_network_allocations(self):
        networks = self.client.list_networks()["networks"]
        if not networks:
            raise lib_exc.InvalidConfiguration("no networks available, cannot show.")

        allocations = self.client.list_network_allocations()
        self.assertIn("allocations", allocations)

    def test_show_network_allocation(self):
        networks = self.client.list_networks()["networks"]
        if not networks:
            raise lib_exc.InvalidConfiguration("no networks available, cannot show.")

        found_network = networks[0]
        network_alloc_body = self.client.show_network_allocation(found_network["id"])
        self.assertIn("allocation", network_alloc_body)

        network_alloc = network_alloc_body["allocation"]
        self.assertIn("resource_id", network_alloc)
        self.assertIn("reservations", network_alloc)

        # ensure that allocation resource ID == blazar network ID
        # does NOT equal hypervisor_networkname
        self.assertEquals(found_network["id"], network_alloc["resource_id"])

    def test_list_network_properties(self):
        properties = self.client.list_network_properties()
        self.assertIn("resource_properties", properties)
        resource_properties = properties["resource_properties"]
        for p in resource_properties:
            self.assertIn("property", p)
            self.assertNotIn("private", p)
            self.assertNotIn("values", p)
            self.assertNotIn("is_unique", p)
