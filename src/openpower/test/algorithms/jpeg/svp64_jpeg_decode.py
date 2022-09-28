# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

from pathlib import Path
from nmutil.plain_data import plain_data

RAINBOW_SMILEY = Path(__file__).with_name("rainbow_smiley.jpg").read_bytes()


@plain_data(unsafe_hash=True, frozen=True)
class HuffmanTableId:
    __slots__ = "is_ac", "table_id"

    def __init__(self, is_ac, table_id):
        # type: (bool, int) -> None
        self.is_ac = is_ac
        self.table_id = table_id

    @staticmethod
    def from_id_byte(id_byte):
        # type: (int) -> HuffmanTableId
        return HuffmanTableId(is_ac=id_byte & 0xF0 != 0,
                              table_id=id_byte & 0xF)


@plain_data()
class HuffmanTables:
    __slots__ = "tables",

    def __init__(self, tables=None):
        # type: (None | dict[HuffmanTableId, dict[str, int]]) -> None
        if tables is None:
            tables = {}
        self.tables = tables

    def add_from_bytes(self, data):
        # type: (bytes) -> None
        id_offset = 0
        counts_offset = 1
        table_id = HuffmanTableId.from_id_byte(data[id_offset])
        num_counts = 16
        offset = counts_offset + num_counts
        code = 0
        table = {}  # type: dict[str, int]
        for i in range(num_counts):
            bit_length = 1 + i
            count = data[counts_offset + i]
            code <<= 1
            for _ in range(count):
                value = data[offset]
                offset += 1
                code_str = bin(code)[2:].rjust(bit_length, "0")
                table[code_str] = value
                code += 1

        self.tables[table_id] = table


@plain_data()
class ScanComp:
    __slots__ = "comp_id", "dc_huffman_table_id", "ac_huffman_table_id"

    def __init__(self, comp_id, dc_huffman_table_id, ac_huffman_table_id):
        # type: (int, int | HuffmanTableId, int | HuffmanTableId) -> None
        self.comp_id = comp_id
        if isinstance(dc_huffman_table_id, int):
            dc_huffman_table_id = HuffmanTableId(is_ac=False,
                                                 table_id=dc_huffman_table_id)
        assert not dc_huffman_table_id.is_ac, \
            "dc huffman table id must be a dc table"
        if isinstance(ac_huffman_table_id, int):
            ac_huffman_table_id = HuffmanTableId(is_ac=True,
                                                 table_id=ac_huffman_table_id)
        assert ac_huffman_table_id.is_ac, \
            "ac huffman table id must be an ac table"
        self.dc_huffman_table_id = dc_huffman_table_id
        self.ac_huffman_table_id = ac_huffman_table_id


def parse_start_of_scan(data):
    # type: (bytes) -> list[ScanComp]
    offset = 0
    comp_cnt = data[offset]
    offset += 1
    retval = []
    for _ in range(comp_cnt):
        retval.append(ScanComp(
            comp_id=data[offset],
            dc_huffman_table_id=data[offset + 1] >> 4,
            ac_huffman_table_id=data[offset + 1] & 0xF,
        ))
        offset += 2
    # ignore the rest
    return retval


@plain_data()
class FrameHeaderComp:
    __slots__ = "comp_id", "h_smpl_fac", "v_smpl_fac", "quant_tbl"

    def __init__(self, comp_id, h_smpl_fac, v_smpl_fac, quant_tbl):
        # type: (int, int, int, int) -> None
        self.comp_id = comp_id
        self.h_smpl_fac = h_smpl_fac
        self.v_smpl_fac = v_smpl_fac
        self.quant_tbl = quant_tbl

    @property
    def repeat(self):
        return self.h_smpl_fac * self.v_smpl_fac

    @property
    def mcu_h(self):
        return 8 * self.h_smpl_fac

    @property
    def mcu_v(self):
        return 8 * self.v_smpl_fac


@plain_data()
class FrameHeader:
    __slots__ = "smpl_prec", "img_h", "img_w", "components"

    def __init__(self, smpl_prec, img_h, img_w, components):
        # type: (int, int, int, dict[int, FrameHeaderComp]) -> None
        self.smpl_prec = smpl_prec
        self.img_h = img_h
        self.img_w = img_w
        self.components = components


