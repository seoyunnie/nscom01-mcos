import enum
import struct
from typing import Final, Self


class PacketType(enum.IntEnum):
    SYN = 0
    ACK = 1
    DATA = 2
    FIN = 3
    ERROR = 4


class Packet:
    HEADER_FORMAT = "!BIH"
    HEADER_SIZE: Final[int] = struct.calcsize(HEADER_FORMAT)

    type: PacketType
    sequence_num: int
    payload_length: int
    payload: bytes

    def __init__(self, packet_type: PacketType, seq_num: int, payload: bytes = b"") -> None:
        self.type = packet_type
        self.sequence_num = seq_num
        self.payload_length = len(payload)
        self.payload = payload

    def pack(self) -> bytes:
        header = struct.pack(self.HEADER_FORMAT, self.type, self.sequence_num, self.payload_length)

        return header + self.payload

    @classmethod
    def unpack(cls, data: bytes) -> Self:
        if len(data) < cls.HEADER_SIZE:
            err_msg = "Data too short to contain header"

            raise ValueError(err_msg)

        header = data[: cls.HEADER_SIZE]
        packet_type, seq_num, payload_len = struct.unpack(cls.HEADER_FORMAT, header)
        payload = data[cls.HEADER_SIZE : cls.HEADER_SIZE + payload_len]

        return cls(PacketType(packet_type), seq_num, payload)
