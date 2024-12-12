from tempest.lib import exceptions as lib_exc

from blazar_tempest_plugin.services.reservation import base


class ReservableFloatingIPsClient(base.BaseReservableResourceClient):
    floatingip_uri = "/floatingips"
    floatingip_path_uri = "/floatingips/%s"

    def list_floatingips(self):
        return self.list_resources(self.floatingip_uri)

    def show_floatingip(self, floatingip_id):
        uri = self.floatingip_path_uri % floatingip_id
        return self.show_resource(uri)

    def create_floatingip(self):
        raise lib_exc.NotImplemented

    def delete_floatingip(self):
        raise lib_exc.NotImplemented
