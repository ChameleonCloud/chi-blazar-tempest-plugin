from tempest.lib import exceptions as lib_exc


class LeaseErrorException(lib_exc.TempestException):
    message = "Lease %(lease_id)s failed to start and is in ERROR status"
