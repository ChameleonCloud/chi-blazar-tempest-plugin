from tempest.lib.services import clients
from tempest.test_discover import plugins
from tempest.tests import base
from tempest.tests.lib.services import registry_fixture

from blazar_tempest_plugin.plugin import BlazarTempestPlugin


class FakeBlazarPluginObj(object):
    obj = BlazarTempestPlugin()

    @property
    def name(self):
        return self._name

    def __init__(self, name="BlazarTest1"):
        self._name = name


class TestPluginDiscovery(base.TestCase):
    def setUp(self):
        super(TestPluginDiscovery, self).setUp()
        # Make sure we leave the registry clean
        self.useFixture(registry_fixture.RegistryFixture())

    def test_load_blazar_client(self):
        registry = clients.ClientsRegistry()
        manager = plugins.TempestTestPluginManager()
        manager._register_service_clients()

        registered_clients = registry.get_service_clients()
        self.assertIn("blazar_tempest_plugin", registered_clients)

        plugin_client = registered_clients["blazar_tempest_plugin"][0]
        self.assertEqual("reservation", plugin_client.get("name"))
