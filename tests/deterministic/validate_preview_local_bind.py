"""The loopback preview must bind and serve without a reverse-DNS lookup."""

from functools import partial
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest.mock import patch
from urllib.request import urlopen

from web_view.url_fallback import _FallbackHTTPServer


def main():
    with TemporaryDirectory() as directory:
        Path(directory, "index.html").write_text("preview ready", encoding="utf-8")
        handler = partial(SimpleHTTPRequestHandler, directory=directory)
        with patch("socket.getfqdn", side_effect=AssertionError("Loopback preview must not query DNS")):
            with _FallbackHTTPServer(("127.0.0.1", 0), handler) as server:
                assert server.server_name == "127.0.0.1"
                assert server.server_port == server.server_address[1]
                worker = Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    with urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=5) as response:
                        assert response.read() == b"preview ready"
                finally:
                    server.shutdown()
                    worker.join(timeout=5)
    print("Loopback preview HTTP works without DNS.")


if __name__ == "__main__":
    main()
