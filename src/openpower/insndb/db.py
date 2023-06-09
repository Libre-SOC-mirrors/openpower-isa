import argparse
import contextlib
import os
import types

from openpower.decoder.power_enums import (
    find_wiki_dir,
)
from openpower.insndb.core import (
    Database,
    Extra,
    Record,
    Records,
    Visitor,
    visit,
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


class ListVisitor(Visitor):
    @contextlib.contextmanager
    def __call__(self, node):
        if isinstance(node, Record):
            print(node.name)
        yield node


class OpcodesVisitor(Visitor):
    @contextlib.contextmanager
    def __call__(self, node):
        if isinstance(node, Record):
            for opcode in node.opcodes:
                print(opcode)
        yield node


class OperandsVisitor(Visitor):
    @contextlib.contextmanager
    def __call__(self, node):
        if isinstance(node, Record):
            for operand in node.dynamic_operands:
                print(operand.name, ",".join(map(str, operand.span)))
            for operand in node.static_operands:
                if operand.name not in ("PO", "XO"):
                    desc = f"{operand.name}={operand.value}"
                    print(desc, ",".join(map(str, operand.span)))
        yield node


class PCodeVisitor(Visitor):
    @contextlib.contextmanager
    def __call__(self, node):
        if isinstance(node, Record):
            for line in node.pcode:
                print(line)
        yield node


class ExtrasVisitor(Visitor):
    @contextlib.contextmanager
    def __call__(self, node):
        if isinstance(node, Extra):
            print(node.name)
            print("    sel", node.sel)
            print("    reg", node.reg)
            print("    seltype", node.seltype)
            print("    idx", node.idx)
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
        if command not in ("list",):
            if command in ("extras",):
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
    records = next(db.subnodes(match=lambda node: isinstance(node, Records)))
    if command in ("list",):
        match = None
    else:
        insn = args.pop("insn")
        def match(record):
            return (isinstance(record, Record) and (record.name == insn))

    for node in records.subnodes(match=match):
        visit(visitor=visitor, node=node)


if __name__ == "__main__":
    main()
