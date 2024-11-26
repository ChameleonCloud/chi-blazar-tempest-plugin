from http import client as http_client

from oslo_serialization import jsonutils as json
from tempest.lib.common import rest_client


class ReservationClient(rest_client.RestClient):
    """Base Tempest REST client for Blazar API."""

    version = "1"

    lease = "/leases"
    lease_path = "/leases/%s"
    host = "/os-hosts"
    host_path = "/os-hosts/%s"

    def __init__(self, auth_provider, service, region, **kwargs):
        super().__init__(auth_provider, service, region, **kwargs)

    def deserialize(self, object_str):
        """Deserialize a Blazar object."""

        return json.loads(object_str)

    def list_lease(self):
        resp, body = self.get(self.lease)
        self.expected_success(http_client.OK, resp.status)
        return resp, self.deserialize(body)

    def get_lease(self, lease_id):
        resp, body = self.get(self.lease_path % str(lease_id))
        self.expected_success(http_client.OK, resp.status)
        return resp, self.deserialize(body)

    def create_lease(self, body):
        body = json.dump_as_bytes(body)
        resp, body = self.post(self.lease, body=body)
        self.expected_success(http_client.CREATED, resp.status)
        return resp, self.deserialize(body)

    def update_lease(self, lease_id, body):
        body = json.dump_as_bytes(body)
        resp, body = self.put(self.lease_path % str(lease_id), body=body)
        self.expected_success(
            [http_client.ACCEPTED, http_client.NO_CONTENT], resp.status
        )
        return resp, self.deserialize(body)

    def delete_lease(self, lease_id):
        resp, body = self.delete(self.lease_path % str(lease_id))
        self.expected_success(http_client.NO_CONTENT, resp.status)
        return self._response_helper(resp, body)

    def list_host(self):
        resp, body = self.get(self.host)
        self.expected_success(http_client.OK, resp.status)
        return resp, self.deserialize(body)

    def get_host(self, host_id):
        resp, body = self.get(self.host_path % str(host_id))
        self.expected_success(http_client.OK, resp.status)
        return resp, self.deserialize(body)

    def create_host(self, body):
        body = json.dump_as_bytes(body)
        resp, body = self.post(self.host, body=body)
        self.expected_success(http_client.CREATED, resp.status)
        return resp, self.deserialize(body)

    def update_host(self, host_id, body):
        body = json.dump_as_bytes(body)
        resp, body = self.put(self.host_path % str(host_id), body=body)
        self.expected_success(
            [http_client.ACCEPTED, http_client.NO_CONTENT], resp.status
        )
        return resp, self.deserialize(body)

    def delete_host(self, host_id):
        resp, body = self.delete(self.host_path % str(host_id))
        self.expected_success(http_client.NO_CONTENT, resp.status)
        return self._response_helper(resp, body)
