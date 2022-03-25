# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com

""" Draw Textual Tree from list of operations

https://bugs.libre-soc.org/show_bug.cgi?id=697
"""


from dataclasses import dataclass, field
from enum import Enum
from re import T
from typing import Iterable
from cached_property import cached_property


class Op:
    """Generic N-in M-out operation."""

    def __init__(self, outs, ins):
        self.outs = tuple(map(int, outs))
        self.ins = tuple(map(int, ins))

    @property
    def name(self):
        return self.__class__.__name__

    def __str__(self):
        outs = repr(self.outs) if len(self.outs) != 1 else repr(self.outs[0])
        ins = repr(self.ins) if len(self.ins) != 1 else repr(self.ins[0])
        return f"{self.name} {outs} <= {ins}"

    def __repr__(self):
        return f"{self.name}({self.outs!r}, {self.ins!r})"


@dataclass(frozen=True, unsafe_hash=True)
class _SSAReg:
    reg: int
    counter: int


@dataclass
class _RegState:
    ssa_reg: _SSAReg
    written_by: "_Cell | None"

    @property
    def tree_depth(self):
        if self.written_by is None:
            return 0
        return self.written_by.tree_depth


@dataclass
class _Cell:
    op: "Op | None"
    outs: "tuple[_SSAReg, ...]"
    ins: "tuple[_SSAReg, ...]"
    tree_depth: int

    @cached_property
    def __op_text(self):
        # only cache if op is set, otherwise debuggers could cache the empty
        # value prematurely, causing the code to fail when debugged
        assert self.op is not None
        return str(self.op)

    @property
    def text(self):
        if self.op is None:
            return ""
        return self.__op_text

    @property
    def io_coords_count(self):
        return max(len(self.outs), len(self.ins))

    @property
    def cell_part_text_width(self):
        """return the terminal width used by text"""
        # Python doesn't have the right function needed to implement this,
        # the correct function is something like:
        # https://docs.rs/unicode-width/0.1.9/unicode_width/trait.UnicodeWidthStr.html#tymethod.width
        # so, we just return something kinda sorta ok, sorry non-ascii people
        text_width = len(self.text)
        io_text_width = self.io_coords_count
        return max(text_width, io_text_width)

    @property
    def cell_part_text_height(self):
        return 1

    @property
    def grid_x(self):
        if len(self.outs):
            return self.outs[0].reg
        if len(self.ins):
            return self.ins[0].reg
        return 0

    @property
    def grid_y(self):
        return self.tree_depth

    @property
    def grid_pos(self):
        return self.grid_x, self.grid_y

    def clear_after_size_bump(self):
        # TODO: add clearing locals with routing info
        pass


class _RestartWithBiggerChannel(Exception):
    pass


class _CheckIfFitsResult(Enum):
    FITS = True
    KEEP_LOOKING = False
    CANCEL = "cancel"


@dataclass
class _RoutingChannelBase:
    cell_coord: int
    used: "set[tuple[_Coord, _Coord]]" = field(default_factory=set, init=False)
    size: int = 0

    def clear_after_size_bump(self):
        self.used.clear()

    def _allocate_segment(self, coord_range, flip_coords, check_if_fits=None):
        """allocate a segment of a horizontal line extending to every x
            in coord_range.
            returns the allocated y _Coord.
            flip_coords: bool
                true if we're allocating a vertical line segment rather than
                horizontal. exchanges x and y.
        """
        subcell_coord = 0
        coord_range = list(coord_range)
        while True:
            y = _Coord(cell_coord=self.cell_coord, in_routing_channel=True,
                       subcell_coord=subcell_coord)
            fits = True
            for x in coord_range:
                assert isinstance(x, _Coord)
                pos = (y, x) if flip_coords else (x, y)
                if pos in self.used:
                    fits = False
                    break
            if fits and check_if_fits is not None:
                result = check_if_fits(y)
                if result == _CheckIfFitsResult.CANCEL:
                    return None
                elif result == _CheckIfFitsResult.KEEP_LOOKING:
                    fits = False
                else:
                    assert result == _CheckIfFitsResult.FITS
            if not fits:
                subcell_coord += 1
                if subcell_coord >= self.size:
                    self.size += 1
                    raise _RestartWithBiggerChannel
                continue
            for x in coord_range:
                assert isinstance(x, _Coord)
                pos = (y, x) if flip_coords else (x, y)
                self.used.add(pos)
            return y


