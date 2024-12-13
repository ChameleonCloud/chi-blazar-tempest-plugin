from tempest.lib.exceptions import NotImplemented

from blazar_tempest_plugin.tests.api.test_networks import TestReservationNetworksApi


class TestReservationNetworksAdminApi(TestReservationNetworksApi):
    credentials = ["primary", "admin"]
