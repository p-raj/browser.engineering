from dataclasses import dataclass
import pytest
import socket
import ssl


@dataclass
class HTTPResponse:
    status_code: int
    status_text: str
    headers: dict
    body: str


class URL:
    def __init__(self, url: str):
        self.schema = url.split("://")[0]
        if self.schema not in ["http", "https"]:
            raise ValueError("Schema must be http or https")
        if not url.endswith("/"):
            url += "/"
        self.host = url.split("://")[1].split("/")[0]
        if ":" in self.host:
            self.port = self.host.split(":")[1]
            self.host = self.host.split(":")[0]
        else:
            self.port = 80 if self.schema == "http" else 443
        self.path = url.split("://")[1].split("/")[1:]
        self.path = [p for p in self.path if p != ""]

    def connect(self, secure=False):
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        if secure:
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)
        s.connect((self.host, self.port))
        return s

    def default_request_headers(self):
        return {
            "Host": self.host,
            "Connection": "close",
        }

    def get(self):
        s = self.connect(secure=True if self.schema == "https" else False)
        packet = (
            f"GET /{'/'.join(self.path)} HTTP/1.1\r\n"
            + "\r\n".join(
                [f"{k}: {v}" for k, v in self.default_request_headers().items()]
            )
            + "\r\n\r\n"
        )
        s.send(packet.encode("utf-8"))
        response = s.makefile("r", encoding="utf-8", newline="\r\n")
        status = response.readline()
        # 2 means split only 2 times
        # HTTP/1.1 200 OK => HTTP/1.1, 200, OK
        _, status_code, status_text = status.split(" ", 2)
        status_text = status_text.rstrip("\r\n")
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        body = response.read()
        s.close()
        return HTTPResponse(
            status_code=int(status_code),
            status_text=status_text,
            headers=response_headers,
            body=body,
        )

    def extract_text_from_html(self, html: str):
        in_tag = False
        text = ""
        while html:
            if html.startswith("<"):
                in_tag = True
            elif html.startswith(">"):
                in_tag = False
            elif not in_tag:
                text += html[0]
            html = html[1:]
        return text

    def show_text(self):
        response = self.get()
        body = response.body
        print(self.extract_text_from_html(body))


class TestURL:
    def test_url(self):
        url = URL("https://example.com/")
        assert url.schema == "https"
        assert url.host == "example.com"
        assert url.path == []

    def test_url_with_path(self):
        url = URL("https://example.com/path/to/file")
        assert url.schema == "https"
        assert url.host == "example.com"
        assert url.path == ["path", "to", "file"]

    def test_url_without_slash(self):
        url = URL("https://example.com")
        assert url.schema == "https"
        assert url.host == "example.com"
        assert url.path == []

    def test_url_without_schema(self):
        with pytest.raises(ValueError):
            URL("example.com")

    def test_url_with_invalid_schema(self):
        with pytest.raises(ValueError):
            URL("ftp://example.com")

    def test_url_with_invalid_host(self):
        URL("https://example.com:8080")

    def test_url_with_port(self):
        url = URL("https://example.com:8080/")
        assert url.schema == "https"
        assert url.host == "example.com"
        assert url.path == []

    def test_url_with_port_and_path(self):
        url = URL("https://example.com:8080/path/to/file")
        assert url.schema == "https"
        assert url.host == "example.com"
        assert url.path == ["path", "to", "file"]


class TestRequest:
    def test_get(self):
        url = URL("http://example.com/")
        response = url.get()
        assert response.status_code == 200
        assert response.status_text == "OK"
        assert response.headers["Content-Type".casefold()] == "text/html; charset=UTF-8"
        assert "<h1>Example Domain</h1>" in response.body


if __name__ == "__main__":
    url = URL("https://browser.engineering/http.html")
    url.show_text()
