import urllib.request

from oslo_log import log as logging
import tempest.test
from tempest import config
from tempest.lib import decorators
from tempest.lib.common.utils import data_utils, test_utils
from tempest.lib.services.identity.v3 import token_client as v3_token

CONF = config.CONF
LOG = logging.getLogger(__name__)


class TestAppCredentialImplicitRoles(tempest.test.BaseTestCase):
    """Regression test for LP#2030061.

    Keystone application credentials don't inherit implicit roles.
    Our policy fix adds explicit ``role:member`` alongside ``role:reader``
    in Nova and Glance policies. This test creates an app credential with
    only the ``member`` role and verifies that read-only Nova/Glance API
    calls succeed (they would 403 without the policy fix).
    """

    credentials = ["primary"]

    @classmethod
    def setup_credentials(cls):
        cls.set_network_resources()
        super().setup_credentials()

    @classmethod
    def skip_checks(cls):
        super().skip_checks()
        if not CONF.service_available.glance:
            raise cls.skipException("Glance service is not available.")
        if not CONF.service_available.nova:
            raise cls.skipException("Nova service is not available.")

    @classmethod
    def setup_clients(cls):
        super().setup_clients()
        cls.app_creds_client = cls.os_primary.application_credentials_client
        cls.user_id = cls.os_primary.credentials.user_id
        cls.project_id = cls.os_primary.credentials.project_id

    @classmethod
    def resource_setup(cls):
        super().resource_setup()

        app_cred = cls.app_creds_client.create_application_credential(
            cls.user_id,
            name=data_utils.rand_name(
                prefix=CONF.resource_name_prefix,
                name="app-cred-implicit-role",
            ),
            roles=[{"name": "member"}],
        )["application_credential"]

        cls.addClassResourceCleanup(
            test_utils.call_and_ignore_notfound_exc,
            cls.app_creds_client.delete_application_credential,
            cls.user_id,
            app_cred["id"],
        )

        auth_url = CONF.identity.uri_v3
        token_client = v3_token.V3TokenClient(auth_url)
        token, token_data = token_client.get_token(
            app_cred_id=app_cred["id"],
            app_cred_secret=app_cred["secret"],
            auth_data=True,
        )
        cls.app_cred_token = token
        cls.service_catalog = token_data["catalog"]

    @classmethod
    def _endpoint_for(cls, service_type):
        for entry in cls.service_catalog:
            if entry["type"] == service_type:
                for ep in entry["endpoints"]:
                    if ep["interface"] == "public":
                        return ep["url"]
        raise Exception(f"No public endpoint found for {service_type}")

    def _get(self, url):
        req = urllib.request.Request(url, headers={
            "X-Auth-Token": self.app_cred_token,
        })
        resp = urllib.request.urlopen(req)
        return resp.status

    @decorators.attr(type="smoke")
    def test_list_servers(self):
        url = f"{self._endpoint_for('compute')}/servers"
        self.assertEqual(200, self._get(url))

    @decorators.attr(type="smoke")
    def test_list_images(self):
        url = f"{self._endpoint_for('image')}/v2/images"
        self.assertEqual(200, self._get(url))
