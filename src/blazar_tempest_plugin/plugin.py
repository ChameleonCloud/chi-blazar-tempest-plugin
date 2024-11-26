import os

from tempest import config
from tempest.test_discover import plugins

from blazar_tempest_plugin import config as blazar_config


class BlazarTempestPlugin(plugins.TempestPlugin):
    def load_tests(self):
        base_path = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
        test_dir = "blazar_tempest_plugin/tests"
        full_test_dir = os.path.join(base_path, test_dir)
        return full_test_dir, base_path

    def register_opts(self, conf: config.cfg.ConfigOpts):
        conf.register_opt(blazar_config.blazar_service_option, "service_available")
        config.register_opt_group(
            conf,
            blazar_config.reservation_group,
            blazar_config.ReservationGroup,
        )
        config.register_opt_group(
            conf,
            blazar_config.reservation_features_group,
            blazar_config.ReservationFeaturesGroup,
        )

    def get_opt_lists(self):
        return [
            ("service_available", [blazar_config.blazar_service_option]),
            (blazar_config.reservation_group.name, blazar_config.ReservationGroup),
            (
                blazar_config.reservation_features_group.name,
                blazar_config.ReservationFeaturesGroup,
            ),
        ]

    def get_service_clients(self):
        try:
            reservation_config = config.service_client_config("reservation")
        except Exception as ex:
            raise ex
        reservation_client = {
            "name": "reservation",
            "service_version": "reservation.v1",
            "module_path": "blazar_tempest_plugin.services.reservation",
            "client_names": ["ReservationClient"],
        }
        reservation_client.update(reservation_config)

        return [reservation_client]
