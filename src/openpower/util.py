from openpower.consts import FastRegsEnum
from openpower.decoder.power_enums import SPRfull as SPR, spr_dict

# note that we can get away with using SPRfull here because the values
# (numerical values) are what is used for lookup.
spr_to_fast = { SPR.CTR: FastRegsEnum.CTR,
                SPR.LR: FastRegsEnum.LR,
                SPR.TAR: FastRegsEnum.TAR,
                SPR.SRR0: FastRegsEnum.SRR0,
                SPR.SRR1: FastRegsEnum.SRR1,
                SPR.XER: FastRegsEnum.XER,
                SPR.DEC: FastRegsEnum.DEC,
                SPR.TB: FastRegsEnum.TB,
               }

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
    

