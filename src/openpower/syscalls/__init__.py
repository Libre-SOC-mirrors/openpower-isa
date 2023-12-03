import ctypes
import errno
import inspect
import json
import pathlib
from openpower.util import log, LogType


def architecture(arch, bits=0):
    assert bits in (0, 32, 64)
    multilib = {
        ("aarch64", 32): "arm",
        ("amd64", 32): "i386",
        ("ppc64", 32): "ppc",
    }
    arch = {
        "powerpc": "ppc",
        "powerpc64": "ppc64",
        "ppc64le": "ppc64",
        "i686": "i386",
        "x86_64": "amd64",
        "x64": "amd64",
        "arm64": "aarch64",
        "aarch64_be": "aarch64",
        "armv8b": "aarch64",
        "armv8l": "aarch64",
    }.get(arch, arch)

    return multilib.get((arch, bits), arch)


class Syscall:
    def __init__(self, entry, guest, host, parameters):
        if not isinstance(entry, str):
            raise ValueError(entry)
        if not isinstance(guest, int):
            raise ValueError(guest)
        if not isinstance(parameters, tuple):
            raise ValueError(parameters)

        self.__entry = entry
        self.__guest = guest
        self.__host = host
        self.__parameters = parameters

        return super().__init__()

    @property
    def entry(self):
        return self.__entry

    @property
    def guest(self):
        return self.__guest

    @property
    def host(self):
        return self.__host

    def __len__(self):
        return len(self.__parameters)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.entry} {self.guest}=>{self.host})"

    def __call__(self, *arguments):
        if len(arguments) < len(self):
            raise ValueError("conflict between arguments and parameters")

        for index in range(len(arguments)):
            value = arguments[index]
            if not isinstance(value, int):
                raise ValueError("integer argument expected")

        libc = ctypes.CDLL(None)
        syscall = libc.syscall
        restype = syscall.restype
        argtypes = syscall.argtypes
        syscall.restype = ctypes.c_long
        syscall.argtypes = ([ctypes.c_long] * len(arguments))
        res = int(syscall(ctypes.c_long(self.host), *map(ctypes.c_long, arguments)))
        syscall.restype = restype
        syscall.argtypes = argtypes
        return res


class UnimplementedSyscall(Syscall):
    def __init__(self, guest):
        return super().__init__(entry="sys_ni_syscall", guest=guest, host=-1, parameters=tuple())

    def __call__(self, *arguments):
        return -errno.ENOSYS


class UnknownSyscall(Syscall):
    def __init__(self, entry, guest):
        return super().__init__(entry=entry, guest=guest, host=-1, parameters=tuple())

    def __call__(self, *arguments):
        raise NotImplemented


class Dispatcher:
    def __init__(self, guest, host, logger=None, table=None):
        if table is None:
            path = (pathlib.Path(__file__).parent / "syscalls.json")
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

        def arm(sysnums):
            yield from sysnums["arm"]["common"].items()

        def aarch64(sysnums):
            yield from sysnums["generic"]["arch64"].items()

        def ppc(sysnums):
            yield from sysnums["ppc"]["nospu"].items()
            yield from sysnums["ppc"]["common"].items()
            yield from sysnums["ppc"]["32"].items()

        def ppc64(sysnums):
            yield from sysnums["ppc"]["nospu"].items()
            yield from sysnums["ppc"]["common"].items()
            yield from sysnums["ppc"]["64"].items()

        def riscv32(sysnums):
            yield from sysnums["generic"]["arch32"].items()

        def riscv64(sysnums):
            yield from sysnums["generic"]["arch64"].items()

        arch = {
            "i386": i386,
            "amd64": amd64,
            "arm": arm,
            "aarch64": aarch64,
            "ppc": ppc,
            "ppc64": ppc64,
            "riscv32": riscv32,
            "riscv64": riscv64,
        }
        if guest not in arch:
            raise ValueError(guest)
        if host not in arch:
            raise ValueError(host)

        sysnums = table["sysnums"]
        sysargs = table["sysargs"]

        self.__guest = dict(arch[guest](sysnums))
        self.__host = dict(arch[host](sysnums))
        self.__parameters = sysargs
        self.__logger = logger
        self.__libc = ctypes.CDLL(None)

        return super().__init__()

    def __iter__(self):
        identifiers = sorted(map(int, filter(str.isnumeric, self.__guest)))
        for identifier in identifiers:
            entry = self.__guest[str(identifier)][1][0]
            name = self.__guest[str(identifier)][0]
            syscall = getattr(self, entry, None)
            if syscall is None:
                if entry == "sys_ni_syscall":
                    syscall = UnimplementedSyscall(guest=identifier)
                else:
                    syscall = UnknownSyscall(entry=entry, guest=identifier)
            yield syscall

    def __getitem__(self, identifier):
        if not isinstance(identifier, int):
            raise ValueError(identifier)

        identifier = str(identifier)
        entry = self.__guest[identifier][1][0]

        log("syscalls.Dispatcher[%s] (%s)" % (identifier, entry),
            kind=LogType.InstrInOuts)

        return getattr(self, entry)

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

        if identifier not in self.__host:
            raise AttributeError(entry)

        guest = int(self.__guest[identifier])
        host = int(self.__host[identifier])
        parameters = tuple(self.__parameters[entry].items())

        return Syscall(entry=entry, guest=guest, host=host, parameters=parameters)

    def __call__(self, identifier, *arguments):
        syscall = self[identifier]

        return syscall(*arguments)
