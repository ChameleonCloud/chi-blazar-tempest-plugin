from tempest.scenario import manager

from blazar_tempest_plugin.tests.api.base import BaseReservationTest


class BlazarScenarioTest(manager.ScenarioTest, BaseReservationTest):
    credentials = ["primary"]
