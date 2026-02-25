#!/usr/bin/env python3

import argparse
import os
import socket

from file_transfer.endpoint import Endpoint
from file_transfer.packet import Packet, PacketType


class Client(Endpoint):
    FILENAME_PREFIX = "client_"

    def upload_file(self, filename: str) -> None:
        if not os.path.exists(filename):
            print(f"File '{filename}' not found, aborting upload")

            self.send_abort(0, "File not found")

            return

        print(f"Uploading file '{filename}' to {self.addr}...")

        seq_num = 1

        with open(filename, "rb") as f:
            while chunk := f.read(self.CHUNK_SIZE):
                if not self.send_reliable(PacketType.DATA, seq_num, chunk):
                    print(f"Failed to send chunk {seq_num}, aborting transfer")

                    self.send_abort(seq_num, "Transfer interrupted")

                    return

                seq_num += 1

        if not self.send_reliable(PacketType.FIN, seq_num, b"EOF"):
            print("Failed to send FIN packet, upload may be incomplete")

            self.send_abort(seq_num, "Failed to finalize upload")

            return

        print(f"File {filename} uploaded successfully")

    def download_file(self, filename: str) -> None:
        print(f"Downloading file '{filename}' from {self.addr}...")

        downloaded_filename = f"{self.FILENAME_PREFIX}{filename}"

        with open(downloaded_filename, "wb") as f:
            seq_num = 1

            retries = 0

            while True:
                try:
                    data, sender_addr = self.socket.recvfrom(self.BUFFER_SIZE)

                    if sender_addr != self.addr:
                        continue

                    packet = Packet.unpack(data)

                    if packet.type == PacketType.ERROR:
                        print(f"Received error from {self.addr}: {packet.payload.decode()}")

                        self.socket.sendto(Packet(PacketType.ACK, packet.sequence_num).pack(), self.addr)

                        return

                    if packet.sequence_num < seq_num:
                        self.socket.sendto(Packet(PacketType.ACK, packet.sequence_num).pack(), self.addr)

                        continue

                    if packet.type == PacketType.DATA and packet.sequence_num == seq_num:
                        f.write(packet.payload)

                        self.socket.sendto(Packet(PacketType.ACK, seq_num).pack(), self.addr)

                        seq_num += 1

                        retries = 0

                        continue

                    if packet.type == PacketType.FIN and packet.sequence_num == seq_num:
                        self.socket.sendto(Packet(PacketType.ACK, seq_num).pack(), self.addr)

                        break
                except TimeoutError:
                    retries += 1

                    if retries >= self.MAX_RETRIES:
                        print("Max retries reached, aborting download")

                        self.send_abort(seq_num, "Transfer interrupted")

                        return

                    if seq_num > 1:
                        print(f"Timeout waiting for chunk {seq_num}, retrying...")

                        self.socket.sendto(Packet(PacketType.ACK, seq_num - 1).pack(), self.addr)

        print(f"File {filename} downloaded successfully as {downloaded_filename}")

    def request_operation(self, op: str, filename: str) -> None:
        payload = f"{op}|{filename}".encode()

        if not self.send_reliable(PacketType.SYN, 0, payload):
            print("Failed to send request, aborting")

            return

        if op == "UPLOAD":
            self.upload_file(filename)
        elif op == "DOWNLOAD":
            self.download_file(filename)


def main() -> None:
    parser = argparse.ArgumentParser(description="UDP File Transfer Client")
    parser.add_argument(
        "-s",
        "--server",
        default=socket.gethostbyname(socket.gethostname()),
        help="set the server IP address (default: localhost)",
    )
    parser.add_argument("-p", "--port", type=int, default=9999, help="set the port to send to (default: 9999)")
    parser.add_argument("operation", choices=["UPLOAD", "DOWNLOAD"], help="the operation to perform")
    parser.add_argument("filename", help="the name of or path to the file to upload/download")

    args = parser.parse_args()
    server_addr: tuple[str, int] = (socket.gethostbyname(args.server), args.port)
    op, filename = args.operation, args.filename

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        Client(s, server_addr).request_operation(op, filename)


if __name__ == "__main__":
    main()
