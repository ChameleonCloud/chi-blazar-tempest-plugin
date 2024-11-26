from oslo_config import cfg

service_option = [
    cfg.BoolOpt(
        "blazar", default=True, help="Whether or not blazar is expected to be available"
    ),
]

resource_reservation_group = cfg.OptGroup(
    name="resource_reservation", title="Resource reservation service options"
)

ResourceReservationGroup = [
    cfg.StrOpt(
        "endpoint_type",
        default="publicURL",
        choices=["public", "admin", "internal", "publicURL", "adminURL", "internalURL"],
        help="The endpoint type to use for the resource_reservation service.",
    ),
    cfg.BoolOpt(
        "flavor_instance_plugin",
        default=True,
        help="Whether to test flavor-based instance reservation",
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
]
