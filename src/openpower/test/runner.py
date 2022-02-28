"""TestRunner class, part of the Test API

SPDX-License: LGPLv2+

Copyright (C) 2020,2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
Copyright (C) 2021 Kyle Lehman <klehman9@comcast.net>
Copyright (C) 2021 Jonathan Neuschäfer <j.neuschaefer@gmx.net>
Copyright (C) 2021 Tobias Platen <tplaten@posteo.de>
Copyright (C) 2021 Cesar Strauss <cestrauss@gmail.com>

related bugs:

 * https://bugs.libre-soc.org/show_bug.cgi?id=363
 * https://bugs.libre-soc.org/show_bug.cgi?id=686#c51
"""

from nmigen import Module, ClockSignal
from copy import copy, deepcopy
from pprint import pprint

# NOTE: to use cxxsim, export NMIGEN_SIM_MODE=cxxsim from the shell
# Also, check out the cxxsim nmigen branch, and latest yosys from git
from nmutil.sim_tmp_alternative import Simulator, Settle

from nmutil.formaltest import FHDLTestCase
from nmutil.gtkw import write_gtkw
from openpower.decoder.isa.all import ISA
from openpower.endian import bigendian

from openpower.decoder.power_decoder2 import PowerDecode2

from soc.config.test.test_loadstore import TestMemPspec
from nmutil.util import wrap
from openpower.test.wb_get import wb_get
import openpower.test.wb_get as wbget
from openpower.test.state import TestState, StateRunner, ExpectedState


class SimRunner(StateRunner):
    """SimRunner:  Implements methods for the setup, preparation, and
    running of tests using ISACaller simulation
    """
    def __init__(self, dut, m, pspec):
        super().__init__("sim", SimRunner)
        self.dut = dut

        self.mmu = pspec.mmu == True
        regreduce_en = pspec.regreduce_en == True
        self.simdec2 = simdec2 = PowerDecode2(None, regreduce_en=regreduce_en)
        m.submodules.simdec2 = simdec2  # pain in the neck

    def prepare_for_test(self, test):
        self.test = test
        if False:
            yield

    def run_test(self, instructions, gen, insncode):
        """run_sim_state - runs an ISACaller simulation
        """

        dut, test, simdec2 = self.dut, self.test, self.simdec2
        sim_states = []

        # set up the Simulator (which must track TestIssuer exactly)
        sim = ISA(simdec2, test.regs, test.sprs, test.cr, test.mem,
                  test.msr,
                  initial_insns=gen, respect_pc=True,
                  disassembly=insncode,
                  bigendian=bigendian,
                  initial_svstate=test.svstate,
                  mmu=self.mmu)

        # run the loop of the instructions on the current test
        index = sim.pc.CIA.value//4
        while index < len(instructions):
            ins, code = instructions[index]

            print("sim instr: 0x{:X}".format(ins & 0xffffffff))
            print(index, code)

            # set up simulated instruction (in simdec2)
            try:
                yield from sim.setup_one()
            except KeyError:  # instruction not in imem: stop
                break
            yield Settle()

            # call simulated operation
            print("sim", code)
            yield from sim.execute_one()
            yield Settle()
            index = sim.pc.CIA.value//4

            # get sim register and memory TestState, add to list
            state = yield from TestState("sim", sim, dut, code)
            sim_states.append(state)

        if self.dut.allow_overlap:
            # get last state, at end of run
            state = yield from TestState("sim", sim, dut, code)
            sim_states.append(state)

        return sim_states


