"""exceptions
"""
from nmutil.iocontrol import RecordObject
from nmigen import Signal
from collections import namedtuple

exc_types = ['alignment',
             'instr_fault', # this one is not an actual exception
                            # but information *about* the type of
                            # exception that must be generated
             'invalid',
             'badtree',
             'perm_error',
             'rc_error',
             'segment_fault',
             'happened', # must be last: may overlap with Data.ok
            ]

LDSTExceptionTuple = namedtuple("LDSTExceptionTuple", exc_types)

# https://bugs.libre-soc.org/show_bug.cgi?id=465
class LDSTException(RecordObject):
    _exc_types = exc_types
    def __init__(self, name=None):
        RecordObject.__init__(self, name=name)
        for f in self._exc_types:
            setattr(self, f, Signal(name=f))
        self.srr1 = Signal(64)
    length = len(exc_types) + 64 # update this if adding anything else!
