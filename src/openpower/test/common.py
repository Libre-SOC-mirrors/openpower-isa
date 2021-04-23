"""
Bugreports:
* https://bugs.libre-soc.org/show_bug.cgi?id=361
"""

import inspect
import functools
import types


# TODO: make this a util routine (somewhere)
def mask_extend(x, nbits, repeat):
    res = 0
    extended = (1<<repeat)-1
    for i in range(nbits):
        if x & (1<<i):
            res |= extended << (i*repeat)
    return res


class SkipCase(Exception):
    """Raise this exception to skip a test case.

    Usually you'd use one of the skip_case* decorators.

    For use with TestAccumulatorBase
    """


def _id(obj):
    """identity function"""
    return obj


def skip_case(reason):
    """
    Unconditionally skip a test case.

    Use like:
        @skip_case("my reason for skipping")
        def case_abc(self):
            ...
    or:
        @skip_case
        def case_def(self):
            ...

    For use with TestAccumulatorBase
    """
    def decorator(item):
        assert not isinstance(item, type), \
            "can't use skip_case to decorate types"

        @functools.wraps(item)
        def wrapper(*args, **kwargs):
            raise SkipCase(reason)
        return wrapper
    if isinstance(reason, types.FunctionType):
        item = reason
        reason = ""
        return decorator(item)
    return decorator


def skip_case_if(condition, reason):
    """
    Conditionally skip a test case.

    Use like:
        @skip_case_if(should_i_skip(), "my reason for skipping")
        def case_abc(self):
            ...

    For use with TestAccumulatorBase
    """
    if condition:
        return skip_case(reason)
    return _id


class TestAccumulatorBase:

    def __init__(self):
        self.test_data = []
        # automatically identifies anything starting with "case_" and
        # runs it.  very similar to unittest auto-identification except
        # we need a different system
        for n, v in self.__class__.__dict__.items():
            if n.startswith("case_") and callable(v):
                try:
                    v(self)
                except SkipCase as e:
                    # TODO(programmerjake): translate to final test sending
                    # skip signal to unittest. for now, just print the skipped
                    # reason and ignore
                    print(f"SKIPPED({n}):", str(e))

    def add_case(self, prog, initial_regs=None, initial_sprs=None,
                 initial_cr=0, initial_msr=0,
                 initial_mem=None,
                 initial_svstate=0):

        test_name = inspect.stack()[1][3]  # name of caller of this function
        tc = TestCase(prog, test_name,
                      regs=initial_regs, sprs=initial_sprs, cr=initial_cr,
                      msr=initial_msr,
                      mem=initial_mem,
                      svstate=initial_svstate)

        self.test_data.append(tc)


class TestCase:
    def __init__(self, program, name, regs=None, sprs=None, cr=0, mem=None,
                 msr=0,
                 do_sim=True,
                 extra_break_addr=None,
                 svstate=0):

        self.program = program
        self.name = name

        if regs is None:
            regs = [0] * 32
        if sprs is None:
            sprs = {}
        if mem is None:
            mem = {}
        self.regs = regs
        self.sprs = sprs
        self.cr = cr
        self.mem = mem
        self.msr = msr
        self.do_sim = do_sim
        self.extra_break_addr = extra_break_addr
        self.svstate = svstate


