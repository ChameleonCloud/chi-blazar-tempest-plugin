from tempest.lib import auth as _tl_auth

from .auth.oidc_provider import (
    KeystoneV3OidcAuthProvider,
    KeystoneV3OidcCredentials,
)

# Monkey patch the new identity version so tempest will pick it up
_tl_auth.IDENTITY_VERSION["v3"] = (
    KeystoneV3OidcCredentials,
    KeystoneV3OidcAuthProvider,
)
