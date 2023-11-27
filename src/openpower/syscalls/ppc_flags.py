# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2023 Jacob Lifshay <programmerjake@gmail.com>
# Funded by NLnet http://nlnet.nl
""" flags for PowerPC syscalls

related bugs:

* https://bugs.libre-soc.org/show_bug.cgi?id=1169
"""

def parse_defines(flags, compiler):
    """ parse `#define`s into the dict `flags` using the given `compiler`
    """
    from subprocess import run, PIPE
    inp = """
#include <sys/mman.h>
#include <errno.h>
#include <unistd.h>
#include <sys/syscall.h>
"""
    if isinstance(compiler, str):
        compiler = [compiler]
    out = run([*compiler, '-E', '-dM', '-'], input=inp,
              check=True, stdout=PIPE, encoding='utf-8').stdout
    def_start = '#define '
    defines = {}
    for define in out.splitlines():
        assert define.startswith(def_start)
        define = define[len(def_start):]
        name, space, value = define.partition(' ')
        assert space == ' '
        if not name.isidentifier():
            continue
        defines[name] = value
    # resolve things defined in terms of other things
    more_substitutions = True
    while more_substitutions:
        more_substitutions = False
        for name, value in defines.items():
            new_value = defines.get(value)
            if new_value is not None and new_value != value:
                defines[name] = new_value
                more_substitutions = True
    for name, value in defines.items():
        if value.startswith('(') and value.endswith(')'):
            value = value[1:-2]
        if len(value) > 1 and value.startswith('0') and value[1].isdigit():
            value = '0o' + value[1:]
        try:
            flags[name] = int(value, 0)
        except ValueError:
            pass
    return flags

parse_defines(globals(), 'powerpc64le-linux-gnu-gcc')

def _host_defines():
    import sysconfig
    return parse_defines({}, sysconfig.get_config_var('CC').split(' '))

host_defines = _host_defines()
del _host_defines
