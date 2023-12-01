# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2023 Jacob Lifshay <programmerjake@gmail.com>
# Funded by NLnet http://nlnet.nl
""" simple ELF test cases

related bugs:

* https://bugs.libre-soc.org/show_bug.cgi?id=1169
"""

from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.test.state import ExpectedState
from openpower.test.elf import compile_elf
from openpower.consts import MSR, DEFAULT_MSR

SYSCALL_DEF = r"""
#include <sys/syscall.h>

long syscall(long number, ...);

asm(".globl syscall\n"
    ".p2align 4\n"
    ".type syscall,@function\n"
    "syscall:\n"
    "mr 0,3\n"
    "mr 3,4\n"
    "mr 4,5\n"
    "mr 5,6\n"
    "mr 6,7\n"
    "mr 7,8\n"
    "mr 8,9\n"
    "sc\n"
    "blr");
"""

# we have to specify *all* sprs that our binary might possibly need to
# read, because ISACaller is annoying like that...
# https://bugs.libre-soc.org/show_bug.cgi?id=1226#c2
_INITIAL_SPRS = ('LR', 'CTR', 'TAR', 'SVSTATE', 'SRR0', 'SRR1',
                 'SVSHAPE0', 'SVSHAPE1', 'SVSHAPE2', 'SVSHAPE3')

DEFAULT_USER_MSR = DEFAULT_MSR | (1 << MSR.PR)

class SimpleCases(TestAccumulatorBase):
    def case_hello_world(self):
        prog = compile_elf(SYSCALL_DEF + r"""
void _start() {
    static const char msg[] = "Hello World!\n";
    syscall(SYS_write, 1, (const void *)msg, sizeof(msg) - 1);
    syscall(SYS_exit_group, 0);
}
""")
        self.add_case(prog, initial_sprs=dict.fromkeys(_INITIAL_SPRS, 0),
                      initial_msr=DEFAULT_USER_MSR)

    def case_hello_world_with_data_and_bss(self):
        prog = compile_elf(SYSCALL_DEF + r"""
const char msg_in_ro_data[] = "World!\n";
char msg_in_data[] = "Hello ";
char msg_in_bss[sizeof(msg_in_data)] = {};

void _start() {
    for(int i = 0; i < sizeof(msg_in_data); i++)
        msg_in_bss[i] = msg_in_data[i];
    syscall(SYS_write, 1, (const void *)msg_in_bss, sizeof(msg_in_data) - 1);
    syscall(SYS_write, 1, (const void *)msg_in_ro_data, sizeof(msg_in_ro_data) - 1);
    syscall(SYS_exit_group, 0);
}
""")
        self.add_case(prog, initial_sprs=dict.fromkeys(_INITIAL_SPRS, 0),
                      initial_msr=DEFAULT_USER_MSR)

    def case_just_exit(self):
        prog = compile_elf(SYSCALL_DEF + r"""
void _start() {
    syscall(SYS_exit_group, 0);
}
""")
        self.add_case(prog, initial_sprs=dict.fromkeys(_INITIAL_SPRS, 0),
                      initial_msr=DEFAULT_USER_MSR)
