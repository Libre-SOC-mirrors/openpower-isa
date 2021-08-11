import re
from nmigen import Module, Signal
from nmigen.back.pysim import Simulator, Settle
from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.isa.caller import ISACaller
from openpower.decoder.power_decoder import create_pdecode
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import ISACaller, inject
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isa.all import ISA


# PowerISA Version 3.0C Book 1 App. B, Table 129
BCD_TO_DPD_TABLE = """
     0   1   2   3   4   5   6   7   8   9
00_ 000 001 002 003 004 005 006 007 008 009
01_ 010 011 012 013 014 015 016 017 018 019
02_ 020 021 022 023 024 025 026 027 028 029
03_ 030 031 032 033 034 035 036 037 038 039
04_ 040 041 042 043 044 045 046 047 048 049
05_ 050 051 052 053 054 055 056 057 058 059
06_ 060 061 062 063 064 065 066 067 068 069
07_ 070 071 072 073 074 075 076 077 078 079
08_ 00A 00B 02A 02B 04A 04B 06A 06B 04E 04F
09_ 01A 01B 03A 03B 05A 05B 07A 07B 05E 05F
10_ 080 081 082 083 084 085 086 087 088 089
11_ 090 091 092 093 094 095 096 097 098 099
12_ 0A0 0A1 0A2 0A3 0A4 0A5 0A6 0A7 0A8 0A9
13_ 0B0 0B1 0B2 0B3 0B4 0B5 0B6 0B7 0B8 0B9
14_ 0C0 0C1 0C2 0C3 0C4 0C5 0C6 0C7 0C8 0C9
15_ 0D0 0D1 0D2 0D3 0D4 0D5 0D6 0D7 0D8 0D9
16_ 0E0 0E1 0E2 0E3 0E4 0E5 0E6 0E7 0E8 0E9
17_ 0F0 0F1 0F2 0F3 0F4 0F5 0F6 0F7 0F8 0F9
18_ 08A 08B 0AA 0AB 0CA 0CB 0EA 0EB 0CE 0CF
19_ 09A 09B 0BA 0BB 0DA 0DB 0FA 0FB 0DE 0DF
20_ 100 101 102 103 104 105 106 107 108 109
21_ 110 111 112 113 114 115 116 117 118 119
22_ 120 121 122 123 124 125 126 127 128 129
23_ 130 131 132 133 134 135 136 137 138 139
24_ 140 141 142 143 144 145 146 147 148 149
25_ 150 151 152 153 154 155 156 157 158 159
26_ 160 161 162 163 164 165 166 167 168 169
27_ 170 171 172 173 174 175 176 177 178 179
28_ 10A 10B 12A 12B 14A 14B 16A 16B 14E 14F
29_ 11A 11B 13A 13B 15A 15B 17A 17B 15E 15F
30_ 180 181 182 183 184 185 186 187 188 189
31_ 190 191 192 193 194 195 196 197 198 199
32_ 1A0 1A1 1A2 1A3 1A4 1A5 1A6 1A7 1A8 1A9
33_ 1B0 1B1 1B2 1B3 1B4 1B5 1B6 1B7 1B8 1B9
34_ 1C0 1C1 1C2 1C3 1C4 1C5 1C6 1C7 1C8 1C9
35_ 1D0 1D1 1D2 1D3 1D4 1D5 1D6 1D7 1D8 1D9
36_ 1E0 1E1 1E2 1E3 1E4 1E5 1E6 1E7 1E8 1E9
37_ 1F0 1F1 1F2 1F3 1F4 1F5 1F6 1F7 1F8 1F9
38_ 18A 18B 1AA 1AB 1CA 1CB 1EA 1EB 1CE 1CF
39_ 19A 19B 1BA 1BB 1DA 1DB 1FA 1FB 1DE 1DF
40_ 200 201 202 203 204 205 206 207 208 209
41_ 210 211 212 213 214 215 216 217 218 219
42_ 220 221 222 223 224 225 226 227 228 229
43_ 230 231 232 233 234 235 236 237 238 239
44_ 240 241 242 243 244 245 246 247 248 249
45_ 250 251 252 253 254 255 256 257 258 259
46_ 260 261 262 263 264 265 266 267 268 269
47_ 270 271 272 273 274 275 276 277 278 279
48_ 20A 20B 22A 22B 24A 24B 26A 26B 24E 24F
49_ 21A 21B 23A 23B 25A 25B 27A 27B 25E 25F
50_ 280 281 282 283 284 285 286 287 288 289
51_ 290 291 292 293 294 295 296 297 298 299
52_ 2A0 2A1 2A2 2A3 2A4 2A5 2A6 2A7 2A8 2A9
53_ 2B0 2B1 2B2 2B3 2B4 2B5 2B6 2B7 2B8 2B9
54_ 2C0 2C1 2C2 2C3 2C4 2C5 2C6 2C7 2C8 2C9
55_ 2D0 2D1 2D2 2D3 2D4 2D5 2D6 2D7 2D8 2D9
56_ 2E0 2E1 2E2 2E3 2E4 2E5 2E6 2E7 2E8 2E9
57_ 2F0 2F1 2F2 2F3 2F4 2F5 2F6 2F7 2F8 2F9
58_ 28A 28B 2AA 2AB 2CA 2CB 2EA 2EB 2CE 2CF
59_ 29A 29B 2BA 2BB 2DA 2DB 2FA 2FB 2DE 2DF
60_ 300 301 302 303 304 305 306 307 308 309
61_ 310 311 312 313 314 315 316 317 318 319
62_ 320 321 322 323 324 325 326 327 328 329
63_ 330 331 332 333 334 335 336 337 338 339
64_ 340 341 342 343 344 345 346 347 348 349
65_ 350 351 352 353 354 355 356 357 358 359
66_ 360 361 362 363 364 365 366 367 368 369
67_ 370 371 372 373 374 375 376 377 378 379
68_ 30A 30B 32A 32B 34A 34B 36A 36B 34E 34F
69_ 31A 31B 33A 33B 35A 35B 37A 37B 35E 35F
70_ 380 381 382 383 384 385 386 387 388 389
71_ 390 391 392 393 394 395 396 397 398 399
72_ 3A0 3A1 3A2 3A3 3A4 3A5 3A6 3A7 3A8 3A9
73_ 3B0 3B1 3B2 3B3 3B4 3B5 3B6 3B7 3B8 3B9
74_ 3C0 3C1 3C2 3C3 3C4 3C5 3C6 3C7 3C8 3C9
75_ 3D0 3D1 3D2 3D3 3D4 3D5 3D6 3D7 3D8 3D9
76_ 3E0 3E1 3E2 3E3 3E4 3E5 3E6 3E7 3E8 3E9
77_ 3F0 3F1 3F2 3F3 3F4 3F5 3F6 3F7 3F8 3F9
78_ 38A 38B 3AA 3AB 3CA 3CB 3EA 3EB 3CE 3CF
79_ 39A 39B 3BA 3BB 3DA 3DB 3FA 3FB 3DE 3DF
80_ 00C 00D 10C 10D 20C 20D 30C 30D 02E 02F
81_ 01C 01D 11C 11D 21C 21D 31C 31D 03E 03F
82_ 02C 02D 12C 12D 22C 22D 32C 32D 12E 12F
83_ 03C 03D 13C 13D 23C 23D 33C 33D 13E 13F
84_ 04C 04D 14C 14D 24C 24D 34C 34D 22E 22F
85_ 05C 05D 15C 15D 25C 25D 35C 35D 23E 23F
86_ 06C 06D 16C 16D 26C 26D 36C 36D 32E 32F
87_ 07C 07D 17C 17D 27C 27D 37C 37D 33E 33F
88_ 00E 00F 10E 10F 20E 20F 30E 30F 06E 06F
89_ 01E 01F 11E 11F 21E 21F 31E 31F 07E 07F
90_ 08C 08D 18C 18D 28C 28D 38C 38D 0AE 0AF
91_ 09C 09D 19C 19D 29C 29D 39C 39D 0BE 0BF
92_ 0AC 0AD 1AC 1AD 2AC 2AD 3AC 3AD 1AE 1AF
93_ 0BC 0BD 1BC 1BD 2BC 2BD 3BC 3BD 1BE 1BF
94_ 0CC 0CD 1CC 1CD 2CC 2CD 3CC 3CD 2AE 2AF
95_ 0DC 0DD 1DC 1DD 2DC 2DD 3DC 3DD 2BE 2BF
96_ 0EC 0ED 1EC 1ED 2EC 2ED 3EC 3ED 3AE 3AF
97_ 0FC 0FD 1FC 1FD 2FC 2FD 3FC 3FD 3BE 3BF
98_ 08E 08F 18E 18F 28E 28F 38E 38F 0EE 0EF
99_ 09E 09F 19E 19F 29E 29F 39E 39F 0FE 0FF
"""
BCD_TO_DPD_PATTERN = (r"^(\d{2})_\s" + r"\s".join([r"([0-9A-F]{3})"] * 10) + r"$")
BCD_TO_DPD_REGEX = re.compile(BCD_TO_DPD_PATTERN, re.M)


