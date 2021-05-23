	lis 1, 0xdead     # test comment
	ori 1, 1, 0xbeef
label:                # comment ok here too
    can be anything it will be discarded and entirely replaced # sv.extsw 5.v, 1
label_that_will_be_discarded: # sv.addi 5, 3, 0
