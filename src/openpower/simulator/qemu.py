from pygdbmi.gdbcontroller import GdbController
import subprocess

launch_args_be = ['qemu-system-ppc64',
                  '-machine', 'powernv9',
                  '-cpu', 'power9',
                  '-nographic',
                  '-s', '-S', '-m', 'size=4096']

launch_args_le = ['qemu-system-ppc64le',
                  '-machine', 'powernv9',
                  '-cpu', 'power9',
                  '-nographic',
                  '-s', '-S', '-m', 'size=4096']


def swap_order(x, nbytes):
    x = x.to_bytes(nbytes, byteorder='little')
    x = int.from_bytes(x, byteorder='big', signed=False)
    return x


def find_uint128(val):
    #print (val[1:])
    assert val[1:].startswith('uint128 =')
    val = val.split("=")[1]
    val = val.split(',')[0].strip()
    val = int(val, 0)
    val = swap_order(val, 16)
    val = swap_order(val, 8)
    return val


class QemuController:
    def __init__(self, kernel, bigendian):
        if bigendian:
            args = launch_args_be + ['-kernel', kernel]
        else:
            args = launch_args_le + ['-kernel', kernel]
        self.qemu_popen = subprocess.Popen(args,
                                           stdout=subprocess.PIPE,
                                           stdin=subprocess.PIPE)
        self.gdb = GdbController(gdb_path='powerpc64-linux-gnu-gdb')
        self.bigendian = bigendian
        self._reg_cache = {}

    def _rcache_trash(self, key=None):
        """cache of register values, trash it on call to step or continue
        """
        if key is None:
            self._reg_cache = {}
            return
        self._reg_cache.pop(key, None)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.exit()

    def connect(self):
        return self.gdb.write('-target-select remote localhost:1234')

    def set_endian(self, bigendian):
        if bigendian:
            cmd = '-gdb-set endian big'
        else:
            cmd = '-gdb-set endian little'
        return self.gdb.write(cmd)

    def break_address(self, addr):
        cmd = '-break-insert *0x{:x}'.format(addr)
        return self.gdb.write(cmd)

    def delete_breakpoint(self, breakpoint=None):
        breakstring = ''
        if breakpoint:
            breakstring = f' {breakpoint}'
        return self.gdb.write('-break-delete' + breakstring)

    def set_bytes(self, addr, v, wid):
        print("qemu set bytes", hex(addr), hex(v))
        v = swap_order(v, wid)
        faddr = '&{int}0x%x' % addr
        fmt = '"%%0%dx"' % (wid * 2)
        cmd = '-data-write-memory-bytes %s ' + fmt
        res = self.gdb.write(cmd % (faddr, v))
        #print("confirm (byterev'd)", hex(self.get_mem(addr, 8)[0]))

    def set_byte(self, addr, v):
        print("qemu set byte", hex(addr), hex(v))
        faddr = '&{int}0x%x' % addr
        res = self.gdb.write('-data-write-memory-bytes %s "%02x"' % (faddr, v))
        print("confirm", hex(self.get_mem(addr, 1)[0]))

    def get_mem(self, addr, nbytes):
        res = self.gdb.write("-data-read-memory %d u 1 1 %d" %
                             (addr, nbytes))
        print ("get_mem", res)
        for x in res:
            if(x["type"] == "result"):
                l = list(map(int, x['payload']['memory'][0]['data']))
                res = []
                for j in range(0, len(l), 8):
                    b = 0
                    for i, v in enumerate(l[j:j+8]):
                        b += v << (i*8)
                    res.append(b)
                return res
        return None

    def _get_registers(self):
        res = self.gdb.write('-data-list-register-values x')
        self._reg_cache = {}
        for x in res:
            if(x["type"] == "result"):
                assert 'register-values' in x['payload']
                rlist = x['payload']['register-values']
                for rdict in rlist:
                    regnum = int(rdict['number'])
                    regval = rdict['value']
                    #print ("reg get", regnum, rdict)
                    if regval.startswith("{"): # TODO, VSX
                        regval = find_uint128(regval)
                    else:
                        regval = int(regval, 0)
                    self._reg_cache["x %d" % regnum] = regval
        return self._reg_cache

    def _get_register(self, fmt):
        if fmt not in self._reg_cache:
            self._get_registers()
        return self._reg_cache[fmt] # return cached reg value

    def _get_single_register(self, fmt):
        if fmt in self._reg_cache:
            return self._reg_cache[fmt] # return cached reg value
        res = self.gdb.write('-data-list-register-values '+fmt,
                             timeout_sec=1.0)  # increase this timeout if needed
        for x in res:
            if(x["type"] == "result"):
                assert 'register-values' in x['payload']
                res = int(x['payload']['register-values'][0]['value'], 0)
                self._reg_cache[fmt] = res # cache reg value
                return res
                # return swap_order(res, 8)
        return None

    # TODO: use -data-list-register-names instead of hardcoding the values
    def get_pc(self): return self._get_register('x 64')
    def get_msr(self): return self._get_register('x 65')
    def get_cr(self): return self._get_register('x 66')
    def get_lr(self): return self._get_register('x 67')
    def get_ctr(self): return self._get_register('x 68')  # probably
    def get_xer(self): return self._get_register('x 69')
    def get_fpscr(self): return self._get_register('x 70')
    def get_mq(self): return self._get_register('x 71')

    def get_register(self, num):
        return self._get_register('x {}'.format(num))

    def get_gpr(self, num):
        return self.get_register(num)

    def get_fpr(self, num):
        return self.get_register(num+471)

    def set_gpr(self, reg, val):
        self._rcache_trash('x %d' % reg)
        self.gdb_eval('$r%d=%d' % (reg, val))

    def set_fpr(self, reg, val):
        self._rcache_trash('x %d' % (reg+32))
        self._rcache_trash('x %d' % (reg+471))
        # grr, fp set cannot enter raw data
        #val = swap_order(val, 8)
        #val = 1<<31
        valhi = (val >> 32) & 0xffffffff
        vallo = val & 0xffffffff
        res = self.gdb_eval('$vs%d.v4_int32={0,0,0x%x,0x%x}' % \
                            (reg, vallo, valhi))
        #res = self.gdb_eval('$fp%d=1.0')
        #res = self.gdb_eval('$vs%d.uint128=0x%x' % \
        #                    (reg, val))
        print ("set fpr", reg, hex(val), res)
        print ("get fpr", hex(self.get_fpr(reg)))

    def set_pc(self, pc):
        self._rcache_trash('x 64')
        self.gdb_eval('$pc=%d' % pc)

    def set_msr(self, msr):
        self._rcache_trash('x 65')
        self.gdb_eval('$msr=%d' % msr)

    def set_cr(self, cr):
        self._rcache_trash('x 66')
        self.gdb_eval('$cr=%d' % cr)

    def set_lr(self, lr):
        self._rcache_trash('x 67')
        self.gdb_eval('$lr=%d' % lr)

    def step(self):
        self._rcache_trash()
        return self.gdb.write('-exec-step-instruction')

    def gdb_continue(self):
        self._rcache_trash()
        return self.gdb.write('-exec-continue')

    def gdb_eval(self, expr):
        return self.gdb.write(f'-data-evaluate-expression {expr}')

    def exit(self):
        self.gdb.exit()
        self.qemu_popen.kill()
        outs, errs = self.qemu_popen.communicate()
        self.qemu_popen.stdout.close()
        self.qemu_popen.stdin.close()

    def disasm(self, start, end):
        res = self.gdb.write('-data-disassemble -s "%d" -e "%d" -- 0' % \
                        (start, end))
        return res[0]['payload']['asm_insns']

    def upload_mem(self, initial_mem, skip_zeros=False):
        if isinstance(initial_mem, tuple):
            addr, mem = initial_mem # assume 8-byte width
            for j, v in enumerate(mem):
                for i in range(8):
                    # sigh byte-level loads, veery slow
                    self.set_byte(addr+i+j*8, (v >> i*8) & 0xff)
            return
        if isinstance(initial_mem, dict):
            for addr, v in initial_mem.items(): # assume 8-byte width
                if skip_zeros and v == 0:
                    continue
                # sigh byte-level loads, veery slow
                self.set_bytes(addr, v, 8)
            return
        for addr, (v, wid) in initial_mem.items():
            for i in range(wid):
                # sigh byte-level loads, veery slow
                self.set_byte(addr+i, (v >> i*8) & 0xff)


