"""Interactive Zun ``exec`` regression tests (k8s / CHI@Edge).

These drive the *interactive* exec path end to end: the REST handshake
(``interactive=true&run=false``) returns a ``proxy_url``; we connect to that
zun-wsproxy websocket and read the command output. On the k8s driver the command
runs when the websocket connects, so the test reads output without sending
anything on the socket.
"""

import json
import urllib.parse

import websocket

from tempest.lib import decorators

from blazar_tempest_plugin.common import utils
from blazar_tempest_plugin.tests.api.base import ContainerApiBase


# k8s remotecommand channel bytes (mirror zun/websocket/k8s_remotecommand.py).
# A correctly demultiplexing proxy strips these before forwarding to the client.
STDOUT_CHANNEL = b"\x01"
STDERR_CHANNEL = b"\x02"
ERROR_CHANNEL = b"\x03"

# Bound a single probe so a session that never closes cannot hang the suite.
WS_READ_TIMEOUT = 30


class TestReservationContainerExecInteractive(ContainerApiBase):
    """Assert the interactive exec websocket stream is cleanly demultiplexed."""

    def setUp(self):
        super(TestReservationContainerExecInteractive, self).setUp()
        self.lease = self._reserve_device()
        hints = {"reservation": utils.get_device_reservation_from_lease(self.lease)}
        # Long sleep so the container outlives the exec session plus the
        # ~330 KB large-output probe.
        self.container = self._create_reserved_container(
            "exec-ws-container", hints, sleep=600
        )

    def _run_exec_probe(self, command):
        """Handshake, connect to the proxy websocket, drain and return bytes."""
        query = urllib.parse.urlencode(
            {"command": command, "interactive": "true", "run": "false"}
        )
        url = f"/containers/{self.container.uuid}/execute?{query}"
        resp, result = self.container_client.post(url, body=None)
        self.assertEqual(200, resp.status)
        proxy_url = json.loads(result.decode("utf-8"))["proxy_url"]

        # Omit the Origin header: the proxy treats a missing Origin as a
        # non-browser client and skips the allowed-origins check
        # (zun/websocket/websocketproxy.py _verify_origin). Token/uuid/exec_id
        # ride in proxy_url's query string, so no extra auth frame is needed.
        # skip_utf8_validation: don't let the client lib touch the UTF-8 bytes
        # the utf8 probe checks.
        ws = websocket.create_connection(
            proxy_url,
            skip_utf8_validation=True,
            subprotocols=["binary", "base64"],
            timeout=WS_READ_TIMEOUT,
        )
        chunks = []
        try:
            while True:
                frame = ws.recv()
                if not frame:
                    break
                if isinstance(frame, str):
                    frame = frame.encode("utf-8")
                chunks.append(frame)
        except websocket.WebSocketConnectionClosedException:
            pass
        finally:
            ws.close()
        return b"".join(chunks)

    def _assert_no_channel_bytes(self, raw):
        self.assertEqual(0, raw.count(STDOUT_CHANNEL), "stdout byte ^A leaked")
        self.assertEqual(0, raw.count(STDERR_CHANNEL), "stderr byte ^B leaked")
        self.assertEqual(0, raw.count(ERROR_CHANNEL), "error byte ^C leaked")

    @decorators.attr(type="smoke")
    def test_exec_ws_no_channel_byte_leak(self):
        """A short command's output carries no channel-marker bytes."""
        raw = self._run_exec_probe("printf ZUNSTRESSOK")
        self._assert_no_channel_bytes(raw)
        self.assertIn(b"ZUNSTRESSOK", raw)

    @decorators.attr(type="smoke")
    def test_exec_ws_large_output_clean(self):
        """Large output (many frames) carries no leaked channel bytes."""
        raw = self._run_exec_probe("seq 1 50000")
        # One stdout channel byte would leak per frame if the demux regressed.
        self.assertEqual(0, raw.count(STDOUT_CHANNEL), "stdout byte leaked")
        self.assertGreater(len(raw), 250000)
        self.assertIn(b"50000", raw)

    @decorators.attr(type="smoke")
    def test_exec_ws_exit_status_not_leaked(self):
        """A failing command does not leak the channel-3 exit-status JSON."""
        raw = self._run_exec_probe("/bin/false")
        self.assertNotIn(b'"status"', raw)
        self.assertNotIn(b'"metadata"', raw)
        self.assertEqual(0, raw.count(ERROR_CHANNEL), "error byte ^C leaked")

    @decorators.attr(type="smoke")
    def test_exec_ws_special_chars_roundtrip(self):
        """Shell metacharacters and percent-encoding round-trip verbatim."""
        raw = self._run_exec_probe("echo 'a&b=c%20d;x|z'")
        self.assertIn(b"a&b=c%20d;x|z", raw)

    @decorators.attr(type="smoke")
    def test_exec_ws_utf8_roundtrip(self):
        """Multibyte UTF-8 survives the round-trip intact and decodable."""
        raw = self._run_exec_probe("echo 'café—naïve—Ω—█'")
        expected = "café—naïve—Ω—█".encode("utf-8")
        self.assertIn(expected, raw)
        # Must not raise: no mid-multibyte splits / mangling.
        raw.decode("utf-8")