DPD_TO_BCD_TABLE = """
       0     1     2     3     4     5     6     7     8     9     A     B     C     D     E     F
00_   000   001   002   003   004   005   006   007   008   009   080   081   800   801   880   881
01_   010   011   012   013   014   015   016   017   018   019   090   091   810   811   890   891
02_   020   021   022   023   024   025   026   027   028   029   082   083   820   821   808   809
03_   030   031   032   033   034   035   036   037   038   039   092   093   830   831   818   819
04_   040   041   042   043   044   045   046   047   048   049   084   085   840   841   088   089
05_   050   051   052   053   054   055   056   057   058   059   094   095   850   851   098   099
06_   060   061   062   063   064   065   066   067   068   069   086   087   860   861   888   889
07_   070   071   072   073   074   075   076   077   078   079   096   097   870   871   898   899
08_   100   101   102   103   104   105   106   107   108   109   180   181   900   901   980   981
09_   110   111   112   113   114   115   116   117   118   119   190   191   910   911   990   991
0A_   120   121   122   123   124   125   126   127   128   129   182   183   920   921   908   909
0B_   130   131   132   133   134   135   136   137   138   139   192   193   930   931   918   919
0C_   140   141   142   143   144   145   146   147   148   149   184   185   940   941   188   189
0D_   150   151   152   153   154   155   156   157   158   159   194   195   950   951   198   199
0E_   160   161   162   163   164   165   166   167   168   169   186   187   960   961   988   989
0F_   170   171   172   173   174   175   176   177   178   179   196   197   970   971   998   999
10_   200   201   202   203   204   205   206   207   208   209   280   281   802   803   882   883
11_   210   211   212   213   214   215   216   217   218   219   290   291   812   813   892   893
12_   220   221   222   223   224   225   226   227   228   229   282   283   822   823   828   829
13_   230   231   232   233   234   235   236   237   238   239   292   293   832   833   838   839
14_   240   241   242   243   244   245   246   247   248   249   284   285   842   843   288   289
15_   250   251   252   253   254   255   256   257   258   259   294   295   852   853   298   299
16_   260   261   262   263   264   265   266   267   268   269   286   287   862   863  (888) (889)
17_   270   271   272   273   274   275   276   277   278   279   296   297   872   873  (898) (899)
18_   300   301   302   303   304   305   306   307   308   309   380   381   902   903   982   983
19_   310   311   312   313   314   315   316   317   318   319   390   391   912   913   992   993
1A_   320   321   322   323   324   325   326   327   328   329   382   383   922   923   928   929
1B_   330   331   332   333   334   335   336   337   338   339   392   393   932   933   938   939
1C_   340   341   342   343   344   345   346   347   348   349   384   385   942   943   388   389
1D_   350   351   352   353   354   355   356   357   358   359   394   395   952   953   398   399
1E_   360   361   362   363   364   365   366   367   368   369   386   387   962   963  (988) (989)
1F_   370   371   372   373   374   375   376   377   378   379   396   397   972   973  (998) (999)
20_   400   401   402   403   404   405   406   407   408   409   480   481   804   805   884   885
21_   410   411   412   413   414   415   416   417   418   419   490   491   814   815   894   895
22_   420   421   422   423   424   425   426   427   428   429   482   483   824   825   848   849
23_   430   431   432   433   434   435   436   437   438   439   492   493   834   835   858   859
24_   440   441   442   443   444   445   446   447   448   449   484   485   844   845   488   489
25_   450   451   452   453   454   455   456   457   458   459   494   495   854   855   498   499
26_   460   461   462   463   464   465   466   467   468   469   486   487   864   865  (888) (889)
27_   470   471   472   473   474   475   476   477   478   479   496   497   874   875  (898) (899)
28_   500   501   502   503   504   505   506   507   508   509   580   581   904   905   984   985
29_   510   511   512   513   514   515   516   517   518   519   590   591   914   915   994   995
2A_   520   521   522   523   524   525   526   527   528   529   582   583   924   925   948   949
2B_   530   531   532   533   534   535   536   537   538   539   592   593   934   935   958   959
2C_   540   541   542   543   544   545   546   547   548   549   584   585   944   945   588   589
2D_   550   551   552   553   554   555   556   557   558   559   594   595   954   955   598   599
2E_   560   561   562   563   564   565   566   567   568   569   586   587   964   965  (988) (989)
2F_   570   571   572   573   574   575   576   577   578   579   596   597   974   975  (998) (999)
30_   600   601   602   603   604   605   606   607   608   609   680   681   806   807   886   887
31_   610   611   612   613   614   615   616   617   618   619   690   691   816   817   896   897
32_   620   621   622   623   624   625   626   627   628   629   682   683   826   827   868   869
33_   630   631   632   633   634   635   636   637   638   639   692   693   836   837   878   879
34_   640   641   642   643   644   645   646   647   648   649   684   685   846   847   688   689
35_   650   651   652   653   654   655   656   657   658   659   694   695   856   857   698   699
36_   660   661   662   663   664   665   666   667   668   669   686   687   866   867  (888) (889)
37_   670   671   672   673   674   675   676   677   678   679   696   697   876   877  (898) (899)
38_   700   701   702   703   704   705   706   707   708   709   780   781   906   907   986   987
39_   710   711   712   713   714   715   716   717   718   719   790   791   916   917   996   997
3A_   720   721   722   723   724   725   726   727   728   729   782   783   926   927   968   969
3B_   730   731   732   733   734   735   736   737   738   739   792   793   936   937   978   979
3C_   740   741   742   743   744   745   746   747   748   749   784   785   946   947   788   789
3D_   750   751   752   753   754   755   756   757   758   759   794   795   956   957   798   799
3E_   760   761   762   763   764   765   766   767   768   769   786   787   966   967  (988) (989)
3F_   770   771   772   773   774   775   776   777   778   779   796   797   976   977  (998) (999)
"""
DPD_TO_BCD_PATTERN = (r"^([0-9A-F]{2})_\s+" + r"\s+".join([r"\(?(\d{3})\)?"] * 16) + r"$")
DPD_TO_BCD_REGEX = re.compile(DPD_TO_BCD_PATTERN, re.M)


