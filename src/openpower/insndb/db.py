import argparse
import contextlib
import os
import types

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


class SVP64Instruction(Instruction):
    def __new__(cls, string):
        self = super().__new__(cls, string)
        if not self.svp64:
            raise ValueError("illegal SVP64 instruction")
        return self


class BaseVisitor(Visitor):
    def __init__(self, **arguments):
        self.__arguments = types.MappingProxyType(arguments)
        self.__current_db = None
        self.__current_record = None
        self.__current_extra = None
        return super().__init__()

    @property
    def arguments(self):
        return self.__arguments

    @property
    def current_db(self):
        return self.__current_db

    @property
    def current_record(self):
        return self.__current_record

    @property
    def current_extra(self):
        return self.__current_extra

    @contextlib.contextmanager
    def db(self, db):
        self.__current_db = db
        yield db
        self.__current_db = None

    @contextlib.contextmanager
    def record(self, record):
        self.__current_record = record
        yield record
        self.__current_record = None

    @contextlib.contextmanager
    def extra(self, extra):
        self.__current_extra = extra
        yield extra
        self.__current_extra = None


class ListVisitor(BaseVisitor):
    @contextlib.contextmanager
    def record(self, record):
        print(record.name)
        yield record


class InstructionVisitor(BaseVisitor):
    pass


class SVP64InstructionVisitor(InstructionVisitor):
    pass


class OpcodesVisitor(InstructionVisitor):
    @contextlib.contextmanager
    def record(self, record):
        for opcode in record.opcodes:
            print(opcode)


class OperandsVisitor(InstructionVisitor):
    @contextlib.contextmanager
    def record(self, record):
        with super().record(record=record):
            if self.current_record.name == self.arguments["insn"]:
                for operand in record.dynamic_operands:
                    print(operand.name, ",".join(map(str, operand.span)))
                for operand in record.static_operands:
                    if operand.name not in ("PO", "XO"):
                        desc = f"{operand.name}={operand.value}"
                        print(desc, ",".join(map(str, operand.span)))

        yield record


class PCodeVisitor(InstructionVisitor):
    @contextlib.contextmanager
    def record(self, record):
        with super().record(record=record):
            if self.current_record.name == self.arguments["insn"]:
                for line in record.pcode:
                    print(line)


class ExtrasVisitor(SVP64InstructionVisitor):
    @contextlib.contextmanager
    def extra(self, extra):
        with super().extra(extra=extra) as extra:
            if self.current_record.name == self.arguments["insn"]:
                print(extra.name)
                print("    sel", extra.sel)
                print("    reg", extra.reg)
                print("    seltype", extra.seltype)
                print("    idx", extra.idx)
                pass

        yield extra


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

    for (command, (visitor, help)) in commands.items():
        parser = main_subparser.add_parser(command, help=help)
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
    visitor = commands[command][0](**args)

    db = Database(find_wiki_dir())
    db.visit(visitor=visitor)


if __name__ == "__main__":
    main()