def parse_start_of_frame(marker, data):
    # type: (int, bytes) -> FrameHeader
    if marker != 0xC0:
        raise ValueError("only baseline DCT JPEG encoding supported")
    offset = 0
    smpl_prec = data[offset]
    offset += 1
    if smpl_prec != 8:
        raise ValueError(f"unsupported sample-precision {smpl_prec}")
    img_h = (data[offset] << 8) | data[offset + 1]
    offset += 2
    if img_h == 0:
        raise ValueError("image height not being defined in "
                         "start-of-frame is unsupported")
    img_w = (data[offset] << 8) | data[offset + 1]
    offset += 2
    if img_w == 0:
        raise ValueError("invalid image width")
    comp_cnt = data[offset]
    offset += 1
    if comp_cnt != 3:
        raise ValueError("non RGB/YCbCr JPEG not supported")
    components = {}
    for _ in range(comp_cnt):
        comp_id = data[offset]
        components[comp_id] = FrameHeaderComp(
            comp_id=comp_id,
            h_smpl_fac=data[offset + 1] >> 4,
            v_smpl_fac=data[offset + 1] & 0xF,
            quant_tbl=data[offset + 2],
        )
        offset += 3
    return FrameHeader(smpl_prec=smpl_prec, img_h=img_h,
                       img_w=img_w, components=components)


@plain_data()
class DemoBitstream:
    __slots__ = ("bitstream", "huffman_tables",
                 "frame_header", "scan_header")

    def __init__(self, bitstream, huffman_tables,
                 frame_header, scan_header):
        # type: (bytes, HuffmanTables, FrameHeader, list[ScanComp]) -> None
        self.bitstream = bitstream
        self.huffman_tables = huffman_tables
        self.frame_header = frame_header
        self.scan_header = scan_header


def extract_demo_bitstream(data):
    # type: (bytes) -> DemoBitstream
    assert data.startswith(b"\xFF\xD8\xFF"), "not a jpeg"
    huffman_tables = HuffmanTables()
    scan_header = []
    bitstream = []
    extracted_bitstream = None
    frame_header = None

    offset = 0
    while True:
        chunk_start = offset
        while True:
            if data[offset] == 0xFF:
                if data[offset + 1] == 0:
                    offset += 2
                else:
                    break
            else:
                offset += 1
        chunk_end = offset
        if chunk_start != chunk_end:
            bitstream.append(data[chunk_start:chunk_end])
        assert data[offset] == 0xFF
        offset += 1
        assert data[offset] != 0
        while data[offset] == 0xFF:
            offset += 1
        marker = data[offset]
        offset += 1
        if 0xD0 <= marker < 0xD8:  # restart marker
            raise ValueError("restart markers not supported")
        if marker == 0xD8:  # start of image
            continue
        if marker == 0xD9:  # end of image
            assert extracted_bitstream is not None, "missing JPEG image data"
            break
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
        if marker in (0xC0, 0xC1, 0xC2, 0xC3,
                      0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB,
                      0xCD, 0xCE, 0xCF):  # SOF0-15 -- start of frame
            frame_header = parse_start_of_frame(marker, segment_data)
            continue
        if marker == 0xC4:  # DHT -- define huffman table
            huffman_tables.add_from_bytes(segment_data)
            continue
        if marker == 0xDA:  # SOS -- start of scan
            if extracted_bitstream is not None:
                break
            scan_header = parse_start_of_scan(segment_data)
            bitstream = extracted_bitstream = []
            continue
        raise ValueError(f"unknown marker: 0xFF{marker:02X}: {segment_data}")
    if frame_header is None:
        raise ValueError("missing SOF0 marker (0xFF 0xC0)")
    return DemoBitstream(bitstream=b"".join(extracted_bitstream),
                         huffman_tables=huffman_tables,
                         frame_header=frame_header,
                         scan_header=scan_header)


DEMO_BITSTREAM = extract_demo_bitstream(RAINBOW_SMILEY)

if __name__ == "__main__":
    print(DEMO_BITSTREAM)
