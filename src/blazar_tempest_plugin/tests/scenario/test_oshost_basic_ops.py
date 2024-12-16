import json

from oslo_log import log as logging
from tempest import config
from tempest.lib import decorators

from blazar_tempest_plugin.common import exceptions, utils, waiters
from blazar_tempest_plugin.tests.scenario.base import ReservationScenarioTest

CONF = config.CONF
LOG = logging.getLogger(__name__)


def pp(data):
    print(json.dumps(data, indent=2))


class TestReservableBaremetalNode(ReservationScenarioTest):
    """Basic existence test, we will test the following

    1. make a reservation for any one baremetal host
    2. wait for it to start
    3. create an instance using the reservation
    4. ensure we can ssh to it using a floating ip
    5. verify the contents of the vendordata endpoint

    Much of the logic is copied from tempest.scenario.test_server_basic_ops
    """

    def _reserve_physical_host(self):
        """Create a lease for a physical host and wait for it to become active.
        Returns the reservation to be used for scheduling.
        """

        host_reservation_request = {
            "min": "1",
            "max": "1",
            "resource_type": "physical:host",
            "hypervisor_properties": "",
            "resource_properties": "",
        }

        end_date = utils.time_offset_to_blazar_string(hours=1)
        lease = self.create_test_lease(
            start_date="now",
            end_date=end_date,
            reservations=[host_reservation_request],
        )

        active_lease = waiters.wait_for_lease_status(
            self.leases_client, lease["id"], "ACTIVE"
        )

        return active_lease

    def _get_host_reservation(self, lease):
        for res in lease["reservations"]:
            if res["resource_type"] == "physical:host":
                return res["id"]

    @decorators.attr(type="smoke")
    @decorators.attr(type="slow")
    def test_reservable_server_basic_ops(self):
        lease = self._reserve_physical_host()
        reservation_id = self._get_host_reservation(lease)
        LOG.debug(f"got reservation id {reservation_id}")

        keypair = self.create_keypair()
        self.instance = self.create_server(
            keypair=keypair,
            wait_until="SSHABLE",
            scheduler_hints={"reservation": reservation_id},
            flavor=CONF.reservation.reservable_flavor_ref,
        )
