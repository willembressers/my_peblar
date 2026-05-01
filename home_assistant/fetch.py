import base64
import json
import os
import socket
import struct
from urllib.parse import urlparse

from dotenv import dotenv_values

config = dotenv_values(".env")


def _recv_exact(sock, size):
    """Read exactly the requested number of bytes from the socket."""
    data = b""

    while len(data) < size:
        data += sock.recv(size - len(data))

    return data


def websocket_connect():
    """Open a Home Assistant WebSocket connection."""
    url = urlparse(config.get("BASE_URL"))
    host = url.hostname
    port = url.port or 80
    path = "/api/websocket"

    sock = socket.create_connection((host, port), timeout=30)
    key = base64.b64encode(os.urandom(16)).decode()
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock.sendall(request.encode())

    response = b""
    while b"\r\n\r\n" not in response:
        response += sock.recv(1024)

    print(response.decode())
    return sock


def websocket_read(sock):
    """Read one text message from the WebSocket connection."""
    first_byte, second_byte = _recv_exact(sock, 2)
    opcode = first_byte & 0x0F
    length = second_byte & 0x7F

    if length == 126:
        length = struct.unpack("!H", _recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _recv_exact(sock, 8))[0]

    payload = _recv_exact(sock, length)

    if opcode != 1:
        raise RuntimeError(f"Unexpected opcode: {opcode}")

    message = payload.decode()
    print(message)
    return json.loads(message)


def websocket_send(sock, message):
    """Send one JSON message over the WebSocket connection."""
    payload = json.dumps(message).encode()
    frame = bytearray([0x81])
    length = len(payload)

    if length < 126:
        frame.append(0x80 | length)
    elif length < 65536:
        frame.append(0x80 | 126)
        frame.extend(struct.pack("!H", length))
    else:
        frame.append(0x80 | 127)
        frame.extend(struct.pack("!Q", length))

    mask = os.urandom(4)
    frame.extend(mask)

    for index, byte in enumerate(payload):
        frame.append(byte ^ mask[index % 4])

    sock.sendall(frame)


def websocket_auth(sock):
    """Authenticate the WebSocket connection with the Home Assistant token."""
    websocket_read(sock)
    websocket_send(
        sock,
        {
            "type": "auth",
            "access_token": config.get("TOKEN"),
        },
    )
    return websocket_read(sock)


def statistics_during_period(
    sock, message_id, start, end, statistic_ids, period, types
):
    """Fetch long-term statistics for one or more sensors."""
    websocket_send(
        sock,
        {
            "id": message_id,
            "type": "recorder/statistics_during_period",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "statistic_ids": statistic_ids,
            "period": period,
            "types": types,
        },
    )
    return websocket_read(sock)


def data(start, end, charger_entity_id, tariff_entity_id):

    sock = websocket_connect()
    try:
        websocket_auth(sock)

        charger_data = statistics_during_period(
            sock=sock,
            message_id=1,
            start=start,
            end=end,
            statistic_ids=[charger_entity_id],
            period="day",
            types=["change"],
        )
        tariff_data = statistics_during_period(
            sock=sock,
            message_id=2,
            start=start,
            end=end,
            statistic_ids=[tariff_entity_id],
            period="day",
            types=["max"],
        )
    finally:
        sock.close()

    return charger_data, tariff_data