@dataclass
class _HorizontalRoutingChannel(_RoutingChannelBase):
    def alloc_h_seg(self, x_range, check_if_fits=None):
        """allocate a segment of a horizontal line extending to every x
            in x_range.
            returns the allocated y _Coord.
        """
        return self._allocate_segment(x_range, flip_coords=False,
                                      check_if_fits=check_if_fits)


@dataclass
class _VerticalRoutingChannel(_RoutingChannelBase):
    def alloc_v_seg(self, y_range, check_if_fits=None):
        """allocate a segment of a vertical line extending to every y
            in y_range.
            returns the allocated x _Coord.
        """
        return self._allocate_segment(y_range, flip_coords=True,
                                      check_if_fits=check_if_fits)


@dataclass(frozen=True, unsafe_hash=True)
class _Coord:
    r"""
    Coordinates:
                                       cell_x
              /---------------------------^-------------------------\
              |                                                     |
                rx=0  rx=1  rx=2  rx=3       ox=0 ox=1 ox=2 ox=3
           /- +--------------------------+--------------------------+
    ry=0   |  | Routing Channel -------- | Routing Channel -------- | ry=0
           |  | horizontal coord: |      | horizontal coord: |      |
    ry=1   |  | cell_coord=cell_x ------ | cell_coord=cell_x ------ | ry=1
           |  | in_routing_channel=True  | in_routing_channel=False |
    ry=2   |  | subcell_coord=rx ------- | subcell_coord=ox ------- | ry=2
           |  | vertical coord:   |      | vertical coord:   |      |
    ry=3   |  | cell_coord=cell_y ------ | cell_coord=cell_y ------ | ry=3
           |  | in_routing_channel=True  | in_routing_channel=True  |
    ry=4   |  | subcell_coord=ry ------- | subcell_coord=ry ------- | ry=4
           |  | |     |     |     |      |    |    |    |    |      |
           |  +--------------------------+--------------------------+
    cell_y <  | Routing Channel   |      | horizontal coord: |      |
           |  | horizontal coord: |      | cell_coord=cell_x |      |
           |  | cell_coord=cell_x |      | in_routing_channel=False |
           |  | in_routing_channel=True  | subcell_coord=ox  |      |
           |  | subcell_coord=rx  |      | vertical coord:   |      |
           |  | vertical coord:   |      | cell_coord=cell_y |      |
           |  | cell_coord=cell_y |      | in_routing_channel=False |
           |  | in_routing_channel=False | subcell_coord=oy  |      |
           |  | subcell_coord=oy  |      |    |    |    |    |      |
           |  | |     |     |     |      |    V    V    V    V      |
     oy=0  |  | |     |     |     |      | +-In0--In1--In2--In3--+  | oy=0
           |  | |     |     |     |      | |          Op         |  |
     oy=1  |  | |     |     |     |      | +-Out0-Out1-Out2------+  | oy=1
           |  | |     |     |     |      |    |    |    |           |
           \- +--------------------------+--------------------------+
                rx=0  rx=1  rx=2  rx=3       ox=0 ox=1 ox=2 ox=3
    """
    cell_coord: int
    in_routing_channel: bool
    subcell_coord: int

    def __lt__(self, other):
        if not isinstance(other, _Coord):
            return NotImplemented
        if self.cell_coord < other.cell_coord:
            return True
        if self.cell_coord > other.cell_coord:
            return False
        if self.in_routing_channel and not other.in_routing_channel:
            return True
        if not self.in_routing_channel and other.in_routing_channel:
            return False
        return self.subcell_coord < other.subcell_coord

    def __le__(self, other):
        if not isinstance(other, _Coord):
            return NotImplemented
        return not other.__lt__(self)

    def __gt__(self, other):
        if not isinstance(other, _Coord):
            return NotImplemented
        return other.__lt__(self)

    def __ge__(self, other):
        if not isinstance(other, _Coord):
            return NotImplemented
        return not self.__lt__(other)


