import struct
import time
from typing import Final, TypedDict

NTP_EPOCH_OFFSET = 2208988800
NTP_FRACTION_SCALE = 2**32

RTCP_VERSION = 2
RTCP_PADDING = 0
RTCP_REPORT_COUNT = 0

RTCP_HEADER_FORMAT = "!BBH"
RTCP_HEADER_SIZE: Final[int] = struct.calcsize(RTCP_HEADER_FORMAT)

RTCP_SR_FORMAT = RTCP_HEADER_FORMAT + "IIIIII"
RTCP_SR_SIZE: Final[int] = struct.calcsize(RTCP_SR_FORMAT)

RTCP_FIRST_HEADER_BYTE: Final[int] = (RTCP_VERSION << 6) | (RTCP_PADDING << 5) | (RTCP_REPORT_COUNT)
RTCP_PACKET_TYPE_SR = 200
RTCP_SR_LENGTH = 6


def build_sender_report(ssrc: int, packet_cnt: int, octet_cnt: int, rtp_ts: int) -> bytes:
    now = time.time()

    ntp_seconds = int(now) + NTP_EPOCH_OFFSET
    ntp_frac = int((now % 1) * NTP_FRACTION_SCALE)

    return struct.pack(
        RTCP_SR_FORMAT,
        RTCP_FIRST_HEADER_BYTE,
        RTCP_PACKET_TYPE_SR,
        RTCP_SR_LENGTH,
        ssrc,
        ntp_seconds,
        ntp_frac,
        rtp_ts,
        packet_cnt,
        octet_cnt,
    )


class RTCPSenderReport(TypedDict):
    ssrc: int
    ntp_seconds: int
    ntp_fraction: int
    rtp_timestamp: int
    packet_count: int
    octet_count: int


def parse_sender_report(data: bytes) -> RTCPSenderReport | None:
    try:
        if len(data) < RTCP_SR_SIZE:
            return None

        _, packet_type, _ = struct.unpack(RTCP_HEADER_FORMAT, data[:RTCP_HEADER_SIZE])

        if packet_type != RTCP_PACKET_TYPE_SR:
            return None

        _, _, _, ssrc, ntp_seconds, ntp_frac, rtp_ts, packet_cnt, octet_cnt = struct.unpack(
            RTCP_SR_FORMAT, data[:RTCP_SR_SIZE]
        )
    except struct.error:
        return None
    else:
        return {
            "ssrc": ssrc,
            "ntp_seconds": ntp_seconds,
            "ntp_fraction": ntp_frac,
            "rtp_timestamp": rtp_ts,
            "packet_count": packet_cnt,
            "octet_count": octet_cnt,
        }
