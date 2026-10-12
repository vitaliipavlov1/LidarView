#!/usr/bin/env python3
"""Packet-level sanity check for a Velodyne LiDAR capture.

Confirms the file really is a PCAP holding Velodyne UDP packets, independently of
LidarView. This only inspects packet headers -- it does not decode points.

Usage: check_pcap.py <file.pcap> [max_packets]
"""
import struct
import sys

LIDAR_PORT, POSITION_PORT = 2368, 8308
VELODYNE_LIDAR_PAYLOAD = 1206      # 42-byte UDP/IP/Eth header stripped
VELODYNE_BLOCK_FLAG = b"\xff\xee"  # start of every firing block


def main(path, limit=200000):
    with open(path, "rb") as fh:
        magic = fh.read(4)
        endian, nano = {
            b"\xd4\xc3\xb2\xa1": ("<", False), b"\xa1\xb2\xc3\xd4": (">", False),
            b"\x4d\x3c\xb2\xa1": ("<", True),  b"\xa1\xb2\x3c\x4d": (">", True),
        }.get(magic, (None, None))
        if endian is None:
            print("FAIL: not a libpcap file (magic %s)" % magic.hex())
            return 1
        vmaj, vmin, _tz, _sig, snaplen, link = struct.unpack(endian + "HHiIII", fh.read(20))
        print("file           : %s" % path)
        print("pcap magic     : %s  (%s-endian, %s)" % (
            magic.hex(), "little" if endian == "<" else "big",
            "nanosecond" if nano else "microsecond"))
        print("pcap version   : %d.%d  snaplen=%d linktype=%d (%s)" % (
            vmaj, vmin, snaplen, link, "ETHERNET" if link == 1 else "other"))

        n = lidar = position = other = blocks_ok = 0
        sizes, ports, t_first, t_last = {}, {}, None, None
        while n < limit:
            hdr = fh.read(16)
            if len(hdr) < 16:
                break
            ts_s, ts_frac, caplen, _orig = struct.unpack(endian + "IIII", hdr)
            data = fh.read(caplen)
            if len(data) < caplen:
                break
            n += 1
            t = ts_s + ts_frac / (1e9 if nano else 1e6)
            t_first = t if t_first is None else t_first
            t_last = t
            if link == 1 and caplen >= 42 and data[12:14] == b"\x08\x00" and data[23] == 17:
                dport = struct.unpack("!H", data[36:38])[0]
                payload = data[42:]
                ports[dport] = ports.get(dport, 0) + 1
                sizes[len(payload)] = sizes.get(len(payload), 0) + 1
                if dport == LIDAR_PORT and len(payload) == VELODYNE_LIDAR_PAYLOAD:
                    lidar += 1
                    if payload[0:2] == VELODYNE_BLOCK_FLAG:
                        blocks_ok += 1
                elif dport == POSITION_PORT:
                    position += 1
                else:
                    other += 1
            else:
                other += 1

    print("packets read   : %d%s" % (n, "  (limit reached)" if n >= limit else ""))
    if t_first is not None:
        print("capture span   : %.3f s  (%.3f .. %.3f)" % (t_last - t_first, t_first, t_last))
    print("UDP dst ports  : %s" % ", ".join("%d x%d" % (p, c) for p, c in sorted(ports.items())))
    print("payload sizes  : %s" % ", ".join("%dB x%d" % (s, c) for s, c in sorted(sizes.items())))
    print("lidar packets  : %d on port %d with %d-byte payload" % (lidar, LIDAR_PORT, VELODYNE_LIDAR_PAYLOAD))
    print("valid 0xFFEE   : %d / %d firing-block markers" % (blocks_ok, lidar))
    print("position pkts  : %d on port %d" % (position, POSITION_PORT))
    print("other packets  : %d" % other)

    ok = link == 1 and lidar > 0 and blocks_ok == lidar
    print()
    print("RESULT: %s" % ("PASS - valid PCAP with Velodyne LiDAR packets" if ok
                         else "FAIL - no consistent Velodyne LiDAR packets found"))
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 200000))
