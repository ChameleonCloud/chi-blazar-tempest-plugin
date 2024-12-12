from tempest.lib import exceptions as lib_exc

from blazar_tempest_plugin.services.reservation import base


class ReservableNetworksClient(base.BaseReservableResourceClient):
    network_uri = "/networks"
    network_path_uri = "/networks/%s"

    network_allocations_uri = "/networks/allocations"
    network_allocations_path_uri = "/networks/%s/allocation"

    network_properties_uri = "/networks/properties"
    network_properties_path_uri = "/networks/properties/%s"

    def list_networks(self):
        return self.list_resources(self.network_uri)

    def show_network(self, network_id):
        uri = self.network_path_uri % network_id
        return self.show_resource(uri)

    def create_network(self):
        raise lib_exc.NotImplemented

    def delete_network(self):
        raise lib_exc.NotImplemented

    def update_network(self):
        raise lib_exc.NotImplemented

    def list_network_allocations(self):
        return self.list_resources(self.network_allocations_uri)

    def show_network_allocation(self, network_id):
        uri = self.network_allocations_path_uri % network_id
        return self.show_resource(uri)

    def list_network_properties(self, detail=None, all=None):
        kwargs = {}
        if detail:
            kwargs["detail"] = True
        if all:
            kwargs["all"] = True

        return self.list_resources(self.network_properties_uri, **kwargs)

    def update_network_property(self):
        raise lib_exc.NotImplemented
