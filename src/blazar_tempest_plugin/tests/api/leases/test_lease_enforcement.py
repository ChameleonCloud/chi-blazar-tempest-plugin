from tempest.lib import decorators
from tempest.lib.exceptions import Forbidden

from blazar_tempest_plugin.common import utils
from blazar_tempest_plugin.tests.api.base import ReservationApiTest


class TestLeasesEnforcement(ReservationApiTest):
    @decorators.attr(type=["negative"])
    def test_lease_create_max_duration(self):
        """Try to create a lease that exceeds the enforcement length limit."""
        lease_name = self.get_resource_name("-lease")

        # TODO get max lease duration from config
        end_date = utils.time_offset_to_blazar_string(days=300)

        # Create a lease to start ASAP
        self.assertRaises(
            Forbidden,
            self.create_test_lease,
            lease_name=lease_name,
            start_date="now",
            end_date=end_date,
        )

    @decorators.attr(type=["negative"])
    def test_lease_extend_max_duration(self):
        """Try to create a lease that exceeds the enforcement length limit."""
        lease_name = self.get_resource_name("-lease")

        # TODO get lease update window from config
        end_date = utils.time_offset_to_blazar_string(days=7)
        # Create a lease to start ASAP
        lease = self.create_test_lease(
            name=lease_name,
            start_date="now",
            end_date=end_date,
        )

        # TODO get max lease duration from config
        new_end_date = utils.time_offset_to_blazar_string(days=300)

        self.assertRaises(
            Forbidden,
            self.leases_client.update_lease,
            lease["id"],
            end_date=new_end_date,
        )

    @decorators.attr(type=["negative"])
    def test_lease_update_before_allowed(self):
        """Create a maximum length lease, and try to extend it before it would be allowed."""
        lease_name = self.get_resource_name("-lease")
        end_date = utils.time_offset_to_blazar_string(days=6)
        new_end_date = utils.time_offset_to_blazar_string(days=7)
        # Create a lease to start ASAP
        lease = self.create_test_lease(
            name=lease_name,
            start_date="now",
            end_date=end_date,
        )

        self.assertRaises(
            Forbidden,
            self.leases_client.update_lease,
            lease["id"],
            end_date=new_end_date,
        )
