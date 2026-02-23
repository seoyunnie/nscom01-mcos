import enum
import struct
import zlib
from typing import Final, Self


class PacketType(enum.IntEnum):
    SYN = 0
    ACK = 1
    DATA = 2
    FIN = 3
    ERROR = 4


class Packet:
    HEADER_BASE_FORMAT = "!BIH"
    HEADER_FORMAT = "!BIHI"
    HEADER_SIZE: Final[int] = struct.calcsize(HEADER_FORMAT)

    CHECKSUM_MASK: Final[int] = (1 << 32) - 1

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
        header_base = struct.pack(self.HEADER_BASE_FORMAT, self.type, self.sequence_num, self.payload_length)

        checksum = zlib.crc32(header_base + self.payload) & self.CHECKSUM_MASK

        header = struct.pack(self.HEADER_FORMAT, self.type, self.sequence_num, self.payload_length, checksum)

        return header + self.payload

    @classmethod
    def unpack(cls, data: bytes) -> Self:
        if len(data) < cls.HEADER_SIZE:
            err_msg = "Data too short to contain header"

            raise ValueError(err_msg)

        header = data[: cls.HEADER_SIZE]
        packet_type, seq_num, payload_len, recv_checksum = struct.unpack(cls.HEADER_FORMAT, header)
        payload = data[cls.HEADER_SIZE : cls.HEADER_SIZE + payload_len]

        header_base = struct.pack(cls.HEADER_BASE_FORMAT, packet_type, seq_num, payload_len)
        expected_checksum = zlib.crc32(header_base + payload) & cls.CHECKSUM_MASK

        if recv_checksum != expected_checksum:
            err_msg = "Checksum mismatch"

            raise ValueError(err_msg)

        return cls(PacketType(packet_type), seq_num, payload)
