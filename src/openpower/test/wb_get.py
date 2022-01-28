"""useful function for emulating a wishbone interface
"""
from nmigen.sim import Settle

stop = False

def wb_get_classic(wb, mem, name=None):
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


def wb_get(wb, mem, name=None):
    """simulator process for emulating wishbone (pipelined) out of a dictionary
    deliberately do not send back a stall (ever)
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

        next_ack = 0
        addr = 0
        while cyc:
            prev_addr = addr
            addr = (yield wb.adr) << 3
            if addr not in mem:
                print ("    %s WB NO entry @ %x, returning zero" % \
                            (name, addr))

            print ("    %s WB req @ %x" % (name, addr))

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
                print ("    %s WB set %x mask %x data %x" % \
                            (name, addr, sel, res))
            else:
                # READ
                if next_ack:
                    data = mem.get(prev_addr, 0)
                    yield wb.dat_r.eq(data)
                    print ("    %s WB get %x data %x" % \
                                    (name, prev_addr, data))

            # acknowledge previous strobe 1 clock late
            yield wb.ack.eq(next_ack)
            yield
            next_ack = stb
            stb = yield (wb.stb)
            cyc = yield (wb.cyc)

        # clear ack for next cyc
        yield wb.ack.eq(0)


