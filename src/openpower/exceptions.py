"""exceptions
"""
from nmutil.iocontrol import RecordObject
from nmigen import Signal

# https://bugs.libre-soc.org/show_bug.cgi?id=465
class LDSTException(RecordObject):
    _exc_types = ['alignment', 'instr_fault', 'invalid', 'badtree',
                 'perm_error', 'rc_error', 'segment_fault',
                  'happened', ] # must be last: may overlap with Data.ok
    def __init__(self, name=None):
        RecordObject.__init__(self, name=name)
        for f in self._exc_types:
            setattr(self, f, Signal())