def run_tst(generator, initial_regs, initial_sprs=None, svstate=0, mmu=False,
                                     initial_cr=0, mem=None,
                                     initial_fprs=None):
    if initial_sprs is None:
        initial_sprs = {}
    m = Module()
    comb = m.d.comb
    instruction = Signal(32)

    pdecode = create_pdecode(include_fp=initial_fprs is not None)

    gen = list(generator.generate_instructions())
    insncode = generator.assembly.splitlines()
    instructions = list(zip(gen, insncode))

    m.submodules.pdecode2 = pdecode2 = PowerDecode2(pdecode)
    simulator = ISA(pdecode2, initial_regs, initial_sprs, initial_cr,
                    initial_insns=gen, respect_pc=True,
                    initial_svstate=svstate,
                    initial_mem=mem,
                    fpregfile=initial_fprs,
                    disassembly=insncode,
                    bigendian=0,
                    mmu=mmu)
    comb += pdecode2.dec.raw_opcode_in.eq(instruction)
    sim = Simulator(m)

    def process():

        print ("GPRs")
        simulator.gpr.dump()
        print ("FPRs")
        simulator.fpr.dump()

        yield pdecode2.dec.bigendian.eq(0)  # little / big?
        pc = simulator.pc.CIA.value
        index = pc//4
        while index < len(instructions):
            print("instr pc", pc)
            try:
                yield from simulator.setup_one()
            except KeyError:  # indicates instruction not in imem: stop
                break
            yield Settle()

            ins, code = instructions[index]
            print("    0x{:X}".format(ins & 0xffffffff))
            opname = code.split(' ')[0]
            print(code, opname)

            # ask the decoder to decode this binary data (endian'd)
            yield from simulator.execute_one()
            pc = simulator.pc.CIA.value
            index = pc//4

    sim.add_process(process)
    with sim.write_vcd("simulator.vcd", "simulator.gtkw",
                       traces=[]):
        sim.run()
    return simulator


