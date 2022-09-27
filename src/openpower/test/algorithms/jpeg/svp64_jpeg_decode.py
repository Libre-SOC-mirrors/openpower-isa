# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

from pathlib import Path
from nmutil.plain_data import plain_data

RAINBOW_SMILEY = Path(__file__).with_name("rainbow_smiley.jpg").read_bytes()


@plain_data()
class HuffmanTable:
    __slots__ = "table", "table_id", "is_ac"

    def __init__(self, table=None, table_id=0, is_ac=False):
        # type: (None | dict[str, int], int, bool) -> None
        if table is None:
            table = {}
        self.table = table
        self.table_id = table_id
        self.is_ac = is_ac

    @staticmethod
    def decode(data):
        # type: (bytes) -> HuffmanTable
        id_offset = 0
        counts_offset = 1
        retval = HuffmanTable(table_id=data[id_offset] & 0xF,
                              is_ac=data[id_offset] & 0xF0 != 0)
        num_counts = 16
        offset = counts_offset + num_counts
        code = 0
        for i in range(num_counts):
            bit_length = 1 + i
            count = data[counts_offset + i]
            code <<= 1
            for _ in range(count):
                value = data[offset]
                offset += 1
                code_str = bin(code)[:2].rjust(bit_length, "0")
                retval.table[code_str] = value
                code += 1

        return retval


@plain_data()
class StartOfScanComponent:
    __slots__ = "component_id", "dc_huffman_table_id", "ac_huffman_table_id"

    def __init__(self, component_id, dc_huffman_table_id, ac_huffman_table_id):
        # type: (int, int, int) -> None
        self.component_id = component_id
        self.dc_huffman_table_id = dc_huffman_table_id
        self.ac_huffman_table_id = ac_huffman_table_id


def parse_start_of_scan(data):
    # type: (bytes) -> list[StartOfScanComponent]
    offset = 0
    color_component_count = data[offset]
    offset += 1
    retval = []
    for _ in range(color_component_count):
        retval.append(StartOfScanComponent(
            component_id=data[offset],
            dc_huffman_table_id=data[offset + 1] >> 4,
            ac_huffman_table_id=data[offset + 1] & 0xF,
        ))
        offset += 2
    # ignore the rest
    return retval


def extract_demo_bitstream(data):
    # type: (bytes) -> tuple[bytes, HuffmanTable]
    assert data.startswith(b"\xFF\xD8\xFF"), "not a jpeg"
    dc_huffman_tables = {}  # type: dict[int, HuffmanTable]
    ac_huffman_tables = {}  # type: dict[int, HuffmanTable]
    start_of_scan_data = []  # type: list[StartOfScanComponent]

    offset = 0
    while True:
        if data[offset] != 0xFF:
            offset += 1
            continue
        offset += 1
        if data[offset] == 0:
            offset += 1
            continue
        while data[offset] == 0xFF:
            offset += 1
        marker = data[offset]
        offset += 1
        if 0xD0 <= marker <= 0xD8:  # restart marker
            continue
        if marker == 0xD8:  # start of image
            break
        if marker == 0xD9:  # end of image
            assert False, "missing JPEG image data"
        segment_size = data[offset] << 8
        segment_size |= data[offset + 1]
        assert segment_size >= 2, "invalid marker segment size"
        segment_data = data[offset + 2:offset + segment_size]
        assert len(data) >= offset + segment_size, \
            "file truncated before end of marker segment"
        offset += segment_size
        if 0xE0 <= marker <= 0xEF:  # APP0 through APP15
            continue  # ignored
        if marker == 0xDB:  # DQT -- define quantization table
            continue  # ignored
        if marker == 0xC0:  # SOF0 -- start of frame
            continue  # ignored
        if marker == 0xC4:  # DHT -- define huffman table
            table = HuffmanTable.decode(segment_data)
            if table.is_ac:
                ac_huffman_tables[table.table_id] = table
            else:
                dc_huffman_tables[table.table_id] = table
            continue
        if marker == 0xDA:  # SOS -- start of scan
            start_of_scan_data = parse_start_of_scan(segment_data)
            print(start_of_scan_data)
            continue
        assert False, f"0xFF{marker:02X}: {segment_data}"
    # plan is to just extract a minimal huffman-compressed bitstream that can
    # be used for the assembly algorithm demo. this will just be the first
    # chunk of the file, not the whole thing.
    raise NotImplementedError  # TODO: finish


# DEMO_BITSTREAM, DEMO_HUFFMAN_TABLE = extract_demo_bitstream(RAINBOW_SMILEY)
