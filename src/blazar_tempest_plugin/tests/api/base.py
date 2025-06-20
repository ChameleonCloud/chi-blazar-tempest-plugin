from oslo_log import log as logging
from tempest import config, test
from tempest.lib.common.utils import data_utils, test_utils

from blazar_tempest_plugin.common import utils, waiters

from zun_tempest_plugin.tests.tempest.api.clients import (
    ZunClient,
    set_container_service_api_microversion,
)
from zun_tempest_plugin.tests.tempest.api.common import datagen


CONF = config.CONF
LOG = logging.getLogger(__name__)


class ReservationApiTest(test.BaseTestCase):
    credentials = ["primary"]

    @classmethod
    def skip_checks(cls):
        super(ReservationApiTest, cls).skip_checks()
        if not CONF.service_available.blazar:
            skip_msg = "Blazar is disabled"
            raise cls.skipException(skip_msg)

    @classmethod
    def setup_credentials(cls):
        cls.set_network_resources()
        super(ReservationApiTest, cls).setup_credentials()

    @classmethod
    def setup_clients(cls):
        super(ReservationApiTest, cls).setup_clients()
        cls.leases_client = cls.os_primary.reservation.LeasesClient()

    @classmethod
    def create_test_lease(cls, lease_name=None, **kwargs):
        """Create a test lease with sane defaults for name and dates.
        Lease will be in the far future to ensure no conflicts."""

        if not lease_name:
            lease_name = data_utils.rand_name(
                prefix=CONF.resource_name_prefix,
                name=__name__ + "-lease",
            )

        kwargs.setdefault("name", lease_name)
        kwargs.setdefault("start_date", "2050-12-26 12:00")
        kwargs.setdefault("end_date", "2050-12-27 12:00")

        lease_body = cls.leases_client.create_lease(**kwargs)
        lease = lease_body["lease"]

        cls.addClassResourceCleanup(
            test_utils.call_and_ignore_notfound_exc,
            cls.leases_client.delete_lease,
            lease["id"],
        )
        return lease

    @classmethod
    def get_resource_name(cls, prefix):
        return data_utils.rand_name(
            prefix=CONF.resource_name_prefix,
            name=cls.__name__ + prefix,
        )


class ContainerApiBase(ReservationApiTest):
    """Base class for container API tests."""

    @classmethod
    def skip_checks(cls):
        super(ContainerApiBase, cls).skip_checks()
        if not CONF.service_available.zun:
            raise cls.skipException("Zun service is not available.")

    @classmethod
    def setup_clients(cls):
        super(ContainerApiBase, cls).setup_clients()
        cls.floating_ips_client = cls.os_primary.floating_ips_client
        cls.container_client = ZunClient(cls.os_primary.auth_provider)
        cls.request_microversion = CONF.container_service.min_microversion
        set_container_service_api_microversion(cls.request_microversion)

    def _create_container(self, desired_state="Running", **kwargs):
        gen_model = datagen.container_data(default_data={}, **kwargs)
        resp, model = self.container_client.post_container(gen_model)

        self.addCleanup(
            test_utils.call_and_ignore_notfound_exc,
            self.container_client.delete_container,
            model.uuid,
            {"stop": True},
        )

        self.assertEqual(202, resp.status)
        self.container_client.ensure_container_in_desired_state(model.uuid, desired_state)
        return resp, model

    def _reserve_device(
            self,
            lease_status="ACTIVE",
            start_date="now",
            end_date=utils.time_offset_to_blazar_string(hours=1),
            leases_client=None
        ):
        """Reserve a device for testing."""
        if not leases_client:
            leases_client = self.leases_client

        device_reservation_request = {
            "resource_type": "device",
            "min": "1",
            "max": "1",
            "resource_properties": '["==", "$machine_name", "raspberrypi4-64"]',
        }

        lease = self.create_test_lease(
            start_date=start_date,
            end_date=end_date,
            reservations=[device_reservation_request],
        )

        final_lease = waiters.wait_for_lease_status(
            leases_client, lease["id"], lease_status
        )

        return final_lease

    def _create_reserved_container(self, name, hints, desired_state="Running"):
        _, container = self._create_container(
            desired_state=desired_state,
            name=data_utils.rand_name(name),
            hints=hints,
            image="busybox",
            command="/bin/sh -c 'echo hello-from-container && sleep 60'",
        )
        return container
