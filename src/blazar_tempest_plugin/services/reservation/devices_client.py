from tempest.lib import exceptions as lib_exc

from blazar_tempest_plugin.services.reservation import base


class ReservableDevicesClient(base.BaseReservableResourceClient):
    device_uri = "/devices"
    device_path_uri = "/devices/%s"

    device_allocations_uri = "/devices/allocations"
    device_allocations_path_uri = "/devices/%s/allocation"

    device_properties_uri = "/devices/properties"
    device_properties_path_uri = "/devices/properties/%s"

    def list_devices(self):
        return self.list_resources(self.device_uri)

    def show_device(self, device_id):
        uri = self.device_path_uri % device_id
        return self.show_resource(uri)

    def create_device(self):
        raise lib_exc.NotImplemented

    def delete_device(self):
        raise lib_exc.NotImplemented

    def update_device(self):
        raise lib_exc.NotImplemented

    def reallocate_device(self):
        raise lib_exc.NotImplemented

    def list_device_allocations(self):
        return self.list_resources(self.device_allocations_uri)

    def show_device_allocation(self, device_id):
        uri = self.device_allocations_path_uri % device_id
        return self.show_resource(uri)

    def list_device_properties(self, detail=None, all=None):
        kwargs = {}
        if detail:
            kwargs["detail"] = True
        if all:
            kwargs["all"] = True

        return self.list_resources(self.device_properties_uri, **kwargs)

    def update_device_property(self):
        raise lib_exc.NotImplemented