@dataclass
class _Route:
    """route, made of horizontal and vertical lines,
        from some op's output to another op's input.
    """
    coords: "list[_Coord]" = field(default_factory=list)
    """alternating x and y coords for the route, starting with y"""

    def __len__(self):
        """number of points in this route"""
        return max(len(self.coords) - 1, 0)

    def __getitem__(self, index):
        assert isinstance(index, int)
        if index < 0:
            index += len(self)
        assert 0 <= index < len(self)
        c0 = self.coords[index]
        c1 = self.coords[index + 1]
        if index % 2 != 0:
            return c0, c1
        return c1, c0

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    @property
    def start_pos(self):
        return self[0]

    @property
    def end_pos(self):
        return self[-1]

    def __str__(self):
        return f"Route{{{' -> '.join(map(repr, self))}}}"


@dataclass
class _GridRow:
    cells: "list[_Cell | None]"
    routing_channel: _HorizontalRoutingChannel
    cell_part_text_height: int = 0
    text_y_start: "int | None" = None

    @property
    def text_height(self):
        return self.cell_part_text_height + self.routing_channel.size

    def __init__(self, cell_y, x_size):
        assert isinstance(x_size, int)
        self.cells = [None] * x_size
        self.routing_channel = _HorizontalRoutingChannel(cell_coord=cell_y)

    def clear_after_size_bump(self):
        for cell in self.cells:
            if cell is not None:
                cell.clear_after_size_bump()
        self.routing_channel.clear_after_size_bump()
        self.cell_part_text_height = 0
        self.text_y_start = None


@dataclass
class _GridCol:
    routing_channel: _VerticalRoutingChannel
    cell_part_text_width: int = 0
    io_coords_count: int = 0
    text_x_start: "int | None" = None

    @property
    def text_width(self):
        return self.cell_part_text_width + self.routing_channel.size

    def __init__(self, cell_x):
        self.routing_channel = _VerticalRoutingChannel(cell_coord=cell_x)

    def clear_after_size_bump(self):
        self.routing_channel.clear_after_size_bump()
        self.cell_part_text_width = 0
        self.text_x_start = None


