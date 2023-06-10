import argparse
import contextlib
import os
import types

from openpower.decoder.power_enums import (
    find_wiki_dir,
)
from openpower.insndb.core import (
    Database,
    Dataclass,
    Record,
    Records,
    Tuple,
    Visitor,
    visit,
    visitormethod,
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


class TreeVisitor(Visitor):
    def __init__(self):
        self.__depth = 0
        self.__path = [""]
        return super().__init__()

    @contextlib.contextmanager
    def __call__(self, path, node):
        with super().__call__(path=path, node=node):
            self.__path.append(path)
            print("/".join(self.__path))
            if not isinstance(node, (Dataclass, Tuple)):
                print("    ", repr(node), sep="")
            self.__depth += 1
            yield node
            self.__path.pop(-1)
            self.__depth -= 1


class ListVisitor(Visitor):
    @visitormethod(Record)
    def Record(self, path, node):
        print(node.name)
        yield node


# No use other than checking issubclass and adding an argument.
class InstructionVisitor(Visitor):
    pass

class SVP64InstructionVisitor(InstructionVisitor):
    pass


class OpcodesVisitor(InstructionVisitor):
    @visitormethod(Record)
    def Record(self, path, node):
        for opcode in node.opcodes:
            print(opcode)
        yield node


class OperandsVisitor(InstructionVisitor):
    @visitormethod(Record)
    def Record(self, path, node):
        if isinstance(node, Record):
            for operand in node.dynamic_operands:
                print(operand.name, ",".join(map(str, operand.span)))
            for operand in node.static_operands:
                if operand.name not in ("PO", "XO"):
                    desc = f"{operand.name}={operand.value}"
                    print(desc, ",".join(map(str, operand.span)))
        yield node


class PCodeVisitor(InstructionVisitor):
    @visitormethod(Record)
    def Record(self, path, node):
        if isinstance(node, Record):
            for line in node.pcode:
                print(line)
        yield node


class ExtrasVisitor(SVP64InstructionVisitor):
    @visitormethod(Record)
    def Record(self, path, node):
        for (name, extra) in node.extras.items():
            print(name)
            print("    sel", extra["sel"])
            print("    reg", extra["reg"])
            print("    seltype", extra["seltype"])
            print("    idx", extra["idx"])
        yield node


def main():
    commands = {
        "tree": (
            TreeVisitor,
            "list all records",
        ),
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
        if issubclass(visitor, InstructionVisitor):
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
    (path, records) = next(db.walk(match=lambda pair: isinstance(pair, Records)))
    if not isinstance(visitor, InstructionVisitor):
        match = None
    else:
        insn = args.pop("insn")
        def match(record):
            return (isinstance(record, Record) and (record.name == insn))

    for (subpath, node) in records.walk(match=match):
        visit(visitor=visitor, node=node, path=subpath)


if __name__ == "__main__":
    main()
