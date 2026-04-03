import struct
from typing import Final, Self

PAYLOAD_TYPE_PCMU = 0

RTP_VERSION = 2
RTP_PADDING = 0
RTP_EXTENSION = 0
RTP_CSRC_COUNT = 0

RTP_MARKER = 0
RTP_PAYLOAD_TYPE = PAYLOAD_TYPE_PCMU


class RTPPacket:
    HEADER_FORMAT = "!BBHII"
    HEADER_SIZE: Final[int] = struct.calcsize(HEADER_FORMAT)

    FIRST_HEADER_BYTE: Final[int] = (RTP_VERSION << 6) | (RTP_PADDING << 5) | (RTP_EXTENSION << 4) | (RTP_CSRC_COUNT)
    SECOND_HEADER_BYTE: Final[int] = (RTP_MARKER << 7) | (RTP_PAYLOAD_TYPE)

    sequence_number: int
    timestamp: int
    ssrc: int
    payload: bytes

    def __init__(self, seq_num: int, ts: int, ssrc: int, payload: bytes) -> None:
        self.sequence_number = seq_num
        self.timestamp = ts
        self.ssrc = ssrc
        self.payload = payload

    @classmethod
    def unpack(cls, data: bytes) -> Self:
        if len(data) < cls.HEADER_SIZE:
            err_msg = "Data too short to contain header"

            raise ValueError(err_msg)

        header = data[: cls.HEADER_SIZE]
        _, _, seq_num, ts, ssrc = struct.unpack(cls.HEADER_FORMAT, header)

        payload = data[cls.HEADER_SIZE :]

        return cls(seq_num, ts, ssrc, payload)

    def pack(self) -> bytes:
        header = struct.pack(
            self.HEADER_FORMAT,
            self.FIRST_HEADER_BYTE,
            self.SECOND_HEADER_BYTE,
            self.sequence_number,
            self.timestamp,
            self.ssrc,
        )

        return header + self.payload
