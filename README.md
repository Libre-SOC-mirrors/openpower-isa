# OpenPOWER ISA resources

OpenPOWER ISA resources, including a python-based simulator plus thousands
of OpenPOWER ISA unit tests.  Includes machine-readable versions of the
OpenPOWER v3.0B specification, from which the python-based simulator
is compiled (python-ply) into python.  Additional languages (c, c++)
are planned.  Also planned: co-simulation of power-gem5, microwatt,
and other HDL and emulators.

Part of the Libre-SOC Project (http://libre-soc.org)
Sponsored by http://nlnet.nl

# Installation

Prerequisites: qemu, powerpc64-linux-gnu-gcc and associated binutils and
gdb, pygdbmi, nmigen and nmutil are needed.  Make life easy: use debian,
and the following scripts:

* https://git.libre-soc.org/?p=dev-env-setup.git;a=blob;f=ppc64-gdb-gcc
* https://git.libre-soc.org/?p=dev-env-setup.git;a=blob;f=install-hdl-apt-reqs
* https://git.libre-soc.org/?p=dev-env-setup.git;a=blob;f=pia-install

Once those are sorted, installation and setup is as follows:

* python3 setup.py develop
* make svanalysis
* make pywriter
* make pyfnwriter

# Usage

Usage depends on what your goal is.  The python-based simulator is in no
way intended to win any speed contests: it's designed for "readability".
Additionally, running qemu via pygdmi and extracting its register file
is equally horribly slow.  To demonstrate, run the following:

    python3 openpower/simulator/test_sim.py

This will do the following:

* compile each of the (tiny) programs in the test
* extract the raw binary
* fire up the python-based simulator (ineptly named ISACaller)
* fire up qemu using the machine interface pygdbmi
* single-step through both ISACaller and qemu, extracting full regfiles
  and memory
* compare them both and throw exceptions on detected discrepancies

This should be pretty obvious as to why this is done: it's checking
one simulator against another (and has found bugs in qemu as a result).

What if you could then also run the same unit tests against *your own
hardware*, or against say Microwatt, or Libre-SOC, or against your
own emulator?

Given that this is a work-in-progress, so far the only external HDL
that uses these unit tests is Libre-SOC's very simple TestIssuer:
https://git.libre-soc.org/?p=soc.git;a=blob;f=src/soc/simple/test/test_issuer.py

The ISACaller itself of course needed to bootstrap up by having unit
tests that explicitly and clearly checked against expected values.  Example:

* python openpower/decoder/isa/test_caller.py

These tests pre-prepare the register files, then check afterwards that
the result of operation is as expected.  In this way, at least basic
functionality of ISACaller can be confirmed in a stand-alone fashion
(useful if you do not wish to install qemu etc. etc. etc.)

# Contributions

Contributions are welcomed as this is a collaborative Libre Project.
Libre-SOC is covered by the following dead-simple Charter:

* https://libre-soc.org/charter/

Contributions even to the Charter, in the form of appropriate Dilbert
cartoons especially appreciated:

* https://libre-soc.org/charter/discussion/

# Copyrights

All programs are written by Libre-SOC team members are LGPLv3+.
However the specification and the CSV files came from their
respective Copyright holders (IBM, OpenPOWER Foundation, Microwatt).

Bear in mind that the *facts* in a specification may not be copyrighted,
however the document (or source code) *containing* those facts can be and
is copyrightable.  In this repository, the **facts** were extracted
(from Microwatt and from the OpenPOWER ISA Technical Specification).

Therefore, you, likewise, may *also* extract the **facts** from this
source code, but for the actual source code itself you must respect the
terms and conditions of the LGPLv3+ License in which those facts happen
to be embedded.

# Other Unit Tests

There do exist other unit tests for OpenPOWER.  List them here:

* https://bitbucket.org/sandip4n/gem5-powerpc64le-tests/src/master/
* http://sources.buildroot.net/kvm-unit-tests/git/powerpc/
* https://github.com/lioncash/DolphinPPCTests

