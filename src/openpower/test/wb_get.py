"""useful function for emulating a wishbone interface
"""
from nmigen.sim import Settle

stop = False

def wb_get(wb, mem, name=None):
    """simulator process for emulating wishbone (classic) out of a dictionary
    """
    if name is None:
        name = ""

    global stop
    assert (stop == False)

    while not stop:
        while True: # wait for dc_valid
            if stop:
                return
            cyc = yield (wb.cyc)
            stb = yield (wb.stb)
            if cyc and stb:
                break
            yield
        addr = (yield wb.adr) << 3
        if addr not in mem:
            print ("    %s WB NO entry @ %x, returning zero" % \
                        (name, addr))

        # read or write?
        we = (yield wb.we)
        if we:
            # WRITE
            store = (yield wb.dat_w)
            sel = (yield wb.sel)
            data = mem.get(addr, 0)
            # note we assume 8-bit sel, here
            res = 0
            for i in range(8):
                mask = 0xff << (i*8)
                if sel & (1<<i):
                    res |= store & mask
                else:
                    res |= data & mask
            mem[addr] = res
            print ("    %s WB set %x mask %x data %x" % (name, addr, sel, res))
        else:
            # READ
            data = mem.get(addr, 0)
            yield wb.dat_r.eq(data)
            print ("    %s WB get %x data %x" % (name, addr, data))

        # a dumb "single-ack", this is non-pipeline
        yield wb.ack.eq(1)
        yield
        yield wb.ack.eq(0)
        yield


