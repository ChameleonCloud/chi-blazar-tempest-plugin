from datetime import datetime, timedelta, timezone
from typing import Optional

from tempest import config

CONF = config.CONF


def time_offset_to_blazar_string(time_now: Optional[datetime] = None, **kwargs) -> str:
    """Specify offset from now (or time_now), and return blazar formatted string representation."""

    if not time_now:
        time_now = datetime.now(timezone.utc)

    time_offset = time_now + timedelta(**kwargs)
    return time_offset.strftime("%Y-%m-%d %H:%M")


# def _get_time_now() -> datetime:
#     time_now = datetime.now(timezone.utc)
#     return time_now


# def _blazar_time_req_from_output(cls, iso8601_timestring: str):
#     """Convert openstack standard datetime string to blazar request format."""
#     result = datetime.fromisoformat(iso8601_timestring)
#     output_string = result.strftime("%Y-%m-%d %H:%M")
#     return output_string


# def _blazar_time_req_to_iso8601(cls, date_string: str):
#     parsed_datetime = datetime.strptime(date_string, "%Y-%m-%d %H:%M")
#     return parsed_datetime.isoformat(timespec="microseconds")
