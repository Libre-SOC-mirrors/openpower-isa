import argparse
import collections
import enum
import functools
import json
import os
import pathlib
import re


def collect_sysnums(tree):
    def parse(path):
        table = collections.defaultdict(dict)
        whitespace = re.compile(r"\s+")
        with open(path, mode="r", encoding="UTF-8") as stream:
            lines = filter(lambda line: not line.strip().startswith("#"), stream)
            for line in filter(bool, map(str.strip, lines)):
                (number, abi, name, *entries) = map(str.strip, whitespace.split(line))
                entries = tuple(entries)
                if len(entries) > 2:
                    raise ValueError(line)
                table[abi][number] = (name, entries)
                table[abi][name] = number

        return table

    tables = (
        ("alpha", "arch/alpha/kernel/syscalls/syscall.tbl"),
        ("arm", "arch/arm/tools/syscall.tbl"),
        ("ia64", "arch/ia64/kernel/syscalls/syscall.tbl"),
        ("m68k", "arch/m68k/kernel/syscalls/syscall.tbl"),
        ("microblaze", "arch/microblaze/kernel/syscalls/syscall.tbl"),
        ("mips-n32", "arch/mips/kernel/syscalls/syscall_n32.tbl"),
        ("mips-n64", "arch/mips/kernel/syscalls/syscall_n64.tbl"),
        ("mips-o32", "arch/mips/kernel/syscalls/syscall_o32.tbl"),
        ("parisc", "arch/parisc/kernel/syscalls/syscall.tbl"),
        ("ppc", "arch/powerpc/kernel/syscalls/syscall.tbl"),
        ("s390", "arch/s390/kernel/syscalls/syscall.tbl"),
        ("sh", "arch/sh/kernel/syscalls/syscall.tbl"),
        ("sparc", "arch/sparc/kernel/syscalls/syscall.tbl"),
        ("x86-32", "arch/x86/entry/syscalls/syscall_32.tbl"),
        ("x86-64", "arch/x86/entry/syscalls/syscall_64.tbl"),
        ("xtensa", "arch/xtensa/kernel/syscalls/syscall.tbl"),
    )
    for (arch, path) in tables:
        yield (arch, parse(path=(tree / path)))


def collect_sysargs(tree):
    pattern = re.compile(r"(COMPAT_)?SYSCALL_DEFINE[0-7]\((.*?)\)", re.S | re.M)
    compat_arg_u64_pattern = re.compile(r"compat_arg_u64_dual\((.+?)\)")

    for (root, _, paths) in os.walk(top=tree):
        root = pathlib.Path(root)
        paths = map(lambda path: (root / path), paths)
        for path in filter(lambda path: path.suffix == ".c", paths):
            with open(path, mode="r", encoding="UTF-8") as stream:
                code = stream.read()
                code = compat_arg_u64_pattern.sub(r"u32, \1_a, u32, \1_b", code)
                for match in pattern.finditer(code):
                    compat = (match.group(1) is not None)
                    match = match.group(2).replace("\t", "").replace("\n", "")
                    (name, *arguments) = map(str.strip, match.split(","))
                    if compat:
                        name = f"compat_{name}"
                    yield (name, dict(zip(arguments[1::2], arguments[0::2])))


def main():
    parser = argparse.ArgumentParser("lscmg",
        description="Linux system calls mapping generator")
    parser.add_argument("tree",
        help="path to kernel source tree",
        type=pathlib.Path)

    arguments = dict(vars(parser.parse_args()))

    tree = arguments.pop("tree")
    tree = tree.expanduser()
    sysnums = dict(collect_sysnums(tree=tree))
    sysargs = dict(collect_sysargs(tree=tree))

    print("SYSNUMS", "=", json.dumps(sysnums, indent=4))
    print("SYSARGS", "=", json.dumps(sysargs, indent=4))


if __name__ == "__main__":
    main()
