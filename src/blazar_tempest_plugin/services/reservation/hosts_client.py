from tempest.lib import exceptions as lib_exc

from blazar_tempest_plugin.services.reservation import base


class ReservableHostsClient(base.BaseReservableResourceClient):
    host_uri = "/os-hosts"
    host_path_uri = "/os-hosts/%s"

    host_allocations_uri = "/os-hosts/allocations"
    host_allocations_path_uri = "/os-hosts/%s/allocation"

    host_properties_uri = "/os-hosts/properties"
    host_properties_path_uri = "/os-hosts/properties/%s"

    def list_hosts(self):
        return self.list_resources(self.host_uri)

    def show_host(self, host_id):
        uri = self.host_path_uri % host_id
        return self.show_resource(uri)

    def create_host(self):
        raise lib_exc.NotImplemented

    def delete_host(self):
        raise lib_exc.NotImplemented

    def update_host(self):
        raise lib_exc.NotImplemented

    def reallocate_host(self):
        raise lib_exc.NotImplemented

    def list_host_allocations(self):
        return self.list_resources(self.host_allocations_uri)

    def show_host_allocation(self, host_id):
        uri = self.host_allocations_path_uri % host_id
        return self.show_resource(uri)

    def list_host_properties(self, detail=None, all=None):
        kwargs = {}
        if detail:
            kwargs["detail"] = True
        if all:
            kwargs["all"] = True

        return self.list_resources(self.host_properties_uri, **kwargs)

    def update_host_property(self):
        raise lib_exc.NotImplemented
