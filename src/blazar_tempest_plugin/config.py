from oslo_config import cfg

blazar_service_option = cfg.BoolOpt(
    "blazar", default=True, help="Whether or not blazar is expected to be available"
)


reservation_group = cfg.OptGroup(
    name="reservation", title="Resource reservation service options"
)

reservation_features_group = cfg.OptGroup(
    name="reservation_feature_enabled",
    title="Enabled features for resource reservation",
)

ReservationGroup = [
    cfg.StrOpt(
        "catalog_type",
        default="reservation",
        help="Catalog type of the reservation service",
    ),
    cfg.StrOpt(
        "endpoint_type",
        default="publicURL",
        choices=["public", "admin", "internal", "publicURL", "adminURL", "internalURL"],
        help="The endpoint type to use for the reservation service.",
    ),
    cfg.IntOpt(
        "lease_interval",
        default=10,
        help="Time in seconds between lease status checks.",
    ),
    cfg.IntOpt(
        "lease_end_timeout",
        default=300,
        help="Timeout in seconds to wait for a lease to finish.",
    ),
    cfg.StrOpt(
        "reservable_flavor_ref",
        help="flavor to use for reservable instances",
    ),
]

ReservationFeaturesGroup = [
    cfg.BoolOpt(
        "flavor_instance_plugin",
        default=True,
        help="Whether to test flavor-based instance reservation",
    ),
    cfg.BoolOpt(
        "floatingip_plugin",
        default=True,
        help="Whether to test floatingip reservation",
    ),
    cfg.BoolOpt(
        "network_plugin",
        default=True,
        help="Whether to test network reservation",
    ),
    cfg.BoolOpt(
        "network_storage_plugin",
        default=True,
        help="Whether to test network_storage reservation",
    ),
    cfg.BoolOpt(
        "device_plugin",
        default=True,
        help="Whether to test device reservation",
    ),
]
