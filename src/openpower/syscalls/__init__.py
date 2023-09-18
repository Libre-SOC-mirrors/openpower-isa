import ctypes
import functools
import inspect
import json
import pathlib


class Dispatcher:
    def __init__(self, guest, host, logger=None, table=None):
        if table is None:
            path = pathlib.Path(inspect.getfile(self.__class__))
            path = (path.parent / "syscalls.json")
            with open(path, "r", encoding="UTF-8") as stream:
                table = json.load(stream)
        if not isinstance(table, dict):
            raise ValueError("dict instance expected")
        if "sysnums" not in table or "sysargs" not in table:
            raise ValueError("sysnums and sysargs keys expected")

        if logger is None:
            logger = lambda *args, **kwargs: None

        def i386(sysnums):
            yield from sysnums["x86-32"]["i386"].items()

        def amd64(sysnums):
            yield from sysnums["x86-64"]["common"].items()
            yield from sysnums["x86-64"]["64"].items()

        def ppc(sysnums):
            yield from sysnums["ppc"]["nospu"].items()
            yield from sysnums["ppc"]["common"].items()
            yield from sysnums["ppc"]["32"].items()

        def ppc64(sysnums):
            yield from sysnums["ppc"]["nospu"].items()
            yield from sysnums["ppc"]["common"].items()
            yield from sysnums["ppc"]["64"].items()

        arch = {
            "i386": i386,
            "amd64": amd64,
            "ppc": ppc,
            "ppc64": ppc64,
        }
        sysnums = table["sysnums"]
        sysargs = table["sysargs"]

        self.__guest = dict(arch[guest](sysnums))
        self.__host = dict(arch[host](sysnums))
        self.__parameters = sysargs
        self.__logger = logger
        self.__libc = ctypes.CDLL(None)

        return super().__init__()

    def __getattr__(self, entry):
        if entry.startswith("compat_sys_"):
            identifier = entry[len("compat_sys_"):]
        elif entry.startswith("sys_"):
            identifier = entry[len("sys_"):]
        else:
            raise AttributeError(entry)

        if entry not in self.__parameters:
            raise AttributeError(entry)

        if identifier not in self.__guest:
            raise AttributeError(entry)
        identifier = int(self.__guest[identifier])

        def syscall(identifier, *arguments):
            parameters = tuple(self.__parameters[entry].items())
            if len(arguments) != len(parameters):
                raise ValueError("conflict between arguments and parameters")

            identifier = str(identifier)
            identifier = self.__guest[identifier][0]
            guest = int(self.__guest[identifier])
            host = int(self.__host[identifier])
            self.__logger(f"{identifier} {guest} => {host}")
            for index in range(len(arguments)):
                value = arguments[index]
                if not isinstance(value, int):
                    raise ValueError("integer argument expected")
                name = parameters[index][0]
                ctype = parameters[index][1]
                self.__logger(f"    0x{value:016x} {name} ({ctype})")

            syscall = self.__libc.syscall
            syscall.restype = ctypes.c_long
            syscall.argtypes = ([ctypes.c_long] * len(arguments))

            return int(syscall(ctypes.c_ulong(host)))

        return functools.partial(syscall, identifier)

    def __call__(self, identifier, *arguments):
        if not isinstance(identifier, int):
            raise ValueError(identifier)

        identifier = str(identifier)
        entry = self.__guest[identifier][1][0]
        syscall = getattr(self, entry)

        return syscall(*arguments)
