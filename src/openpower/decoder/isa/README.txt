Power ISA Simulator in python
---------

This simulator is not in the least bit designed for performance, it is
designed for understandability of the Power ISA Specification. It uses
compiler technology and the pseudocode and tables from the actual PDF
(v3.0B initially) and has made it executable.

A class called SelectableInt makes it possible to access numbers in MSB0
order due to the Power ISA Spec being MSB0 order.

A RADIX MMU based on Microwatt and gem5-experimental is available.

There are thousands of unit tests in this subdirectory (and many more
in openpower/tests).

Boris Shingarov has created a Power ISA Formal Correctness Proof using
the machine-readable spec and the compiler.

A "co-execution" Test API is available which allows single-stepping and
extraction of memory and registers for comparison. Qemu and HDL is supported.

Some unit tests also have "Expected Results" and the rest will be converted
over time.

In conclusion this Simulator's purpose is for validation and correctness
rather than high performance.

The main simulator class is ISACaller.  Compiling the psedudocode is done
with the command "pywriter" and the helper routines (extracted from the
Power ISA Appendices) with "pyfnwriter".

Unit tests are both stand-alone executable as well as automatically
picked up by "nosetests3".  Most but not all of the unit tests are for
SVP64 in this subdirectory: see test_caller.py for Standard Scalar Power
ISA 3.0 which picks up tests from openpower/tests

Also of interest is pypowersim which is a standalone Power ISA bare metal
simulator.  More details at https://libre-soc.org/docs/pypowersim
