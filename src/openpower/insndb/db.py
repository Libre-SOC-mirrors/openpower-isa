import argparse
import contextlib
import sys

from openpower.decoder.power_enums import (
    find_wiki_dir,
)
from openpower.insndb.core import (
    Database,
    Visitor,
)


class BaseVisitor(Visitor):
    def __init__(self, **_):
        pass


class ListVisitor(BaseVisitor):
    @contextlib.contextmanager
    def record(self, record):
        print(record.name)
        yield record


class ConcreteInstructionVisitor(BaseVisitor):
    def __init__(self, insn, **_):
        self.__insn = insn
        return super().__init__()

    def handler(self, record):
        raise NotImplementedError

    @contextlib.contextmanager
    def record(self, record):
        if record.name == self.__insn:
            self.handler(record=record)
        yield record


class OpcodesVisitor(ConcreteInstructionVisitor):
    def handler(self, record):
        for opcode in record.opcodes:
            print(opcode)


class OperandsVisitor(ConcreteInstructionVisitor):
    def handler(self, record):
        for operand in record.dynamic_operands:
            print(operand.name)
        for operand in record.static_operands:
            if operand.name not in ("PO", "XO"):
                print(operand.name, operand.value, sep="=")


def main():
    visitors = {
        "list": ListVisitor,
        "opcodes": OpcodesVisitor,
        "operands": OperandsVisitor,
    }
    main_parser = argparse.ArgumentParser()
    main_subparser = main_parser.add_subparsers(dest="command", required=True)
    main_subparser.add_parser("list",
        help="list all instructions")

    for (command, help) in {
                "opcodes": "print instruction opcodes",
                "operands": "print instruction operands",
            }.items():
        parser = main_subparser.add_parser(command, help=help)
        parser.add_argument("insn", metavar="INSN", help="instruction")

    args = vars(main_parser.parse_args())
    command = args.pop("command")
    visitor = visitors[command](**args)

    db = Database(find_wiki_dir())
    db.visit(visitor=visitor)
