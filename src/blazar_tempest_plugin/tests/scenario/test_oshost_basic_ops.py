import copy
import json
import time

from oslo_log import log as logging
from tempest import config
from tempest.lib import decorators

from blazar_tempest_plugin.common import exceptions, waiters
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

    @classmethod
    def skip_checks(cls):
        super().skip_checks()
        if not CONF.service_available.ironic:
            skip_msg = "Ironic service is not available"
            raise cls.skipException(skip_msg)

    @decorators.attr(type="smoke")
    @decorators.attr(type="slow")
    def test_reservable_server_basic_ops(self):
        lease = self._reserve_physical_host()

        reserved_hosts = self._get_reserved_hosts(lease)
        LOG.info(f"got reserved_hosts {reserved_hosts}")

        reservation_id = self._get_host_reservation(lease)
        LOG.info(f"got reservation id {reservation_id}")

        keypair = self.create_keypair()
        self.instance = self.create_server(
            keypair=keypair,
            wait_until="SSHABLE",
            scheduler_hints={"reservation": reservation_id},
            flavor=CONF.reservation.reservable_flavor_ref,
        )


class TestReservableBaremetalNodeNegative(ReservationScenarioTest):
    credentials = ["primary", "alt"]

    CHI_NO_VALID_HOST_MSG = "No valid host was found. There are not enough hosts available. To troubleshoot, please see bit.ly/faq-instance-failure"
    UPSTREAM_NO_VALID_HOST_MSG = "No valid host was found. "

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.alt_leases_client = cls.os_alt.reservation.LeasesClient()

    def _launch_instance_with_reservation(
        self,
        reservation_id=None,
        **kwargs,
    ):
        launch_kwargs = copy.deepcopy(kwargs)
        launch_kwargs.setdefault("flavor", CONF.reservation.reservable_flavor_ref)
        if reservation_id:
            launch_kwargs["scheduler_hints"] = {"reservation": reservation_id}

        instance = self.create_server(**launch_kwargs)
        return instance

    @decorators.attr(type="negative")
    def test_server_no_hint(self):
        """If configured, ensure instances cannot be launched without a reservation."""

        # self.assertRaises(
        #     exceptions.BuildErrorException,
        #     self._launch_instance_with_reservation,
        #     reservation_id=None,
        # )

        # should succeed, but server will move to error state
        server = self._launch_instance_with_reservation(
            validatable=False, wait_until=False
        )

        # wait for the server to either schedule, or move to an error state
        server_wait = waiters._wait_for_server_scheduling(
            self.servers_client, server["id"]
        )
        self.assertIn("status", server_wait)
        self.assertEqual("ERROR", server_wait["status"])
        self.assertIn("fault", server_wait)
        instance_fault = server_wait["fault"]

        # validate that nova returns the expected error code and message for this case
        # we'll need to update this if we improve/change the error messaging
        self.assertIn("code", instance_fault)
        self.assertEqual(500, instance_fault["code"])
        self.assertIn("message", instance_fault)
        self.assertEqual(self.CHI_NO_VALID_HOST_MSG, instance_fault["message"])

    @decorators.attr(type="negative")
    def test_server_invalid_reservation(self):
        """If configured, ensure instances cannot be launched without a reservation."""

        FAKE_RESERVATION_ID = "106bbc8d-f417-44fa-8483-00b51b574a2c"

        # self.assertRaises(
        #     exceptions.BuildErrorException,
        #     self._launch_instance_with_reservation,
        #     reservation_id=FAKE_RESERVATION_ID,
        # )
        server = self._launch_instance_with_reservation(
            validatable=False, wait_until=False, reservation_id=FAKE_RESERVATION_ID
        )

        # wait for the server to either schedule, or move to an error state
        server_wait = waiters._wait_for_server_scheduling(
            self.servers_client, server["id"]
        )
        self.assertIn("status", server_wait)
        self.assertEqual("ERROR", server_wait["status"])
        self.assertIn("fault", server_wait)
        instance_fault = server_wait["fault"]

        # validate that nova returns the expected error code and message for this case
        # we'll need to update this if we improve/change the error messaging
        self.assertIn("code", instance_fault)
        self.assertEqual(500, instance_fault["code"])
        self.assertIn("message", instance_fault)
        self.assertEqual(self.CHI_NO_VALID_HOST_MSG, instance_fault["message"])

    @decorators.attr(type="negative")
    def test_server_other_project_reservation(self):
        lease = self._reserve_physical_host(leases_client=self.alt_leases_client)
        reservation_id = self._get_host_reservation(lease)

        # should fail, launching server from project #1, on lease from project #2
        # self.assertRaises(
        #     exceptions.BuildErrorException,
        #     self._launch_instance_with_reservation,
        #     reservation_id=reservation_id,
        # )

        server = self._launch_instance_with_reservation(
            validatable=False, wait_until=False, reservation_id=reservation_id
        )

        # wait for the server to either schedule, or move to an error state
        server_wait = waiters._wait_for_server_scheduling(
            self.servers_client, server["id"]
        )
        self.assertIn("status", server_wait)
        self.assertEqual("ERROR", server_wait["status"])
        self.assertIn("fault", server_wait)
        instance_fault = server_wait["fault"]

        # validate that nova returns the expected error code and message for this case
        # we'll need to update this if we improve/change the error messaging
        self.assertIn("code", instance_fault)
        self.assertEqual(500, instance_fault["code"])
        self.assertIn("message", instance_fault)
        self.assertEqual(self.CHI_NO_VALID_HOST_MSG, instance_fault["message"])

    @decorators.attr(type="negative")
    def test_two_servers_one_reserved(self):
        lease = self._reserve_physical_host()
        reservation_id = self._get_host_reservation(lease)

        # should succeed
        server1 = self._launch_instance_with_reservation(
            reservation_id=reservation_id,
            validatable=False,
            wait_until=False,
        )

        # should succeed, since we have a reservation
        spawning_server = waiters._wait_for_server_scheduling(
            self.servers_client, server1["id"]
        )
        self.assertIn("status", spawning_server)

        # ensure the spawning server is in a state that consumes placement resoruces
        self.assertIn(spawning_server["status"], ["ACTIVE", "BUILD"])

        # should fail, since we've used the only host in the aggregate.
        # this will return a 202 from nova, because creation succeeds
        # BUT, the server will move to an error state.
        server2 = self._launch_instance_with_reservation(
            reservation_id=reservation_id,
            validatable=False,
            wait_until=False,
        )

        # using this instead of assertRaises so we can validate the fault message
        server2_wait = waiters._wait_for_server_scheduling(
            self.servers_client, server2["id"]
        )
        self.assertIn("status", server2_wait)
        self.assertEqual("ERROR", server2_wait["status"])

        self.assertIn("fault", server2_wait)
        instance_fault = server2_wait["fault"]

        # validate that nova returns the expected error code and message for this case
        # we'll need to update this if we improve/change the error messaging
        self.assertIn("code", instance_fault)
        self.assertEqual(500, instance_fault["code"])
        self.assertIn("message", instance_fault)
        self.assertEqual("No valid host was found. ", instance_fault["message"])
