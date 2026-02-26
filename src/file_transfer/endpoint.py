from typing import TYPE_CHECKING, Final

from file_transfer.packet import Packet, PacketType

if TYPE_CHECKING:
    import socket


class Endpoint:
    CHUNK_SIZE = 4096
    BUFFER_SIZE: Final[int] = CHUNK_SIZE + Packet.HEADER_SIZE

    TIMEOUT = 2.0
    MAX_RETRIES = 5

    socket: socket.socket
    addr: tuple[str, int]

    def __init__(self, socket: socket.socket, addr: tuple[str, int]) -> None:
        self.socket = socket
        self.socket.settimeout(self.TIMEOUT)
        self.addr = addr

    def send_reliable(self, packet_type: PacketType, seq_num: int, payload: bytes = b"") -> bool:
        packet = Packet(packet_type, seq_num, payload).pack()

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.socket.sendto(packet, self.addr)

                res, sender_addr = self.socket.recvfrom(self.BUFFER_SIZE)

                if sender_addr != self.addr:
                    continue

                ack_packet = Packet.unpack(res)

                if ack_packet.sequence_num != seq_num:
                    continue

                if ack_packet.type == PacketType.ACK:
                    return True

                if ack_packet.type == PacketType.ERROR:
                    print(f"Received error from {self.addr}: {ack_packet.payload.decode()}")

                    return False
            except TimeoutError:
                print(f"Attempt {attempt} failed for packet {packet_type.name} seq {seq_num}, retrying...")
            except ValueError as e:
                print(f"Received invalid packet from {self.addr}: {e}")

        return False

    def send_abort(self, seq_num: int, error_msg: str) -> None:
        self.send_reliable(PacketType.ERROR, seq_num, error_msg.encode())
