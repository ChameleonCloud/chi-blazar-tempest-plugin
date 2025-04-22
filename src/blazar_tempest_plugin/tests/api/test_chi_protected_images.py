"""Tests for chameleon supported images.

TODO: this should be in a different, "chameleon-tempest" repo, rather than
bundled with blazar, but fine for now.
"""

from oslo_log import log as logging
from tempest import config
from tempest.api.image.base import BaseImageTest
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc
from tempest.lib.common.utils import data_utils

CONF = config.CONF
LOG = logging.getLogger(__name__)


class GlanceProtectedImageTest(BaseImageTest):
    """Test that glance protected properties apply."""

    # TODO: enable
    # @classmethod
    # def skip_checks(cls):
    #     super().skip_checks()
    #     if not CONF.image_feature_enabled.protected_properties:
    #         msg = "Glance protected properties not supported"
    #         raise cls.skipException(msg)

    #     if not CONF.image_feature_enabled.protected_properties:
    #         msg = "Glance protected properties not supported"
    #         raise cls.skipException(msg)

    @classmethod
    def setup_clients(cls):
        super(GlanceProtectedImageTest, cls).setup_clients()
        cls.client = cls.os_primary.image_client_v2

    @decorators.attr(type="smoke")
    def test_set_get_protected_property(self):
        """Test protected property config.

        see https://docs.openstack.org/api-ref/image/v2/#create-image

        > Additionally, you may include additional properties specified
          as key:value pairs, where the value must be a string data type.
          Keys are limited to 255 chars in length. Available key names may
          be limited by the cloud's property protection configuration and
          reserved namespaces like os_glance.
        """
        container_format = CONF.image.container_formats[0]
        disk_format = "raw"
        image_name = data_utils.rand_name(
            prefix=CONF.resource_name_prefix, name="image"
        )
        image = self.create_image(
            name=image_name,
            container_format=container_format,
            disk_format=disk_format,
            visibility="private",
        )

        # set a property that shouldn't be protected
        self.client.update_image(
            image["id"], [{"add": "/foo", "value": "bar"}]
        )
        updated_image = self.client.show_image(image["id"])
        self.assertEqual("bar", updated_image["foo"])

        # try to set a protected property
        self.assertRaises(
            lib_exc.Forbidden,
            self.client.update_image,
            image["id"],
            [{"add": "/chameleon-supported", "value": "true"}],
        )
