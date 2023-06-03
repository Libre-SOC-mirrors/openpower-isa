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


def main():
    visitors = {
        "list": ListVisitor,
        "opcodes": OpcodesVisitor,
    }
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="command", required=True)
    parser_list = subparser.add_parser("list",
        help="list all instructions")
    parser_opcodes = subparser.add_parser("opcodes",
        help="print instruction opcodes")
    parser_opcodes.add_argument("insn",
        metavar="INSN",
        help="instruction")

    args = vars(parser.parse_args())
    command = args.pop("command")
    visitor = visitors[command](**args)

    db = Database(find_wiki_dir())
    db.visit(visitor=visitor)
