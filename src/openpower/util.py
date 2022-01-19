import os
import random
from openpower.consts import FastRegsEnum, StateRegsEnum
from openpower.decoder.power_enums import SPRfull as SPR, spr_dict


# note that we can get away with using SPRfull here because the values
# (numerical values) are what is used for lookup.
spr_to_fast = {
                SPR.LR: FastRegsEnum.LR,
                SPR.CTR: FastRegsEnum.CTR,
                SPR.SRR0: FastRegsEnum.SRR0,
                SPR.SRR1: FastRegsEnum.SRR1,
                SPR.HSRR0: FastRegsEnum.HSRR0,
                SPR.HSRR1: FastRegsEnum.HSRR1,
                SPR.SPRG0_priv: FastRegsEnum.SPRG0,
                SPR.SPRG1_priv: FastRegsEnum.SPRG1,
                SPR.SPRG2_priv: FastRegsEnum.SPRG2,
                SPR.SPRG3: FastRegsEnum.SPRG3,
                SPR.HSPRG0: FastRegsEnum.HSPRG0,
                SPR.HSPRG1: FastRegsEnum.HSPRG1,
                SPR.XER: FastRegsEnum.XER,
                SPR.TAR: FastRegsEnum.TAR,
                SPR.SVSRR0: FastRegsEnum.SVSRR0,
               }

spr_to_state = { SPR.DEC: StateRegsEnum.DEC,
                 SPR.TB: StateRegsEnum.TB,
               }

sprstr_to_state = {}
state_to_spr = {}
for (k, v) in spr_to_state.items():
    sprstr_to_state[k.name] = v
    state_to_spr[v] = k

def state_reg_to_spr(spr_num):
    return state_to_spr[spr_num].value


def spr_to_state_reg(spr_num):
    if not isinstance(spr_num, str):
        spr_num = spr_dict[spr_num].SPR
    return sprstr_to_state.get(spr_num, None)


sprstr_to_fast = {}
fast_to_spr = {}
for (k, v) in spr_to_fast.items():
    sprstr_to_fast[k.name] = v
    fast_to_spr[v] = k

def fast_reg_to_spr(spr_num):
    return fast_to_spr[spr_num].value


def spr_to_fast_reg(spr_num):
    if not isinstance(spr_num, str):
        spr_num = spr_dict[spr_num].SPR
    return sprstr_to_fast.get(spr_num, None)


def slow_reg_to_spr(slow_reg):
    for i, x in enumerate(SPR):
        if slow_reg == i:
            return x.value


def spr_to_slow_reg(spr_num):
    for i, x in enumerate(SPR):
        if spr_num == x.value:
            return i


# TODO: make this a util routine (somewhere)
def mask_extend(x, nbits, repeat):
    res = 0
    extended = (1<<repeat)-1
    for i in range(nbits):
        if x & (1<<i):
            res |= extended << (i*repeat)
    return res


# makes a logarithmically-skewed random number
def log_rand(n, min_val=1):
    logrange = random.randint(1, n)
    return random.randint(min_val, (1 << logrange)-1)


def log(*args, **kwargs):
    """verbose printing, disabled if an ENV VAR "SILENCELOG" exists.
    """
    if 'SILENCELOG' in os.environ:
        return
    print(*args, **kwargs)

