import base64
import io
import json
import tarfile
import urllib.parse

from tempest.lib import exceptions
from tempest.lib import decorators

from blazar_tempest_plugin.common import utils
from blazar_tempest_plugin.tests.api.base import ContainerApiBase
from zun_tempest_plugin.tests.tempest.api.clients import set_container_service_api_microversion


class TestReservationContainerApi(ContainerApiBase):
    """Test containers API on CHI@Edge."""

    def setUp(self):
        super(TestReservationContainerApi, self).setUp()
        self.lease = self._reserve_device()
        self.hints = {"reservation": utils.get_device_reservation_from_lease(self.lease)}
        self.container = self._create_reserved_container("reservation-container", self.hints)
        self.minimum_archive_api_microversion = "1.25"

    @decorators.attr(type="smoke")
    def test_launch_reserved_container(self):
        """Test launching a container."""
        resp, container = self.container_client.get_container(self.container.uuid)
        self.assertEqual("Running", container.status)

    @decorators.attr(type="smoke")
    def test_list_container(self):
        """Test listing containers."""
        resp, containers = self.container_client.list_containers()
        self.assertEqual(200, resp.status)

        data = containers.to_dict()
        for c in data.get('containers', []):
            self.assertIn('uuid', c)
        uuids = [c['uuid'] for c in data['containers']]
        self.assertEqual(len(uuids), len(set(uuids)))
        self.assertEqual(1, len(uuids))
        self.assertIn(self.container.uuid, uuids)

    @decorators.attr(type="smoke")
    def test_delete_container(self):
        """Test deleting a container."""
        del_resp = self.container_client.delete_container(
            self.container.uuid,
            {"stop": True}
        )
        self.assertIn(del_resp[0].status, (202, 204))
        try:
            self.container_client.ensure_container_in_desired_state(
                self.container.uuid, "Deleted"
            )
        except exceptions.NotFound:
            pass

    @decorators.attr(type="smoke")
    def test_get_container_logs(self):
        """Test get logs from a container."""
        resp, logs = self.container_client.get(f"/containers/{self.container.uuid}/logs")
        self.assertEqual(200, resp.status)
        output = logs.decode('utf-8')
        self.assertIn('hello-from-container', output)

    @decorators.attr(type="smoke")
    def test_exec_in_container(self):
        """Test executing a command in a container."""
        query_params = {
            "command": "echo exec-in-container",
            "run": "true",
        }
        query_string = urllib.parse.urlencode(query_params)
        url = f"/containers/{self.container.uuid}/execute?{query_string}"
        resp, result = self.container_client.post(url, body=None)
        output = json.loads(result.decode('utf-8'))
        self.assertEqual(200, resp.status)
        self.assertIn("exec-in-container", output.get("output"))
        self.assertEqual(0, output.get("exit_code"))

    @decorators.attr(type="smoke")
    def test_download_archive(self):
        """Test downloading an archive from a container."""
        query_params = urllib.parse.urlencode({"path": f"/etc"})
        get_url = f"/containers/{self.container.uuid}/get_archive?{query_params}"

        # this is a workaround due to the fact that we set the microversion in the
        # base class for deleting containers, but we need to bump it for archive
        # support. it may be better to drop the version only for delete instead
        set_container_service_api_microversion(self.minimum_archive_api_microversion)
        resp, result = self.container_client.get(get_url)
        set_container_service_api_microversion(self.request_microversion)

        self.assertEqual(200, resp.status)
        archive_data = json.loads(result.decode('utf-8'))["data"]
        tar_bytes = base64.b64decode(archive_data)
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode='r') as tar:
            member = tar.getmember("./hosts")
            extracted = tar.extractfile(member).read().decode('utf-8')

        self.assertIn("# Kubernetes-managed hosts", extracted)
        self.assertIn("localhost", extracted)
        self.assertIn("127.0.0.1", extracted)

    @decorators.attr(type="smoke")
    def test_upload_archive(self):
        """Test uploading an archive to a container."""
        dir_name = "test-dir"
        file_name = f"{dir_name}/test.txt"
        file_data = b"hello from upload"

        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            tarinfo = tarfile.TarInfo(name=file_name)
            tarinfo.size = len(file_data)
            tar.addfile(tarinfo, io.BytesIO(file_data))

        tar_stream.seek(0)
        encoded = base64.b64encode(tar_stream.read()).decode('utf-8')
        query_params = urllib.parse.urlencode({"path": f"/tmp"})
        put_url = f"/containers/{self.container.uuid}/put_archive?{query_params}"
        body = json.dumps({"data": encoded})
        header = {
            "Content-Type": "application/json",
            "OpenStack-API-Version": f"container {self.minimum_archive_api_microversion}",
        }

        # this is a workaround due to the fact that we set the microversion in the
        # base class for deleting containers, but we need to bump it for archive
        # support. it may be better to drop the version only for delete instead
        set_container_service_api_microversion(self.minimum_archive_api_microversion)
        resp, _ = self.container_client.post(put_url, body=body, headers=header)
        set_container_service_api_microversion(self.request_microversion)

        self.assertEqual(200, resp.status)

        # TODO: we need a way to verify the file was uploaded, all my attempts
        # thus far have failed, so this is a placeholder to figure it out
