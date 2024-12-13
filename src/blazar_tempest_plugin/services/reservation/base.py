from urllib import parse as urllib

from oslo_serialization import jsonutils as json
from tempest.lib.common import rest_client


class BaseReservableResourceClient(rest_client.RestClient):
    """Base class for Tempest REST clients for Blazar.

    Implements:
    * list/show/create/update/delete for the resource
    * list/show for allocations for the resource
    * List/update for properties for the resource
    """

    # added as prefix to endpoint
    api_version = "v1"

    def list_resources(self, uri, **filters):
        req_uri = uri
        if filters:
            req_uri += "?" + urllib.urlencode(filters, doseq=1)
        resp, body = self.get(req_uri)
        body = json.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBody(resp, body)

    def delete_resource(self, uri, expect_empty_body=False, expect_response_code=200):
        req_uri = uri
        resp, body = self.delete(req_uri)

        # what we're *supposed* to see is a a body if 200 or 202, and no body if 204
        self.expected_success(expect_response_code, resp.status)

        if not expect_empty_body:
            body = json.loads(body)
        else:
            body = None

        return rest_client.ResponseBody(resp, body)

    def show_resource(self, uri):
        req_uri = uri
        resp, body = self.get(req_uri)
        body = json.loads(body)
        self.expected_success(200, resp.status)
        return rest_client.ResponseBody(resp, body)

    def create_resource(
        self, uri, post_data, expect_empty_body=False, expect_response_code=201
    ):
        req_uri = uri
        req_post_data = json.dumps(post_data)
        resp, body = self.post(req_uri, req_post_data)
        # NOTE: RFC allows both a valid non-empty body and an empty body for
        # response of POST API. If a body is expected not empty, we decode the
        # body. Otherwise we returns the body as it is.
        if not expect_empty_body:
            body = json.loads(body)
        else:
            body = None
        self.expected_success(expect_response_code, resp.status)
        return rest_client.ResponseBody(resp, body)

    def update_resource(
        self, uri, post_data, expect_empty_body=False, expect_response_code=200
    ):
        req_uri = uri
        req_post_data = json.dumps(post_data)
        resp, body = self.put(req_uri, req_post_data)
        # NOTE: RFC allows both a valid non-empty body and an empty body for
        # response of PUT API. If a body is expected not empty, we decode the
        # body. Otherwise we returns the body as it is.
        if not expect_empty_body:
            body = json.loads(body)
        else:
            body = None
        self.expected_success(expect_response_code, resp.status)
        return rest_client.ResponseBody(resp, body)
