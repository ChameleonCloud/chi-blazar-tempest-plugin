import sys

from enum import Enum

from oslo_log import log as logging
from tempest import config
from tempest.common import waiters as tempest_waiters
from tempest.lib import decorators
from tempest.lib import exceptions as tempest_exc
from tempest.lib.common.utils import test_utils

from blazar_tempest_plugin.common import waiters
from blazar_tempest_plugin.common.utils import get_server_floating_ip
from blazar_tempest_plugin.common.utils import should_skip
from blazar_tempest_plugin.common.utils import wait_for_remote_file
from blazar_tempest_plugin.tests.scenario.base import ReservationScenarioTest


CONF = config.CONF
LOG = logging.getLogger(__name__)


class AlertLevel(Enum):
    CRITICAL = 1
    NONCRITICAL = 2


### Tests ###

def verify_cloud_init(self, remote):
    output = remote.exec_command('cloud-init status --wait')
    if "status: done" not in output:
        self.fail(f"cloud-init did not finish properly.\nOutput:\n{output}")

    output = remote.exec_command('cloud-init status --long')
    if "status: done" not in output:
        self.fail(f"cloud-init did not finish properly.\nOutput:\n{output}")


def verify_openrc_exists(self, remote):
    self.assertTrue(
        wait_for_remote_file(remote, CONF.image.cc_image_tests_openrc_path),
        f"{CONF.image.cc_image_tests_openrc_path} did not appear within timeout"
    )


def verify_openrc(self, remote):
    self.assertTrue(
        wait_for_remote_file(remote, CONF.image.cc_image_tests_openrc_path),
        f"{CONF.image.cc_image_tests_openrc_path} did not appear within timeout"
    )
    output = remote.exec_command(
        f'bash -c "source {CONF.image.cc_image_tests_openrc_path} && openstack token issue -f value -c id" || echo FAILED'
    )
    self.assertNotIn("FAILED", output, f"Failed to source {CONF.image.cc_image_tests_openrc_path} or run OpenStack command.")
    self.assertTrue(output.strip(), "OpenStack command produced no output — openrc may not have been sourced correctly.")


def verify_ssh_key_injection(self, remote, public_key):
    output = remote.exec_command('cat /home/cc/.ssh/authorized_keys || echo MISSING')
    self.assertNotIn("MISSING", output, "Could not read /home/cc/.ssh/authorized_keys")

    pubkey_str = public_key.strip()
    auth_keys = output.strip().splitlines()
    self.assertIn(pubkey_str, auth_keys, f"Expected pubkey not found.\nGot:\n{output}")


def verify_rclone_and_object_store(self, remote):
    output = remote.exec_command('which rclone || echo MISSING')
    self.assertNotIn("MISSING", output, "'rclone' was not found on the instance.")

    output = remote.exec_command('which cc-mount-object-store || echo MISSING')
    self.assertNotIn("MISSING", output, "'cc-mount-object-store' not found.")

    output = remote.exec_command('cc-mount-object-store list || echo ERROR')
    self.assertNotIn("ERROR", output, "cc-mount-object-store list returned error.")
    self.assertTrue(output.strip() and not all(c == '.' for c in output.strip()),
                    "'cc-mount-object-store list' output is invalid.")


TESTS = [
    (AlertLevel.CRITICAL, "verify_ssh_key_injection", verify_ssh_key_injection),
    (AlertLevel.CRITICAL, "verify_rclone_and_object_store", verify_rclone_and_object_store),
    (AlertLevel.NONCRITICAL, "verify_cloud_init", verify_cloud_init),
    (AlertLevel.NONCRITICAL, "verify_openrc_exists", verify_openrc_exists),
    (AlertLevel.NONCRITICAL, "verify_openrc", verify_openrc),
]


### Dynamic Test Class Creation ###

