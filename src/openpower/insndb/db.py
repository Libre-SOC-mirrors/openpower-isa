import argparse
import contextlib
import sys

from openpower.decoder.power_enums import (
    find_wiki_dir,
)
from openpower.insndb.types import (
    Database,
    Visitor,
)


def main():
    class GenericVisitor(Visitor):
        def __init__(self, **_):
            pass

    class ListVisitor(GenericVisitor):
        @contextlib.contextmanager
        def record(self, record):
            print(record.name)
            yield record

    class OpcodesVisitor(GenericVisitor):
        def __init__(self, insn, **_):
            self.__insn = insn
            return super().__init__()

        @contextlib.contextmanager
        def record(self, record):
            if record.name == self.__insn:
                for opcode in record.opcodes:
                    print(opcode)
            yield record

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
