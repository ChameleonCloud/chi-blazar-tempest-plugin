from tempest.exceptions import BuildErrorException
from tempest.lib import exceptions as lib_exc


class LeaseErrorException(lib_exc.TempestException):
    message = "Lease %(lease_id)s failed to start and is in ERROR status"


class NoValidHostWasFoundException(BuildErrorException):
    """Nova scheduler returns a 500 status code when scheduler returns 0 results.
    When blazar is in-play, there are valid reasons to get this result.
    """

    status_code = 500
    message = "No valid host was found. There are not enough hosts available"
