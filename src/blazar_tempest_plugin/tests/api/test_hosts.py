from oslo_serialization import jsonutils as json
from tempest.lib import exceptions as lib_exc
from tempest.lib.common import rest_client

from blazar_tempest_plugin.services.reservation.hosts_client import (
    ReservableHostsClient,
)
from blazar_tempest_plugin.tests.api.base import ReservationApiTest


def _pp(data):
    print(json.dumps(data, indent=2))


class TestReservationHostsApi(ReservationApiTest):
    """Non admin tests for API! That means that these are read-only."""

    @classmethod
    def setup_clients(cls):
        super().setup_clients()

        cls.client: ReservableHostsClient
        cls.client = cls.os_primary.reservation.ReservableHostsClient()

    def test_list_hosts(self):
        hosts = self.client.list_hosts()
        self.assertIn("hosts", hosts)

    def test_show_host(self):
        """We can't create a host without admin api, so can't guarantee this test."""

        hosts: rest_client.ResponseBody
        hosts = self.client.list_hosts()["hosts"]

        if not hosts:
            raise lib_exc.InvalidConfiguration("no hosts available, cannot show.")

        found_host = hosts[0]
        host = self.client.show_host(host_id=found_host["id"])

    def test_list_host_allocations(self):
        hosts = self.client.list_hosts()["hosts"]
        if not hosts:
            raise lib_exc.InvalidConfiguration("no hosts available, cannot show.")

        allocations = self.client.list_host_allocations()
        self.assertIn("allocations", allocations)

    def test_show_host_allocation(self):
        hosts = self.client.list_hosts()["hosts"]
        if not hosts:
            raise lib_exc.InvalidConfiguration("no hosts available, cannot show.")

        found_host = hosts[0]

        host_alloc_body = self.client.show_host_allocation(found_host["id"])
        self.assertIn("allocation", host_alloc_body)

        host_alloc = host_alloc_body["allocation"]
        self.assertIn("resource_id", host_alloc)
        self.assertIn("reservations", host_alloc)

        # ensure that allocation resource ID == blazar host ID
        # does NOT equal hypervisor_hostname
        self.assertEqual(found_host["id"], host_alloc["resource_id"])

    def test_list_host_properties(self):
        properties = self.client.list_host_properties()
        self.assertIn("resource_properties", properties)
        resource_properties = properties["resource_properties"]
        for p in resource_properties:
            self.assertIn("property", p)
            self.assertNotIn("private", p)
            self.assertNotIn("values", p)
            self.assertNotIn("is_unique", p)

        properties = self.client.list_host_properties(detail=True)
        self.assertIn("resource_properties", properties)
        resource_properties = properties["resource_properties"]
        for p in resource_properties:
            self.assertIn("property", p)
            self.assertIn("private", p)
            self.assertIn("values", p)
            self.assertIn("is_unique", p)

        properties = self.client.list_host_properties(all=True)
        self.assertIn("resource_properties", properties)
        resource_properties = properties["resource_properties"]
        for p in resource_properties:
            self.assertIn("property", p)
            self.assertNotIn("private", p)
            self.assertNotIn("values", p)
            self.assertNotIn("is_unique", p)