class BCDTestCase(FHDLTestCase):
    def test_cdtbcd(self):
        # This test is a terrible slowpoke; let's check first 20 values
        # for now, and come up with some clever ideas on how to make
        # it run faster.
        initial_regs = [0] * 32
        for match in DPD_TO_BCD_REGEX.findall(DPD_TO_BCD_TABLE)[0:2]:
            for digit in range(0x10):
                dpd = int((match[0] + f"{digit:X}"), 16)
                bcd = ((int(match[1 + digit][0]) << 8) |
                       (int(match[1 + digit][1]) << 4) |
                       (int(match[1 + digit][2]) << 0))
                lst = ["cdtbcd 0, 1"]
                initial_regs[1] = dpd
                with Program(lst, bigendian=False) as program:
                    sim = self.run_tst_program(program, initial_regs)
                    self.assertEqual(sim.gpr(0), SelectableInt(bcd, 64))

    def test_cbcdtd(self):
        # This test is a terrible slowpoke; let's check first 20 values
        # for now, and come up with some clever ideas on how to make
        # it run faster.
        initial_regs = [0] * 32
        for match in BCD_TO_DPD_REGEX.findall(BCD_TO_DPD_TABLE)[0:2]:
            for digit in range(10):
                bcd = ((int(match[0][0]) << 8) |
                       (int(match[0][1]) << 4) |
                       (int(digit) << 0))
                dpd = int(match[1 + digit], 16)
                lst = ["cbcdtd 0, 1"]
                initial_regs[1] = bcd
                with Program(lst, bigendian=False) as program:
                    sim = self.run_tst_program(program, initial_regs)
                    self.assertEqual(sim.gpr(0), SelectableInt(dpd, 64))

    def run_tst_program(self, prog, initial_regs=[0] * 32):
        simulator = run_tst(prog, initial_regs)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
