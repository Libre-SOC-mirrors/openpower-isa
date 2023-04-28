import unittest
from openpower.decoder.isa.remap_preduce_yield import (
    prefix_sum_work_efficient, iterate_indices2)
from nmutil.prefix_sum import prefix_sum_ops, Op
from nmutil.plain_data import plain_data


@plain_data()
class MockSVShape:
    __slots__ = "lims", "order", "mode", "skip", "offset", "invxyz"

    def __init__(self, lims, order, mode, skip, offset, invxyz):
        # type: (list[int], list[int], int, int, int, list[int]) -> None
        self.lims = lims
        self.order = order
        self.mode = mode
        self.skip = skip
        self.offset = offset
        self.invxyz = invxyz


class TestRemapPrefixSum(unittest.TestCase):
    def test_prefix_sum_work_efficient(self):
        def fmt_op(op):
            return f"items[{op.out}] = items[{op.lhs}] + items[{op.rhs}]"
        for item_count in range(1, 16):
            with self.subTest(item_count=item_count):
                ops = list(prefix_sum_work_efficient(item_count))
                expected = prefix_sum_ops(item_count, work_efficient=True)
                expected = list(map(fmt_op, expected))
                self.assertEqual(ops, expected)

    def iterate_indices2_helper(self, reverse, item_count, offset):
        lhs_svshape = MockSVShape(
            lims=[item_count, 0, 0],
            order=(0, 1, 2),
            mode=0b10,
            skip=0b10,  # prefix-sum lhs
            offset=offset,
            invxyz=[reverse, 0, 0],
        )
        rhs_svshape = MockSVShape(
            lims=[item_count, 0, 0],
            order=(0, 1, 2),
            mode=0b10,
            skip=0b11,  # prefix-sum rhs
            offset=offset,
            invxyz=[reverse, 0, 0],
        )
        lhs_results = list(iterate_indices2(lhs_svshape))
        rhs_results = list(iterate_indices2(rhs_svshape))
        self.assertEqual(len(lhs_results), len(rhs_results))
        ops = []
        for (lhs, lend), (rhs, rend) in zip(lhs_results, rhs_results):
            self.assertEqual(lend, rend)
            ops.append(Op(out=rhs, lhs=lhs, rhs=rhs, row=0))
        expected = list(prefix_sum_ops(item_count, work_efficient=True))

        def f(i):
            return offset + (item_count - 1 - i if reverse else i)
        expected = [Op(
            out=f(i.out), lhs=f(i.lhs), rhs=f(i.rhs), row=0) for i in expected]
        self.assertEqual(ops, expected)

    def test_iterate_indices2(self):
        for r in (False, True):
            for ic in range(1, 16):
                for off in (0, 20):
                    with self.subTest(reverse=r, item_count=ic, offset=off):
                        self.iterate_indices2_helper(r, ic, off)


if __name__ == "__main__":
    unittest.main()
