import argparse
import os
import socket

from file_transfer.endpoint import Endpoint
from file_transfer.packet import Packet, PacketType


class Server(Endpoint):
    def handle_download(self, filename: str) -> None:
        if not os.path.exists(filename):
            print(f"File '{filename}' not found, aborting download")

            self.send_abort(0, "File not found")

            return

        print(f"Sending file '{filename}' to {self.addr}...")

        seq_num = 1

        with open(filename, "rb") as f:
            while chunk := f.read(self.CHUNK_SIZE):
                if not self.send_reliable(PacketType.DATA, seq_num, chunk):
                    print(f"Failed to send chunk {seq_num}, aborting transfer")

                    self.send_abort(seq_num, "Transfer interrupted")

                    return

                seq_num += 1

        if not self.send_reliable(PacketType.FIN, seq_num):
            print("Failed to send FIN packet, download may be incomplete")

            self.send_abort(seq_num, "Failed to finalize download")

            return

        print(f"File {filename} sent successfully")

    def handle_upload(self, filename: str) -> None:
        print(f"Receiving file '{filename}' from {self.addr}...")

        with open(f"server_{filename}", "wb") as f:
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
                        self.socket.sendto(Packet(PacketType.ACK, seq_num).pack(), self.addr)

                        f.write(packet.payload)

                        seq_num += 1

                        retries = 0

                        continue

                    if packet.type == PacketType.FIN and packet.sequence_num == seq_num:
                        self.socket.sendto(Packet(PacketType.ACK, seq_num).pack(), self.addr)

                        break
                except TimeoutError:
                    retries += 1

                    if retries > self.MAX_RETRIES:
                        print("Max retries reached, aborting upload")

                        self.send_abort(seq_num, "Transfer interrupted")

                        return

                    if seq_num > 1:
                        print(f"Timeout waiting for chunk {seq_num}, retrying...")

                        self.socket.sendto(Packet(PacketType.ACK, seq_num - 1).pack(), self.addr)

        print(f"File {filename} received successfully as server_{filename}")

    def run(self) -> None:
        print(f"Server listening on {self.socket.getsockname()}...")

        while True:
            try:
                self.socket.settimeout(None)

                data, client_addr = self.socket.recvfrom(self.BUFFER_SIZE)
                self.addr = client_addr

                req = Packet.unpack(data)

                if req.type == PacketType.SYN:
                    self.socket.sendto(Packet(PacketType.ACK, req.sequence_num).pack(), self.addr)

                    cmd, filename = req.payload.decode().split("|")

                    print()

                    print(f"Received {cmd} request for '{filename}' from {self.addr}")

                    if cmd == "UPLOAD":
                        self.handle_upload(filename)
                    elif cmd == "DOWNLOAD":
                        self.handle_download(filename)
            except TimeoutError:
                print(f"Connection with {self.addr} timed out, waiting for new connections...")
            except ValueError as e:
                print(f"Received malformed packet from {self.addr}: {e}")


def get_local_address() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("1.1.1.1", 9998))

            return s.getsockname()[0]
        except OSError:
            return socket.gethostbyname(socket.gethostname())


def main() -> None:
    parser = argparse.ArgumentParser(description="UDP File Transfer Server")
    parser.add_argument("-p", "--port", type=int, default=9999, help="Port to listen on (default: 9999)")

    args = parser.parse_args()
    port = args.port

    with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as s:
        try:
            addr = (get_local_address(), port)

            s.bind(addr)

            Server(s, addr).run()
        except KeyboardInterrupt:
            print("\nServer shutting down...")