class TestRunnerBase(FHDLTestCase):
    """TestRunnerBase:  Sets up and executes the running of tests
    contained in tst_data. run_hdl (if provided) is an HDLRunner
    object.  If not provided, hdl simulation is skipped.

    ISACaller simulation can be skipped by setting run_sim=False.

    When using an Expected state to test with, the expected state
    is passed in with tst_data.
    """
    def __init__(self, tst_data, microwatt_mmu=False, rom=None,
                        svp64=True, run_hdl=None, run_sim=True,
                        allow_overlap=False, inorder=False):
        super().__init__("run_all")
        self.test_data = tst_data
        self.microwatt_mmu = microwatt_mmu
        self.rom = rom
        self.svp64 = svp64
        self.allow_overlap = allow_overlap
        self.inorder = inorder
        self.run_hdl = run_hdl
        self.run_sim = run_sim

    def run_all(self):
        m = Module()
        comb = m.d.comb
        if self.microwatt_mmu:
            # do not wire these up to anything if wb_get is to be used
            if self.rom is not None:
                ldst_ifacetype = 'mmu_cache_wb'
                imem_ifacetype = 'mmu_cache_wb'
            else:
                ldst_ifacetype = 'test_mmu_cache_wb'
                imem_ifacetype = 'test_bare_wb'
        else:
            ldst_ifacetype = 'test_bare_wb'
            imem_ifacetype = 'test_bare_wb'

        pspec = TestMemPspec(ldst_ifacetype=ldst_ifacetype,
                             imem_ifacetype=imem_ifacetype,
                             addr_wid=64,
                             mask_wid=8,
                             XLEN=64,
                             imem_reg_wid=64,
                             # wb_data_width=32,
                             use_pll=False,
                             nocore=False,
                             xics=False,
                             gpio=False,
                             regreduce=not self.allow_overlap,
                             core_domain="sync", # no alternative domain
                             svp64=self.svp64,
                             allow_overlap=self.allow_overlap,
                             inorder=self.inorder,
                             mmu=self.microwatt_mmu,
                             reg_wid=64)

        ###### SETUP PHASE #######
        # Determine the simulations needed and add to state_list
        # for setup and running
        # The methods contained in the respective Runner classes are
        # called using this list when possible

        # allow wb_get to run
        if self.rom is not None:
            wbget.stop = False

        state_list = []

        if self.run_hdl:
            hdlrun = self.run_hdl(self, m, pspec)
            state_list.append(hdlrun)

        if self.run_sim:
            simrun = SimRunner(self, m, pspec)
            state_list.append(simrun)

        # run core clock at same rate as test clock
        # XXX this has to stay here! TODO, work out why,
        # but Simulation-only fails without it
        intclk = ClockSignal("coresync")
        comb += intclk.eq(ClockSignal())
        dbgclk = ClockSignal("dbgsync")
        comb += dbgclk.eq(ClockSignal())

        # nmigen Simulation - everything runs around this, so it
        # still has to be created.
        sim = Simulator(m)
        sim.add_clock(1e-6)

        def process():

            ###### PREPARATION PHASE AT START OF RUNNING #######

            for runner in state_list:
                yield from runner.setup_during_test()

            # get each test, completely reset the core, and run it

            for test in self.test_data:

                with self.subTest(test.name):

                    ###### PREPARATION PHASE AT START OF TEST #######

                    # HACK: if there is test memory and wb_get is in use,
                    # overwrite (reset) the wb_get memory dictionary with
                    # the test's memory contents (oh, and put the wb_get
                    # memory back in as well)
                    self.default_mem.clear()
                    if self.rom is not None:
                        self.default_mem.update(deepcopy(self.rom))
                    if test.mem is not None:
                        self.default_mem.update(deepcopy(test.mem))

                    for runner in state_list:
                        yield from runner.prepare_for_test(test)

                    print(test.name)
                    program = test.program
                    print("regs", test.regs)
                    print("sprs", test.sprs)
                    print("cr", test.cr)
                    print("mem", test.mem)
                    print("msr", test.msr)
                    print("assem", program.assembly)
                    gen = list(program.generate_instructions())
                    insncode = program.assembly.splitlines()
                    instructions = list(zip(gen, insncode))

                    ###### RUNNING OF EACH TEST #######
                    # StateRunner.step_test()

                    # Run two tests (TODO, move these to functions)
                    # * first the Simulator, collate a batch of results
                    # * then the HDL, likewise
                    #   (actually, the other way round because running
                    #    Simulator somehow modifies the test state!)
                    # * finally, compare all the results

                    # TODO https://bugs.libre-soc.org/show_bug.cgi?id=686#c73

                    ##########
                    # 1. HDL
                    ##########
                    if self.run_hdl:
                        hdl_states = yield from hdlrun.run_test(instructions)

                    ##########
                    # 2. Simulator
                    ##########

                    if self.run_sim:
                        sim_states = yield from simrun.run_test(
                                                          instructions, gen,
                                                          insncode)

                    ###### COMPARING THE TESTS #######

                    ###############
                    # 3. Compare
                    ###############

                    # TODO: here just grab one entry from list_of_sim_runners
                    # (doesn't matter which one, honestly)
                    # TODO https://bugs.libre-soc.org/show_bug.cgi?id=686#c73

                    if self.run_sim:
                        last_sim = copy(sim_states[-1])
                    elif self.run_hdl:
                        last_sim = copy(hdl_states[-1])
                    else:
                        last_sim = None # err what are you doing??

                    if self.run_hdl:
                        print ("hdl_states")
                        for state in hdl_states:
                            print (state)

                    if self.run_sim:
                        print ("sim_states")
                        for state in sim_states:
                            print (state)

                    # compare the states
                    if self.run_hdl and self.run_sim:
                        # if allow_overlap is enabled, because allow_overlap
                        # can commit out-of-order, only compare the last ones
                        if self.allow_overlap:
                            print ("allow_overlap: truncating %d %d "
                                    "states to last" % (len(sim_states),
                                                        len(hdl_states)))
                            sim_states = sim_states[-1:]
                            hdl_states = hdl_states[-1:]
                            sim_states[-1].dump_state_tofile()
                            print ("allow_overlap: last hdl_state")
                            hdl_states[-1].dump_state_tofile()
                        for simstate, hdlstate in zip(sim_states, hdl_states):
                            simstate.compare(hdlstate)     # register check
                            simstate.compare_mem(hdlstate) # memory check

                    # if no expected, create /tmp/case_name.py with code
                    # setting expected state to last_sim
                    if test.expected is None:
                        last_sim.dump_state_tofile(test.name, test.test_file)

                    # compare against expected results
                    if test.expected is not None:
                        # have to put these in manually
                        test.expected.to_test = test.expected
                        test.expected.dut = self
                        test.expected.state_type = "expected"
                        test.expected.code = 0
                        # do actual comparison, against last item
                        last_sim.compare(test.expected)

                    # check number of instructions run (sanity)
                    if self.run_hdl and self.run_sim:
                        n_hdl = len(hdl_states)
                        n_sim = len(sim_states)
                        self.assertTrue(n_hdl == n_sim,
                                    "number of instructions %d %d "
                                    "run not the same" % (n_hdl, n_sim))

                ###### END OF A TEST #######
                # StateRunner.end_test()

                for runner in state_list:
                    yield from runner.end_test() # TODO, some arguments?

            ###### END OF EVERYTHING (but none needs doing, still call fn) ####
            # StateRunner.cleanup()

            for runner in state_list:
                yield from runner.cleanup() # TODO, some arguments?

            # finally stop wb_get from going
            if self.rom is not None:
                wbget.stop = True

        styles = {
            'dec': {'base': 'dec'},
            'bin': {'base': 'bin'},
            'closed': {'closed': True}
        }

        traces = [
            'clk',
            ('state machines', 'closed', [
                'fetch_pc_i_valid', 'fetch_pc_o_ready',
                'fetch_fsm_state',
                'fetch_insn_o_valid', 'fetch_insn_i_ready',
                'pred_insn_i_valid', 'pred_insn_o_ready',
                'fetch_predicate_state',
                'pred_mask_o_valid', 'pred_mask_i_ready',
                'issue_fsm_state',
                'exec_insn_i_valid', 'exec_insn_o_ready',
                'exec_fsm_state',
                'exec_pc_o_valid', 'exec_pc_i_ready',
                'insn_done', 'core_stop_o', 'pc_i_ok', 'pc_changed',
                'is_last', 'dec2.no_out_vec']),
            {'comment': 'fetch and decode'},
            (None, 'dec', [
                'cia[63:0]', 'nia[63:0]', 'pc[63:0]', 'msr[63:0]',
                'cur_pc[63:0]', 'core_core_cia[63:0]']),
            'raw_insn_i[31:0]',
            'raw_opcode_in[31:0]', 'insn_type', 'dec2.dec2_exc_happened',
            ('svp64 decoding', 'closed', [
                'svp64_rm[23:0]', ('dec2.extra[8:0]', 'bin'),
                'dec2.sv_rm_dec.mode', 'dec2.sv_rm_dec.predmode',
                'dec2.sv_rm_dec.ptype_in',
                'dec2.sv_rm_dec.dstpred[2:0]', 'dec2.sv_rm_dec.srcpred[2:0]',
                'dstmask[63:0]', 'srcmask[63:0]',
                'dregread[4:0]', 'dinvert',
                'sregread[4:0]', 'sinvert',
                'core.int.pred__addr[4:0]', 'core.int.pred__data_o[63:0]',
                'core.int.pred__ren']),
            ('register augmentation', 'dec', 'closed', [
                {'comment': 'v3.0b registers'},
                'dec2.dec_o.RT[4:0]',
                'dec2.dec_a.RA[4:0]',
                'dec2.dec_b.RB[4:0]',
                ('Rdest', [
                    'dec2.o_svdec.reg_in[4:0]',
                    ('dec2.o_svdec.spec[2:0]', 'bin'),
                    'dec2.o_svdec.reg_out[6:0]']),
                ('Rsrc1', [
                    'dec2.in1_svdec.reg_in[4:0]',
                    ('dec2.in1_svdec.spec[2:0]', 'bin'),
                    'dec2.in1_svdec.reg_out[6:0]']),
                ('Rsrc1', [
                    'dec2.in2_svdec.reg_in[4:0]',
                    ('dec2.in2_svdec.spec[2:0]', 'bin'),
                    'dec2.in2_svdec.reg_out[6:0]']),
                {'comment': 'SVP64 registers'},
                'dec2.rego[6:0]', 'dec2.reg1[6:0]', 'dec2.reg2[6:0]'
            ]),
            {'comment': 'svp64 context'},
            'core_core_vl[6:0]', 'core_core_maxvl[6:0]',
            'core_core_srcstep[6:0]', 'next_srcstep[6:0]',
            'core_core_dststep[6:0]',
            {'comment': 'issue and execute'},
            'core.core_core_insn_type',
            (None, 'dec', [
                'core_rego[6:0]', 'core_reg1[6:0]', 'core_reg2[6:0]']),
            'issue_i', 'busy_o',
            {'comment': 'dmi'},
            'dbg.dmi_req_i', 'dbg.dmi_ack_o',
            {'comment': 'instruction memory'},
            'imem.sram.rdport.memory(0)[63:0]',
            {'comment': 'registers'},
            # match with soc.regfile.regfiles.IntRegs port names
            'core.int.rp_src1.memory(0)[63:0]',
            'core.int.rp_src1.memory(1)[63:0]',
            'core.int.rp_src1.memory(2)[63:0]',
            'core.int.rp_src1.memory(3)[63:0]',
            'core.int.rp_src1.memory(4)[63:0]',
            'core.int.rp_src1.memory(5)[63:0]',
            'core.int.rp_src1.memory(6)[63:0]',
            'core.int.rp_src1.memory(7)[63:0]',
            'core.int.rp_src1.memory(9)[63:0]',
            'core.int.rp_src1.memory(10)[63:0]',
            'core.int.rp_src1.memory(13)[63:0]',
            # Exceptions: see list archive for description of the chain
            # http://lists.libre-soc.org/pipermail/libre-soc-dev/2021-December/004220.html
            ('exceptions', 'closed', [
                'exc_happened',
                'pdecode2.exc_happened',
                'core.exc_happened',
                'core.fus.ldst0.exc_o_happened']),
        ]

        # PortInterface module path varies depending on MMU option
        if self.microwatt_mmu:
            pi_module = 'core.ldst0'
        else:
            pi_module = 'core.fus.ldst0'

        traces += [('ld/st port interface', {'submodule': pi_module}, [
            'oper_r__insn_type',
            'oper_r__msr[63:0]',
            'ldst_port0_is_ld_i',
            'ldst_port0_is_st_i',
            'ldst_port0_busy_o',
            'ldst_port0_addr_i[47:0]',
            'ldst_port0_addr_i_ok',
            'ldst_port0_addr_ok_o',
            'ldst_port0_exc_happened',
            'ldst_port0_st_data_i[63:0]',
            'ldst_port0_st_data_i_ok',
            'ldst_port0_ld_data_o[63:0]',
            'ldst_port0_ld_data_o_ok',
            'ldst_port0_msr_pr',
            'exc_o_happened',
            'cancel'
        ])]

        if self.microwatt_mmu:
            traces += [
                {'comment': 'microwatt_mmu'},
                'core.fus.mmu0.alu_mmu0.illegal',
                'core.fus.mmu0.alu_mmu0.debug0[3:0]',
                'core.fus.mmu0.alu_mmu0.mmu.state',
                'core.fus.mmu0.alu_mmu0.mmu.pid[31:0]',
                'core.fus.mmu0.alu_mmu0.mmu.prtbl[63:0]',
                {'comment': 'wishbone_memory'},
                'core.l0.pimem.bus__ack',
                'core.l0.pimem.bus__adr[4:0]',
                'core.l0.pimem.bus__bte',
                'core.l0.pimem.bus__cti',
                'core.l0.pimem.bus__cyc',
                'core.l0.pimem.bus__dat_r[63:0]',
                'core.l0.pimem.bus__dat_w[63:0]',
                'core.l0.pimem.bus__dat_err',
                'core.l0.pimem.bus__dat_sel[7:0]',
                'core.l0.pimem.bus__dat_stb',
                'core.l0.pimem.bus__dat_we',
            ]

        gtkname = "issuer_simulator"
        if self.rom:
            gtkname += "_mmu"

        write_gtkw("%s.gtkw" % gtkname,
                   "%s.vcd" % gtkname,
                   traces, styles, module='top.issuer')

        # add run of instructions
        sim.add_sync_process(process)

        # ARGH oh whoops. TODO, core is not passed in!
        # urrr... work out a hacky-way to sort this (access run_hdl
        # core directly for now)

        # optionally, if a wishbone-based ROM is passed in, run that as an
        # extra emulated process
        self.default_mem = {}
        if self.rom is not None:
            print ("TestRunner with MMU ROM")
            pprint (self.rom)
            dcache = hdlrun.issuer.core.fus.fus["mmu0"].alu.dcache
            icache = hdlrun.issuer.core.fus.fus["mmu0"].alu.icache
            self.default_mem = deepcopy(self.rom)
            sim.add_sync_process(wrap(wb_get(dcache.bus,
                                             self.default_mem, "DCACHE")))
            sim.add_sync_process(wrap(wb_get(icache.ibus,
                                             self.default_mem, "ICACHE")))

        with sim.write_vcd("%s.vcd" % gtkname):
            sim.run()
