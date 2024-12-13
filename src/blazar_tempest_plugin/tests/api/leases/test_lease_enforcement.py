from oslo_serialization import jsonutils as json
from tempest.lib import decorators
from tempest.lib.exceptions import Forbidden, NotFound

from blazar_tempest_plugin.tests.api.base import ReservationApiTest


class TestLeasesEnforcement(ReservationApiTest):
    @decorators.attr(type=["negative"])
    def test_lease_create_max_duration(self):
        """Try to create a lease that exceeds the enforcement length limit."""
        lease_name = self._get_name_prefix("-lease")

        # TODO get max lease duration from config
        end_date = self._get_blazar_time_offset(days=300)

        # Create a lease to start ASAP
        self.assertRaises(
            Forbidden,
            self.leases_client.create_lease,
            name=lease_name,
            start_date="now",
            end_date=end_date,
        )

    @decorators.attr(type=["negative"])
    def test_lease_extend_max_duration(self):
        """Try to create a lease that exceeds the enforcement length limit."""
        lease_name = self._get_name_prefix("-lease")

        # TODO get lease update window from config
        end_date = self._get_blazar_time_offset(days=7)
        # Create a lease to start ASAP
        lease = self.create_test_lease(
            name=lease_name,
            start_date="now",
            end_date=end_date,
        )

        # TODO get max lease duration from config
        new_end_date = self._get_blazar_time_offset(days=300)

        self.assertRaises(
            Forbidden,
            self.leases_client.update_lease,
            lease["id"],
            end_date=new_end_date,
        )

    @decorators.attr(type=["negative"])
    def test_lease_update_before_allowed(self):
        """Create a maximum length lease, and try to extend it before it would be allowed."""
        lease_name = self._get_name_prefix("-lease")
        end_date = self._get_blazar_time_offset(days=6)
        new_end_date = self._get_blazar_time_offset(days=7)
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
