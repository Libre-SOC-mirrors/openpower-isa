import argparse
import contextlib
import os

from openpower.decoder.power_enums import (
    find_wiki_dir,
)
from openpower.insndb.core import (
    Database,
    Visitor,
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


class PCodeVisitor(ConcreteInstructionVisitor):
    def handler(self, record):
        for line in record.pcode:
            print(line)


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
    }

    main_parser = argparse.ArgumentParser()
    main_parser.add_argument("-l", "--log",
        help="activate logging",
        action="store_true",
        default=False)
    main_subparser = main_parser.add_subparsers(dest="command", required=True)

    for (command, (visitor, help)) in commands.items():
        parser = main_subparser.add_parser(command, help=help)
        if issubclass(visitor, ConcreteInstructionVisitor):
            parser.add_argument("insn", type=Instruction,
                metavar="INSN", help="instruction")

    args = vars(main_parser.parse_args())
    command = args.pop("command")
    log = args.pop("log")
    if not log:
        os.environ["SILENCELOG"] = "true"
    visitor = commands[command][0](**args)

    db = Database(find_wiki_dir())
    db.visit(visitor=visitor)


if __name__ == "__main__":
    main()
