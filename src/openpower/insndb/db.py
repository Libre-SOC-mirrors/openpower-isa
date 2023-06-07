import argparse
import contextlib
import os
import types

from openpower.decoder.power_enums import (
    find_wiki_dir,
)
from openpower.insndb.core import (
    Database,
    Handler,
    Matcher,
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


class ListHandler(Handler):
    @contextlib.contextmanager
    def Record(self, node, depth):
        print(node.name)
        yield node


class InstructionMatcher(Matcher):
    def Record(self, node, depth):
        return (node.name == self["insn"])


class SVP64InstructionMatcher(InstructionMatcher):
    pass


class OpcodesHandler(Handler):
    @contextlib.contextmanager
    def Record(self, node, depth):
        for opcode in node.opcodes:
            print(opcode)
        yield node


class OperandsHandler(Handler):
    @contextlib.contextmanager
    def Record(self, node, depth):
        for operand in node.dynamic_operands:
            print(operand.name, ",".join(map(str, operand.span)))
        for operand in node.static_operands:
            if operand.name not in ("PO", "XO"):
                desc = f"{operand.name}={operand.value}"
                print(desc, ",".join(map(str, operand.span)))
        yield node


class PCodeHandler(Handler):
    @contextlib.contextmanager
    def Record(self, node, depth):
        for line in node.pcode:
            print(line)
        yield node


class ExtrasHandler(Handler):
    @contextlib.contextmanager
    def Extra(self, node, depth):
        print(node.name)
        print("    sel", node.sel)
        print("    reg", node.reg)
        print("    seltype", node.seltype)
        print("    idx", node.idx)
        yield node


def main():
    commands = {
        "list": (
            ListHandler,
            Matcher,
            "list available instructions",
        ),
        "opcodes": (
            OpcodesHandler,
            InstructionMatcher,
            "print instruction opcodes",
        ),
        "operands": (
            OperandsHandler,
            InstructionMatcher,
            "print instruction operands",
        ),
        "pcode": (
            PCodeHandler,
            InstructionMatcher,
            "print instruction pseudocode",
        ),
        "extras": (
            ExtrasHandler,
            InstructionMatcher,
            "print instruction extras (SVP64)",
        ),
    }

    main_parser = argparse.ArgumentParser()
    main_parser.add_argument("-l", "--log",
        help="activate logging",
        action="store_true",
        default=False)
    main_subparser = main_parser.add_subparsers(dest="command", required=True)

    for (command, (handler, matcher, help)) in commands.items():
        parser = main_subparser.add_parser(command, help=help)
        if issubclass(matcher, InstructionMatcher):
            if issubclass(matcher, SVP64InstructionMatcher):
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
    handler = commands[command][0](**args)
    matcher = commands[command][1](**args)

    db = Database(find_wiki_dir())
    visit(handler=handler, matcher=matcher, node=db)


if __name__ == "__main__":
    main()
