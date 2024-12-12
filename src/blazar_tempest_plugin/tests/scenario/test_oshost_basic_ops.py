import json
import time

import netaddr
from oslo_log import log as logging
from tempest import config
from tempest.common import compute, waiters
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from tempest.lib.common.utils import data_utils, test_utils

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

        lease = self.get_lease_now(hours=1, reservations=[host_reservation_request])
        self.wait_for_lease_status(lease_id=lease["id"], status="ACTIVE")

        for res in lease["reservations"]:
            if res["resource_type"] == "physical:host":
                return res["id"]

    @decorators.attr(type="smoke")
    def test_reservable_server_basic_ops(self):
        keypair = self.create_keypair()
        reservation_id = self._reserve_physical_host()
        self.instance = self.create_server(
            keypair=keypair,
            wait_until="SSHABLE",
            scheduler_hints={"reservation": reservation_id},
            flavor=CONF.reservation.reservable_flavor_ref,
        )
