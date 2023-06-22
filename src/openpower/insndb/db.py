import argparse
import contextlib
import os

import mdis.dispatcher
import mdis.visitor
import mdis.walker

from openpower.decoder.power_enums import (
    find_wiki_dir,
)
from openpower.insndb.core import (
    Database,
    PCode,
    Operands,
    Record,
    SVP64Record,
    Walker,
)
from openpower.decoder.power_enums import (
    SVEType,
    SVPType,
    SVExtra,
    In1Sel,
    In2Sel,
    In3Sel,
    OutSel,
    CRInSel,
    CRIn2Sel,
    CROutSel,
)


class Instruction(str):
    def __new__(cls, string):
        svp64 = False
        if string.startswith("sv."):
            string = string[len("sv."):]
            svp64 = True
        self = super().__new__(cls, string)
        self.__svp64 = svp64
        return self

    @property
    def svp64(self):
        return self.__svp64


class SVP64Instruction(Instruction):
    def __new__(cls, string):
        self = super().__new__(cls, string)
        if not self.svp64:
            raise ValueError("illegal SVP64 instruction")
        return self


class ListVisitor(mdis.visitor.ContextVisitor):
    @mdis.dispatcher.Hook(Record)
    @contextlib.contextmanager
    def dispatch_record(self, node):
        print(node.name)
        yield node


# No use other than checking issubclass and adding an argument.
class InstructionVisitor(mdis.visitor.ContextVisitor):
    pass

class SVP64InstructionVisitor(InstructionVisitor):
    pass


class OpcodesVisitor(InstructionVisitor):
    @mdis.dispatcher.Hook(Record)
    @contextlib.contextmanager
    def dispatch_record(self, node):
        for opcode in node.opcodes:
            print(opcode)
        yield node


class OperandsVisitor(InstructionVisitor):
    def __init__(self):
        self.__record = None
        return super().__init__()

    @mdis.dispatcher.Hook(Record)
    @contextlib.contextmanager
    def dispatch_record(self, node):
        self.__record = node
        yield node

    @mdis.dispatcher.Hook(Operands)
    @contextlib.contextmanager
    def dispatch_operands(self, node):
        for (cls, kwargs) in node:
            operand = cls(record=self.__record, **kwargs)
            print(operand.name, ", ".join(map(str, operand.span)))
        yield node


class PCodeVisitor(InstructionVisitor):
    @mdis.dispatcher.Hook(PCode)
    @contextlib.contextmanager
    def dispatch_record(self, node):
        for line in node:
            print(line)
        yield node


class SelectorsVisitor(InstructionVisitor):
    @mdis.dispatcher.Hook(
            In1Sel, In2Sel, In3Sel, CRInSel, CRIn2Sel,
            OutSel, CROutSel,
        )
    @contextlib.contextmanager
    def dispatch_selector(self, node):
        typename = node.__class__.__name__
        typename = typename.replace("CR", "CR_")
        typename = typename.replace("Sel", "")
        typename = typename.lower()
        print(typename, node)
        yield node


class ETypeVisitor(SVP64InstructionVisitor):
    @mdis.dispatcher.Hook(SVEType)
    @contextlib.contextmanager
    def dispatch_ptype(self, node):
        print(node)
        yield node


class PTypeVisitor(SVP64InstructionVisitor):
    @mdis.dispatcher.Hook(SVPType)
    @contextlib.contextmanager
    def dispatch_ptype(self, node):
        print(node)
        yield node


class ExtrasVisitor(SVP64InstructionVisitor, SelectorsVisitor):
    @mdis.dispatcher.Hook(SVP64Record.ExtraMap)
    @contextlib.contextmanager
    def dispatch_extramap(self, node):
        self.__index = -1
        yield node

    @mdis.dispatcher.Hook(SVP64Record.ExtraMap.Extra)
    @contextlib.contextmanager
    def dispatch_extramap_extra(self, node):
        self.__index += 1
        yield node

    @mdis.dispatcher.Hook(SVP64Record.ExtraMap.Extra.Entry)
    @contextlib.contextmanager
    def dispatch_extramap_extra_entry(self, node):
        idxmap = (
            SVExtra.Idx0,
            SVExtra.Idx1,
            SVExtra.Idx2,
            SVExtra.Idx3,
        )
        print(idxmap[self.__index], node)
        yield node


def main():
    commands = {
        "list": (
            ListVisitor,
            "list available instructions",
        ),
        "opcodes": (
            OpcodesVisitor,
            "print instruction opcodes",
        ),
        "operands": (
            OperandsVisitor,
            "print instruction operands",
        ),
        "pcode": (
            PCodeVisitor,
            "print instruction pseudocode",
        ),
        "selectors": (
            SelectorsVisitor,
            "print instruction selectors",
        ),
        "etype": (
            ETypeVisitor,
            "print instruction etype",
        ),
        "ptype": (
            PTypeVisitor,
            "print instruction ptype",
        ),
        "extras": (
            ExtrasVisitor,
            "print instruction extras (SVP64)",
        ),
    }

    main_parser = argparse.ArgumentParser()
    main_parser.add_argument("-l", "--log",
        help="activate logging",
        action="store_true",
        default=False)
    main_subparser = main_parser.add_subparsers(dest="command", required=True)

    for (command, (visitor, helper)) in commands.items():
        parser = main_subparser.add_parser(command, help=helper)
        if issubclass(visitor, InstructionVisitor):
            if issubclass(visitor, SVP64InstructionVisitor):
                arg_cls = SVP64Instruction
            else:
                arg_cls = Instruction
            parser.add_argument("insn", type=arg_cls,
                metavar="INSN", help="instruction")

    args = vars(main_parser.parse_args())
    command = args.pop("command")
    log = args.pop("log")
    if not log:
        os.environ["SILENCELOG"] = "true"
    visitor = commands[command][0]()

    db = Database(find_wiki_dir())
    if not isinstance(visitor, InstructionVisitor):
        root = db
    else:
        root = [db[args.pop("insn")]]

    walker = Walker()
    for (node, *_) in walker(root):
        with visitor(node):
            pass


if __name__ == "__main__":
    main()
