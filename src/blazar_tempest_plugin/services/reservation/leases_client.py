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

    def create_lease(self, **kwargs):
        post_body = {**kwargs}

        return self.create_resource(self.lease_uri, post_body)

    def delete_lease(self, lease_id):
        uri = self.lease_path_uri % lease_id
        return self.delete_resource(
            uri,
            expect_empty_body=False,
            expect_response_code=200,
        )

    def update_lease(self, lease_id, **kwargs):
        uri = self.lease_path_uri % lease_id
        update_body = {**kwargs}
        return self.update_resource(uri, update_body)
