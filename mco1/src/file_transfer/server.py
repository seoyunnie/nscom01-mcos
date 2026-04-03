#!/usr/bin/env python3

import argparse
import os
import pathlib
import socket

from file_transfer.endpoint import Endpoint
from file_transfer.packet import Packet, PacketType


class Server(Endpoint):
    FILENAME_PREFIX = "server_"

    def __init__(self, socket: socket.socket) -> None:
        super().__init__(socket)

    def handle_download(self, filename: str) -> None:
        stored_filename = f"{self.FILENAME_PREFIX}{filename}"

        if not pathlib.Path(stored_filename).exists():
            print(f"File '{filename}' not found, aborting download")

            self.send_abort(0, "File not found")

            return

        print(f"Sending file '{filename}' to {self.address}...")

        seq_num = 1

        with open(stored_filename, "rb") as f:
            while chunk := f.read(self.CHUNK_SIZE):
                if not self.send_reliable(PacketType.DATA, seq_num, chunk):
                    print(f"Failed to send chunk {seq_num}, aborting transfer")

                    self.send_abort(seq_num, "Transfer interrupted")

                    return

                seq_num += 1

        if not self.send_reliable(PacketType.FIN, seq_num, b"EOF"):
            print("Failed to send FIN packet, download may be incomplete")

            self.send_abort(seq_num, "Failed to finalize download")

            return

        print(f"File {filename} sent successfully")

    def handle_upload(self, filename: str) -> None:
        print(f"Receiving file '{filename}' from {self.address}...")

        stored_filename = f"{self.FILENAME_PREFIX}{filename}"

        with open(stored_filename, "wb") as f:
            seq_num = 1

            retries = 0

            while True:
                try:
                    data, sender_addr = self.socket.recvfrom(self.BUFFER_SIZE)

                    if sender_addr != self.address:
                        continue

                    packet = Packet.unpack(data)

                    if packet.type == PacketType.ERROR:
                        print(f"Received error from {self.address}: {packet.payload.decode()}")

                        self.socket.sendto(Packet(PacketType.ACK, packet.sequence_number).pack(), self.address)

                        raise FileNotFoundError  # noqa: TRY301

                    if packet.sequence_number < seq_num:
                        self.socket.sendto(Packet(PacketType.ACK, packet.sequence_number).pack(), self.address)

                        continue

                    if packet.type == PacketType.DATA and packet.sequence_number == seq_num:
                        self.socket.sendto(Packet(PacketType.ACK, seq_num).pack(), self.address)

                        f.write(packet.payload)

                        seq_num += 1

                        retries = 0

                        continue

                    if packet.type == PacketType.FIN and packet.sequence_number == seq_num:
                        self.socket.sendto(Packet(PacketType.ACK, seq_num).pack(), self.address)

                        break
                except TimeoutError:
                    retries += 1

                    if retries > self.MAX_RETRIES:
                        print("Max retries reached, aborting upload")

                        self.send_abort(seq_num, "Transfer interrupted")

                        return

                    if seq_num > 1:
                        print(f"Timeout waiting for chunk {seq_num}, retrying...")

                        self.socket.sendto(Packet(PacketType.ACK, seq_num - 1).pack(), self.address)
                except FileNotFoundError:
                    if pathlib.Path(stored_filename).exists():
                        os.remove(stored_filename)

                    return

        print(f"File {filename} received successfully as {stored_filename}")

    def run(self) -> None:
        print(f"Server listening on {self.socket.getsockname()}...")

        while True:
            try:
                self.socket.settimeout(None)

                data, client_addr = self.socket.recvfrom(self.BUFFER_SIZE)
                self.address = client_addr

                req = Packet.unpack(data)

                if req.type == PacketType.SYN:
                    self.socket.sendto(Packet(PacketType.ACK, req.sequence_number).pack(), self.address)

                    cmd, filename = req.payload.decode().split("|")

                    print()

                    print(f"Received {cmd} request for '{filename}' from {self.address}")

                    if cmd == "UPLOAD":
                        self.handle_upload(filename)
                    elif cmd == "DOWNLOAD":
                        self.handle_download(filename)
            except TimeoutError:
                print(f"Connection with {self.address} timed out, waiting for new connections...")
            except ValueError as e:
                print(f"Received malformed packet from {self.address}: {e}")


def get_local_address() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("1.1.1.1", 9998))

            return s.getsockname()[0]
        except OSError:
            return socket.gethostbyname(socket.gethostname())


def main() -> None:
    parser = argparse.ArgumentParser(description="UDP File Transfer Server")
    parser.add_argument("-p", "--port", type=int, default=9999, help="set the port to listen on (default: 9999)")

    args = parser.parse_args()
    port = args.port

    with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as s:
        try:
            addr = (get_local_address(), port)

            s.bind(addr)

            Server(s).run()
        except KeyboardInterrupt:
            print("\nServer shutting down...")


if __name__ == "__main__":
    main()