@dataclass
class _Grid:
    cols: "list[_GridCol]"
    rows: "list[_GridRow]"
    x_coords: "list[_Coord]"
    x_coords_indexes: "dict[_Coord, int]"
    y_coords: "list[_Coord]"
    y_coords_indexes: "dict[_Coord, int]"

    def __init__(self, x_size, y_size):
        self.cols = [_GridCol(cell_x) for cell_x in range(x_size)]
        self.rows = [_GridRow(cell_y, x_size) for cell_y in range(y_size)]
        self.x_coords = []
        self.x_coords_indexes = {}
        self.y_coords = []
        self.y_coords_indexes = {}

    def clear_after_size_bump(self):
        for col in self.cols:
            col.clear_after_size_bump()
        for row in self.rows:
            row.clear_after_size_bump()

    def calc_positions_and_sizes(self):
        self.x_coords = []
        self.y_coords = []
        text_y = 0
        for cell_y, row in enumerate(self.rows):
            row.text_y_start = text_y
            for cell_x, cell in enumerate(row.cells):
                if cell is None:
                    continue
                col = self.cols[cell_x]
                col.cell_part_text_width = max(col.cell_part_text_width,
                                               cell.cell_part_text_width)
                row.cell_part_text_height = max(row.cell_part_text_height,
                                                cell.cell_part_text_height)
                col.io_coords_count = max(col.io_coords_count,
                                          cell.io_coords_count)
            for subcell_coord in range(row.routing_channel.size):
                self.y_coords.append(_Coord(cell_coord=cell_y,
                                            in_routing_channel=True,
                                            subcell_coord=subcell_coord))
            self.y_coords.append(_Coord(cell_coord=cell_y,
                                        in_routing_channel=False,
                                        subcell_coord=0))
            self.y_coords.append(_Coord(cell_coord=cell_y,
                                        in_routing_channel=False,
                                        subcell_coord=1))
            text_y += row.text_height
        text_x = 0
        for cell_x, col in enumerate(self.cols):
            col.text_x_start = text_x
            for subcell_coord in range(col.routing_channel.size):
                self.x_coords.append(_Coord(cell_coord=cell_x,
                                            in_routing_channel=True,
                                            subcell_coord=subcell_coord))
            for subcell_coord in range(col.io_coords_count):
                self.x_coords.append(_Coord(cell_coord=cell_x,
                                            in_routing_channel=False,
                                            subcell_coord=subcell_coord))
            text_x += col.text_width
        assert self.x_coords == sorted(self.x_coords), \
            "mismatch with _Coord comparison"
        assert self.y_coords == sorted(self.y_coords), \
            "mismatch with _Coord comparison"
        self.x_coords_indexes = {x: i for i, x in enumerate(self.x_coords)}
        self.y_coords_indexes = {y: i for i, y in enumerate(self.y_coords)}

    def text_x(self, x_coord):
        assert isinstance(x_coord, _Coord)
        col = self.cols[x_coord.cell_coord]
        assert col.text_x_start is not None
        if x_coord.in_routing_channel:
            return col.text_x_start + x_coord.subcell_coord
        else:
            return (col.text_x_start + col.routing_channel.size
                    + x_coord.subcell_coord)

    def text_y(self, y_coord):
        assert isinstance(y_coord, _Coord)
        row = self.rows[y_coord.cell_coord]
        assert row.text_y_start is not None
        if y_coord.in_routing_channel:
            return row.text_y_start + y_coord.subcell_coord
        else:
            return (row.text_y_start + row.routing_channel.size
                    + y_coord.subcell_coord)

    def __getitem__(self, pos):
        x, y = pos
        assert isinstance(x, int)
        assert isinstance(y, int)
        return self.rows[y].cells[x]

    def __setitem__(self, pos, value):
        assert value is None or isinstance(value, _Cell)
        x, y = pos
        assert isinstance(x, int)
        assert isinstance(y, int)
        self.rows[y].cells[x] = value

    def range_x_coord(self, first_x, last_x):
        """return all x `_Coord`s in first_x to last_x inclusive"""
        assert isinstance(first_x, _Coord)
        assert isinstance(last_x, _Coord)
        first = self.x_coords_indexes[first_x]
        last = self.x_coords_indexes[last_x]
        if first < last:
            return self.x_coords[first:last + 1]
        return self.x_coords[last:first + 1]

    def range_y_coord(self, first_y, last_y):
        """return all y `_Coord`s in first_y to last_y inclusive"""
        assert isinstance(first_y, _Coord)
        assert isinstance(last_y, _Coord)
        first = self.y_coords_indexes[first_y]
        last = self.y_coords_indexes[last_y]
        if first < last:
            return self.y_coords[first:last + 1]
        return self.y_coords[last:first + 1]

    def alloc_h_seg(self, src_x, dest_x, cell_y, check_if_fits=None):
        assert isinstance(src_x, _Coord)
        assert isinstance(dest_x, _Coord)
        assert isinstance(cell_y, int)
        horiz_rc = self.rows[cell_y].routing_channel
        r = self.range_x_coord(src_x, dest_x)
        return horiz_rc.alloc_h_seg(r, check_if_fits=check_if_fits)

    def alloc_v_seg(self, cell_x, src_y, dest_y, check_if_fits=None):
        assert isinstance(cell_x, int)
        assert isinstance(src_y, _Coord)
        assert isinstance(dest_y, _Coord)
        vert_rc = self.cols[cell_x].routing_channel
        r = self.range_y_coord(src_y, dest_y)
        return vert_rc.alloc_v_seg(r, check_if_fits=check_if_fits)

    def allocate_route(self, dest_op_input_index, dest_cell_pos,
                       src_op_output_index, src_cell_pos):
        assert isinstance(dest_op_input_index, int)
        dest_cell_x, dest_cell_y = dest_cell_pos
        assert isinstance(dest_cell_x, int)
        assert isinstance(dest_cell_y, int)
        assert isinstance(src_op_output_index, int)
        src_cell_x, src_cell_y = src_cell_pos
        assert isinstance(src_cell_x, int)
        assert isinstance(src_cell_y, int)
        assert dest_cell_y > src_cell_y, "bad route passed in"
        src_x = _Coord(cell_coord=src_cell_x,
                       in_routing_channel=False,
                       subcell_coord=src_op_output_index)
        src_y = _Coord(cell_coord=src_cell_y,
                       in_routing_channel=False,
                       subcell_coord=1)
        dest_x = _Coord(cell_coord=dest_cell_x,
                        in_routing_channel=False,
                        subcell_coord=dest_op_input_index)
        dest_y = _Coord(cell_coord=dest_cell_y,
                        in_routing_channel=False,
                        subcell_coord=0)
        if dest_cell_y == src_cell_y + 1:
            # no intervening cells vertically
            if src_x == dest_x:
                # straight line from src to dest
                return _Route([src_y, src_x, dest_y])
            rc_y = self.alloc_h_seg(src_x, dest_x, dest_cell_y)
            assert rc_y is not None
            return _Route([
                # start
                src_y, src_x,
                # go to routing channel
                rc_y,
                # go horizontally to dest x
                dest_x,
                # go vertically to dest y
                dest_y,
            ])
        else:
            def check_if_fits(y):
                raise NotImplementedError
            raise NotImplementedError
            todo_x = ...  # FIXME finish
            src_horiz_rc_y = self.alloc_h_seg(src_x, todo_x, dest_cell_y,
                                              check_if_fits=check_if_fits)
            raise NotImplementedError