def run_program(program, initial_mem=None, extra_break_addr=None,
                bigendian=False, start_addr=0x20000000, init_endian=True,
                continuous_run=True, initial_sprs=None,
                initial_regs=None, initial_fprs=None):
    q = QemuController(program.binfile.name, bigendian)
    q.connect()
    q.set_endian(init_endian)  # easier to set variables this way

    # Run to the start of the program
    q.set_pc(start_addr)
    pc = q.get_pc()
    print("pc", bigendian, hex(pc))
    q.break_address(start_addr) # set breakpoint at start
    q.gdb_continue()

    # set the MSR bit 63, to set bigendian/littleendian mode
    msr = q.get_msr()
    print("msr", bigendian, hex(msr))
    if bigendian:
        # XXX this is probably wrong
        msr &= ~(1 << 0)
        msr = msr & ((1 << 64)-1)
    else:
        msr |= (1 << 0)
    q.set_msr(msr)
    print("msr set to", hex(msr))

    # set the CR to 0, matching the simulator
    q.set_cr(0)
    # delete the previous breakpoint so loops don't screw things up
    q.delete_breakpoint()

    # allow run to end
    q.break_address(start_addr + program.size())
    # or to trap (not ideal)
    q.break_address(0x700)
    # or to alternative (absolute) address)
    if extra_break_addr is not None:
        q.break_address(extra_break_addr)
    # set endian before SPR set
    q.set_endian(bigendian)

    # upload memory
    if initial_mem:
        q.upload_mem(initial_mem, skip_zeros=True)

    # dump msr after endian set
    msr = q.get_msr()
    print("msr", bigendian, hex(msr), bin(msr))
    # set the MSR bit 13, to set FPU
    if bigendian:
        # XXX this is probably wrong
        msr = msr & ((1 << 53)-1)
    else:
        msr |= (1 << 13)
    #msr = 0x4000000000009

    q.set_msr(msr)
    print("msr set to", hex(msr), bin(msr))

    # upload regs
    if initial_regs:
        for i, reg in enumerate(initial_regs):
            q.set_gpr(i, reg)
    if initial_fprs:
        if isinstance(initial_fprs, dict):
            for i, reg in initial_fprs.items():
                q.set_fpr(i, reg)
        else:
            for i, reg in enumerate(initial_fprs):
                if reg != 0:
                    q.set_fpr(i, reg)

    # can't do many of these - lr, ctr, etc. etc. later, just LR for now
    if initial_sprs:
        lr = initial_sprs.get('lr', None)
        if lr is None:
            lr = initial_sprs.get('LR', None)
        if lr is not None:
            q.set_lr(lr)

    # disassemble and dump
    d = q.disasm(start_addr, start_addr + program.size())
    for line in d:
        print ("qemu disasm", line)

    # start running
    if continuous_run:
        q.gdb_continue()

    return q


if __name__ == '__main__':
    q = QemuController("simulator/qemu_test/kernel.bin", bigendian=True)
    q.connect()
    q.break_address(0x20000000)
    q.gdb_continue()
    print(q.get_gpr(1))
    print(q.step())
    print(q.get_gpr(1))
    q.exit()