def make_image_test_class(image_name):
    """
    Dynamically create a test class for the given image name.

    The classes created by this function will inherit from
    `ReservationScenarioTest` and will include tests for various
    functionalities such as SSH key injection, cloud-init verification,
    and more. Each class will be named `TestImage_<image_name>`, where
    `<image_name>` is the sanitized version of the image name. The
    image name is sanitized by replacing special characters with
    underscores to ensure it is a valid Python class name.

    If there are multiple images with the same name, an exception
    will be raised. If no image is found, an exception will also be
    raised.

    The test methods will be dynamically added to the class based on the
    `TESTS` list defined above, skipping any that should be skipped,
    as specified by the `skip_test_regex` configuration option.

    The class will also include a setup method that creates a server
    using the specified image, and a teardown method that cleans up
    the server and any associated resources.
    """
    safe_name = image_name.replace(":", "_").replace("-", "_").replace(".", "_")
    class_name = f"TestImage_{safe_name}"

    class TestImage(ReservationScenarioTest):
        @classmethod
        def resource_setup(cls):
            super(TestImage, cls).resource_setup()
            inst = cls()
            cls.addClassResourceCleanup(inst.doCleanups)

            resp = cls.image_client.list_images(params={
                'name': image_name,
                'visibility': 'public',
            })
            matching = resp.get('images', [])

            if not matching:
                raise Exception(f"No image found with name: {image_name}")
            if len(matching) > 1:
                raise Exception(f"Multiple images found with name: {image_name}")

            cls.image = matching[0]
            cls.image_id = cls.image['id']
            cls.image_name = image_name

            cls.keypair = inst.create_keypair()
            cls.public_key = cls.keypair["public_key"]
            cls.lease_id = None

            try:
                if CONF.reservation.reservation_required:
                    node_type = None
                    if "ARM64" in cls.image_name:
                        node_type = CONF.reservation.reservable_arm_node_type
                    lease = inst._reserve_physical_host(node_type=node_type)
                    cls.lease_id = lease["id"]
                    reservation_id = inst._get_host_reservation(lease)
                    flavor = CONF.reservation.reservable_flavor_ref
                    scheduler_hints = {"reservation": reservation_id}
                else:
                    flavor = CONF.compute.flavor_ref
                    scheduler_hints = {}

                boot_kwargs = {
                    "image_id": cls.image_id,
                    "keypair": cls.keypair,
                    "wait_until": "SSHABLE",
                    "flavor": flavor,
                }
                if scheduler_hints:
                    boot_kwargs["scheduler_hints"] = scheduler_hints

                server = inst.create_server(**boot_kwargs)
                cls.server_id = server["id"]
                # refresh server details to get security groups and floating IP
                server = cls.servers_client.show_server(cls.server_id)["server"]
                cls._created_sg_names = []
                for sg in server.get("security_groups", []):
                    name = sg.get("name")
                    if name != "default":
                        cls._created_sg_names.append(name)
                cls.fip = get_server_floating_ip(server)
                cls.remote = cls.get_remote_client(cls, cls.fip)

            except Exception:
                if cls.lease_id:
                    test_utils.call_and_ignore_notfound_exc(
                        cls.leases_client.delete_lease, cls.lease_id
                    )
                raise

        @classmethod
        def resource_cleanup(cls):
            try:
                if hasattr(cls, "server_id"):
                    cls.servers_client.delete_server(cls.server_id)
                    tempest_waiters.wait_for_server_termination(cls.servers_client, cls.server_id)

                if getattr(cls, "lease_id", None):
                    try:
                        test_utils.call_and_ignore_notfound_exc(
                            cls.leases_client.delete_lease, cls.lease_id
                        )
                        waiters.wait_for_lease_status(
                            cls.leases_client, cls.lease_id, "TERMINATED"
                        )
                    except tempest_exc.NotFound:
                        pass

                if hasattr(cls, "fip"):
                    try:
                        floating_ips = cls.floating_ips_client.list_floatingips()['floatingips']
                        matching = [fip for fip in floating_ips if fip['floating_ip_address'] == cls.fip]
                        if matching:
                            cls.floating_ips_client.delete_floatingip(matching[0]['id'])
                    except tempest_exc.NotFound:
                        pass

                if hasattr(cls, "keypair"):
                    try:
                        cls.keypairs_client.delete_keypair(cls.keypair["name"])
                    except tempest_exc.NotFound:
                        pass

                for name in getattr(cls, "_created_sg_names", []):
                    sgs = cls.security_groups_client.list_security_groups(
                        name=name
                    )['security_groups']
                    for sg in sgs:
                        sg_id = sg['id']
                        try:
                            cls.security_groups_client.delete_security_group(sg_id)
                        except tempest_exc.NotFound:
                            pass
            finally:
                super(TestImage, cls).resource_cleanup()

    for alert_level, test_name, test_func in TESTS:
        def make_test(alert_level, test_name, test_func):
            def test_fn(self):
                if should_skip(test_name, CONF.image.cc_image_tests_skip_test_regex):
                    self.skipTest(f"{test_name} skipped")
                if test_name == "verify_ssh_key_injection":
                    test_func(self, type(self).remote, type(self).public_key)
                else:
                    test_func(self, type(self).remote)
            test_fn.__name__ = f"test_{test_name}"
            test_fn.__qualname__ = f"{class_name}.{test_fn.__name__}"
            test_fn.__module__ = __name__

            # annotate test with multiple types for filtering
            test_attr_type = [
                "slow",
                alert_level.lower(),
            ]
            decorated_test_fn = decorators.attr(type=test_attr_type)(test_fn)
            return decorated_test_fn

        test_method = make_test(alert_level.name, test_name, test_func)
        setattr(TestImage, test_method.__name__, test_method)

    TestImage.__name__ = class_name
    TestImage.__qualname__ = class_name
    return TestImage


def generate_tests():
    """Dynamically generate test classes for images listed in the config."""

    created_classes = set()
    module = sys.modules[__name__]

    for image_name in getattr(CONF.image, "cc_image_tests_image_names", []):
        image_name = image_name.strip()
        if image_name in created_classes:
            LOG.warning(f"Skipping duplicate image_name in config: {image_name}")
            continue

        test_cls = make_image_test_class(image_name)
        setattr(module, test_cls.__name__, test_cls)
        created_classes.add(image_name)


if not globals().get("__image_tests_generated__"):
    # Ensure tests are generated only once and not multiple times
    # due to tempest potentially importing this module multiple times
    generate_tests()
    __image_tests_generated__ = True
