import argparse
import collections
import json
import os
import pathlib
import re


def collect_sysnums(tree):
    whitespace = re.compile(r"\s+")

    number = r"[0-9]+"
    name = r"[A-Za-z0-9_]+"
    identifier = rf"__NR(?:3264)?_{name}"

    def transform(macro_nr_args):
        (macro, nr_args) = macro_nr_args
        args = r",\s*\\*\s*".join([f"({name})"] * nr_args)
        return rf"(?:({macro})\(({identifier}),\s*\\*\s*{args}\))"

    pattern0 = re.compile(rf"^#define\s+({identifier})\s+({number})$", re.M)
    pattern1 = re.compile("|".join(map(transform, {
        "__SC_COMP_3264": 3,
        "__SC_3264": 2,
        "__SC_COMP": 2,
        "__SYSCALL": 1,
    }.items())))

    path = (tree / "include/uapi/asm-generic/unistd.h")
    with open(path, mode="r", encoding="UTF-8") as stream:
        identifiers = {}
        data = stream.read()

        for match in pattern0.finditer(data):
            identifier = match.group(1)
            number = int(match.group(2))
            identifiers[identifier] = number

        for match in pattern1.finditer(data):
            groups = (group for group in match.groups() if group is not None)
            (category, identifier, *entries) = groups
            number = identifiers[identifier]
            identifiers[identifier] = (category, number, tuple(entries))

    for identifier in ("__NR_arch_specific_syscall", "__NR_syscalls"):
        del identifiers[identifier]

    table = {
        "arch32": collections.defaultdict(),
        "arch64": collections.defaultdict(),
    }
    for (identifier, (category, number, entries)) in identifiers.items():
        name = identifier.replace("__NR3264_", "").replace("__NR_", "")
        (entry, entry32, entry64, compat) = ([None] * 4)
        if category == "__SC_COMP_3264":
            (entry32, entry64, compat) = entries
        elif category == "__SC_3264":
            (entry32, entry64) = entries
        elif category == "__SC_COMP":
            (entry, compat) = entries
        else:
            (entry,) = entries

        for abi in table:
            table[abi][number] = (name, [])
            table[abi][name] = number

        if entry is not None:
            table["arch32"][number][1].append(entry)
            table["arch64"][number][1].append(entry)
        if entry64 is not None:
            table["arch64"][number][1].append(entry64)
        if entry32 is not None:
            table["arch32"][number][1].append(entry32)
        if compat is not None:
            table["arch64"][number][1].append(compat)

        for abi in dict(table):
            if not table[abi][number][1]:
                del table[abi][number]
                del table[abi][name]

        yield ("generic", table)

    def parse(path):
        table = collections.defaultdict(dict)
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
                        name = f"compat_sys_{name}"
                    else:
                        name = f"sys_{name}"
                    yield (name, dict(zip(arguments[1::2], arguments[0::2])))


def generate_json(tree):
    tree = tree.expanduser()
    table = {
        "sysnums": dict(collect_sysnums(tree=tree)),
        "sysargs": dict(collect_sysargs(tree=tree)),
    }
    print(json.dumps(table, indent=4))


def main():
    main_parser = argparse.ArgumentParser("lscmg",
        description="Linux system calls mapping generator")
    main_subparsers = main_parser.add_subparsers(dest="generate", required=True)

    json_parser = main_subparsers.add_parser("json")
    json_parser.add_argument("tree",
        help="path to kernel source tree",
        type=pathlib.Path)
    json_parser.set_defaults(generate=generate_json)

    arguments = dict(vars(main_parser.parse_args()))
    generate = arguments.pop("generate")

    return generate(**arguments)


if __name__ == "__main__":
    main()
