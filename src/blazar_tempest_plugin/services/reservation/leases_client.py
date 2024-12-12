from tempest.lib import exceptions as lib_exc

from blazar_tempest_plugin.services.reservation import base


class LeasesClient(base.BaseReservableResourceClient):
    lease_uri = "/leases"
    lease_path_uri = "/leases/%s"

    def list_leases(self):
        return self.list_resources(self.lease_uri)

    def show_lease(self, lease_id):
        uri = self.lease_path_uri % lease_id
        return self.show_resource(uri)

    def create_lease(self):
        raise lib_exc.NotImplemented

    def delete_lease(self):
        raise lib_exc.NotImplemented

    def update_lease(self):
        raise lib_exc.NotImplemented
