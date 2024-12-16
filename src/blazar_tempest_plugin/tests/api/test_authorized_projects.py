"""Test cases for chi / blazar authorized projects feature."""

from tempest.lib import decorators
from tempest.lib.exceptions import Forbidden

from blazar_tempest_plugin.tests.api.base import ReservationApiTest


class TestAuthorizedProjectDevice(ReservationApiTest):
    """TODO: Create Device with authorized_projects set to project #1, read with project #2."""

    @classmethod
    def resource_setup(cls):
        super().resource_setup()
        # TODO use admin-api to create resource for testing

    # def test_reserve_device_authorized(self):
    #     pass

    # @decorators.attr(type=["negative"])
    # def test_reserve_device_unauthorized(self):
    #     pass
    #     # self.assertRaises(Forbidden, self.reserve_device, self.test_device)


class TestAuthorizedProjectHost(ReservationApiTest):
    """TODO: Create host with authorized_projects set to project #1, read with project #2."""

    @classmethod
    def resource_setup(cls):
        super().resource_setup()
        # TODO use admin-api to create resource for testing

    # def test_reserve_host_authorized(self):
    #     pass

    # @decorators.attr(type=["negative"])
    # def test_reserve_host_unauthorized(self):
    #     pass
    #     # self.assertRaises(Forbidden, self.reserve_host, self.test_host)
