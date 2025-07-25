from keystoneauth1 import loading
from keystoneauth1 import session
from tempest.lib.auth import KeystoneV3AuthProvider
from tempest.lib.auth import KeystoneV3Credentials
from oslo_log import log as logging


LOG = logging.getLogger(__name__)


class KeystoneV3OidcCredentials(KeystoneV3Credentials):

    _EXTRA_ATTRS = [
        "protocol",
        "identity_provider",
        "client_id",
        "client_secret",
        "access_token_type",
        "discovery_endpoint",
    ]

    ATTRIBUTES = KeystoneV3Credentials.ATTRIBUTES + _EXTRA_ATTRS


class KeystoneV3OidcAuthProvider(KeystoneV3AuthProvider):

    def _get_auth(self):
        """Acquire a token through keystoneauth1 v3oidcpassword plugin."""

        # If the credentials do not have any of the extra attributes, fall
        # back to the default v3 password flow.
        if not any(getattr(self.credentials, attr, None) is not None
                   for attr in getattr(self.credentials, '_EXTRA_ATTRS', [])):
            return super()._get_auth()

        LOG.debug("Authenticating with v3oidcpassword flow to %s",
                  self.auth_url)

        loader = loading.get_plugin_loader("v3oidcpassword")
        plugin = loader.load_from_options(
            auth_url=self.auth_url,
            username=self.credentials.username,
            password=self.credentials.password,
            protocol=self.credentials.protocol,
            identity_provider=self.credentials.identity_provider,
            client_id=self.credentials.client_id,
            client_secret=self.credentials.client_secret,
            discovery_endpoint=self.credentials.discovery_endpoint,
            access_token_type=self.credentials.access_token_type,
            project_name=self.credentials.project_name,
            project_id=self.credentials.project_id,
            project_domain_id=self.credentials.project_domain_id,
            project_domain_name=self.credentials.project_domain_name,
        )

        ks_sess = session.Session(
            auth=plugin,
            verify=not self.dscv,
            cert=self.ca_certs,
            timeout=self.http_timeout,
        )

        token = ks_sess.get_token()
        auth_ref = plugin.get_access(ks_sess)

        # Flatten it so tempest _fill_credentials() likes it
        if hasattr(auth_ref, "to_dict"):
            raw = auth_ref.to_dict()
        else:
            raw = auth_ref._data

        t = raw["token"]

        auth_data = {
            "expires_at": t["expires_at"],
            "catalog": t.get("catalog", []),
            "user": t["user"],
        }

        if "project" in t:
            auth_data["project"] = t["project"]
        if "domain" in t:
            auth_data["domain"] = t["domain"]
        if "system" in t:
            auth_data["system"] = t["system"]

        return token, auth_data
