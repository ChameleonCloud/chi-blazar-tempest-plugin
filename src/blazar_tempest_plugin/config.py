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
    cfg.BoolOpt(
        "reservation_required",
        default=True,
        help="If False, run tests on on-demand KVM and skip all Blazar reservations.",
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

image_group = cfg.OptGroup(
    name="image",
    title="Enabled image service features",
)

ImageGroup = [
    cfg.ListOpt(
        "image_protected_properties",
        default=[],
        help=("A list of keys for which glance property protection is enabled."),
    ),
    cfg.ListOpt(
        "image_names",
        default=[],
        help=("A comma-separated list of image names to test (e.g. CC-Ubuntu24.04,CC-Ubuntu22.04)."),
    ),
    cfg.StrOpt(
        "skip_test_regex",
        default='',
        help=("Regex for test method names to skip during image tests (e.g. verify_rclone_and_object_store|verify_openrc)."),
    ),
    cfg.StrOpt(
        "openrc_path",
        default="/home/cc/openrc",
        help="Path to the openrc file on the server used in image tests.",
    ),
]