@dataclass
class _Regs:
    __regs: "list[_RegState]" = field(default_factory=list)

    def get(self, reg):
        assert isinstance(reg, int) and reg >= 0
        for i in range(len(self.__regs), reg + 1):
            self.__regs.append(_RegState(_SSAReg(i, 0), None))
        return self.__regs[reg]

    def __len__(self):
        return len(self.__regs)


def render_tree(program, indent_str=""):
    """draw a tree of operations. returns a string with the rendered tree.
    program: Iterable[Op]
    """
    # build ops_graph
    ops_graph: "dict[_SSAReg, _Cell]"
    ops_graph = {}
    regs = _Regs()
    cells: "list[_Cell]" = []
    for op in program:
        assert isinstance(op, Op)
        ins = tuple(regs.get(reg).ssa_reg for reg in op.ins)
        tree_depth = max(regs.get(reg).tree_depth for reg in op.ins) + 1
        outs = tuple(regs.get(reg).ssa_reg for reg in op.outs)
        assert len(set(outs)) == len(outs), \
            f"duplicate output registers on the same instruction: {op}"
        cell = _Cell(
            op=op, outs=outs, ins=ins, tree_depth=tree_depth)
        for out in op.outs:
            out_reg = regs.get(out)
            out_reg.ssa_reg = out = _SSAReg(out, out_reg.ssa_reg.counter + 1)
            ops_graph[out] = out_reg.written_by = cell
        cells.append(cell)

    # generate output grid
    grid = _Grid(x_size=len(regs),
                 y_size=max(i.grid_y for i in ops_graph.values()) + 1)
    for cell in cells:
        grid[cell.grid_pos] = cell
    raise NotImplementedError


def print_tree(program, indent_str=""):
    """draw a tree of operations. prints the tree to stdout.
    program: Iterable[Op]
    """
    print(render_tree(program, indent_str=indent_str))
