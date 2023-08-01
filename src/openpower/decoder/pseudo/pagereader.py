# Reads OpenPOWER ISA pages from http://libre-soc.org/openpower/isa
"""OpenPOWER ISA page parser

returns an OrderedDict of namedtuple "Ops" containing details of all
instructions listed in markdown files.

format must be strictly as follows (no optional sections) including whitespace:

# Compare Logical

X-Form

* cmpl BF,L,RA,RB

    if L = 0 then a <- [0]*32 || (RA)[32:63]
                  b <- [0]*32 || (RB)[32:63]
             else a <-  (RA)
                  b <-  (RB)
    if      a <u b then c <- 0b100
    else if a >u b then c <- 0b010
    else                c <-  0b001
    CR[4*BF+32:4*BF+35] <- c || XER[SO]

Special Registers Altered:

    CR field BF
    Another field

this translates to:

    # heading
    blank
    Some-Form
    blank
    * instruction registerlist
    * instruction registerlist
    blank
    4-space-indented pseudo-code
    4-space-indented pseudo-code
    blank
    Special Registers Altered:
    4-space-indented register description
    blank
    blank(s) (optional for convenience at end-of-page)
"""

from openpower.util import log
from openpower.decoder.orderedset import OrderedSet
from collections import namedtuple, OrderedDict
from copy import copy
import os
import re

opfields = ("desc", "form", "opcode", "regs", "pcode", "sregs", "page",
            "extra_uninit_regs", "pcode_fname")
Ops = namedtuple("Ops", opfields)


def get_isa_dir():
    fdir = os.path.abspath(os.path.dirname(__file__))
    fdir = os.path.split(fdir)[0]
    fdir = os.path.split(fdir)[0]
    fdir = os.path.split(fdir)[0]
    fdir = os.path.split(fdir)[0]
    # print (fdir)
    return os.path.join(fdir, "openpower", "isa")


pattern_opcode = r"[A-Za-z0-9_\.]+\.?"
pattern_dynamic = r"[A-Za-z0-9_]+(?:\([A-Za-z0-9_]+\))*"
pattern_static = r"[A-Za-z0-9]+\=[01]"
regex_opcode = re.compile(f"^{pattern_opcode}$")
regex_dynamic = re.compile(f"^{pattern_dynamic}(?:,{pattern_dynamic})*$")
regex_static = re.compile(f"^\({pattern_static}(?:\s{pattern_static})*\)$")


def operands(opcode, desc):
    if desc is None:
        return
    desc = desc.replace("(", "")
    desc = desc.replace(")", "")
    desc = desc.replace(",", " ")
    for operand in desc.split(" "):
        operand = operand.strip()
        if operand:
            yield operand


class ISA:
    def __init__(self):
        self.instr = OrderedDict()
        self.forms = {}
        self.page = {}
        self.verbose = False
        for pth in os.listdir(os.path.join(get_isa_dir())):
            if self.verbose:
                print("examining", get_isa_dir(), pth)
            if "swp" in pth:
                continue
            if not pth.endswith(".mdwn"):
                log ("warning, file not .mdwn, skipping", pth)
                continue
            self.read_file(pth)
            continue
            # code which helped add in the keyword "Pseudo-code:" automatically
            rewrite = self.read_file_for_rewrite(pth)
            name = os.path.join("/tmp", pth)
            with open(name, "w") as f:
                f.write('\n'.join(rewrite) + '\n')

    def __iter__(self):
        yield from self.instr.items()

    def read_file_for_rewrite(self, fname):
        pagename = fname.split('.')[0]
        fname = os.path.join(get_isa_dir(), fname)
        with open(fname) as f:
            lines = f.readlines()
        rewrite = []

        l = lines.pop(0).rstrip()  # get first line
        rewrite.append(l)
        while lines:
            if self.verbose:
                print(l)
            # look for HTML comment, if starting, skip line.
            # XXX this is braindead!  it doesn't look for the end
            # so please put ending of comments on one line:
            # <!-- line 1 comment -->
            # {some whitespace}<!-- line 2 comment -->
            if l.strip().startswith('<!--'):
                # print ("skipping comment", l)
                l = lines.pop(0).rstrip()  # get first line
                continue

            # Ignore blank lines before the first #
            if len(l.strip()) == 0:
                continue

            # expect get heading
            assert l.startswith('#'), ("# not found in line %s" % l)

            # whitespace expected
            l = lines.pop(0).strip()
            if self.verbose:
                print(repr(l))
            assert len(l) == 0, ("blank line not found %s" % l)
            rewrite.append(l)

            # Form expected
            l = lines.pop(0).strip()
            assert l.endswith('-Form'), ("line with -Form expected %s" % l)
            rewrite.append(l)

            # whitespace expected
            l = lines.pop(0).strip()
            assert len(l) == 0, ("blank line not found %s" % l)
            rewrite.append(l)

            # get list of opcodes
            while True:
                l = lines.pop(0).strip()
                rewrite.append(l)
                if len(l) == 0:
                    break
                assert l.startswith('*'), ("* not found in line %s" % l)

            rewrite.append("Pseudo-code:")
            rewrite.append("")
            # get pseudocode
            while True:
                l = lines.pop(0).rstrip()
                if l.strip().startswith('<!--'):
                    # print ("skipping comment", l)
                    l = lines.pop(0).rstrip()  # get first line
                    continue
                rewrite.append(l)
                if len(l) == 0:
                    break
                assert l.startswith('    '), ("4spcs not found in line %s" % l)

            # "Special Registers Altered" expected
            l = lines.pop(0).rstrip()
            assert l.startswith("Special"), ("special not found %s" % l)
            rewrite.append(l)

            # whitespace expected
            l = lines.pop(0).strip()
            assert len(l) == 0, ("blank line not found %s" % l)
            rewrite.append(l)

            # get special regs
            while lines:
                l = lines.pop(0).rstrip()
                rewrite.append(l)
                if len(l) == 0:
                    break
                assert l.startswith('    '), ("4spcs not found in line %s" % l)

            # expect and drop whitespace
            while lines:
                l = lines.pop(0).rstrip()
                rewrite.append(l)
                if len(l) != 0 and not l.strip().startswith('<!--'):
                    break

        return rewrite

    def read_file(self, fname):
        pagename = fname.split('.')[0]
        fname = os.path.join(get_isa_dir(), fname)
        with open(fname) as f:
            lines = f.readlines()

        # set up dict with current page name
        d = {'page': pagename}

        # line-by-line lexer/parser, quite straightforward: pops one
        # line off the list and checks it.  nothing complicated needed,
        # all sections are mandatory so no need for a full LALR parser.

        l = lines.pop(0).rstrip()  # get first line
        prefix_lines = 0
        while lines:
            pcode_fname = fname
            if self.verbose:
                print(l)
            # look for HTML comment, if starting, skip line.
            # XXX this is braindead!  it doesn't look for the end
            # so please put ending of comments on one line:
            # <!-- line 1 comment -->
            # <!-- line 2 comment -->
            if l.strip().startswith('<!--'):
                # print ("skipping comment", l)
                l = lines.pop(0).rstrip()  # get next line
                prefix_lines += 1
                continue

            # Ignore blank lines before the first #
            if len(l) == 0:
                l = lines.pop(0).rstrip()  # get next line
                prefix_lines += 1
                continue

            # expect get heading
            assert l.startswith('#'), ("# not found in line '%s'" % l)
            d['desc'] = l[1:].strip()

            # whitespace expected
            l = lines.pop(0).strip()
            prefix_lines += 1
            if self.verbose:
                print(repr(l))
            assert len(l) == 0, ("blank line not found %s" % l)

            # Form expected
            l = lines.pop(0).strip()
            prefix_lines += 1
            assert l.endswith('-Form'), ("line with -Form expected %s" % l)
            d['form'] = l.split('-')[0]

            # whitespace expected
            l = lines.pop(0).strip()
            prefix_lines += 1
            assert len(l) == 0, ("blank line not found %s" % l)

            # get list of opcodes
            opcodes = []
            while True:
                l = lines.pop(0).strip()
                prefix_lines += 1
                if len(l) == 0:
                    break
                assert l.startswith('*'), ("* not found in line %s" % l)
                rest = l[1:].strip()

                (opcode, _, rest) = map(str.strip, rest.partition(" "))
                if regex_opcode.match(opcode) is None:
                    raise IOError(repr(opcode))
                opcode = [opcode]

                (dynamic, _, rest) = map(str.strip, rest.partition(" "))
                if regex_dynamic.match(dynamic) is None and dynamic:
                    raise IOError(f"{l!r}: {dynamic!r}")
                if dynamic:
                    opcode.append(dynamic.split(","))

                static = rest
                if regex_static.match(static) is None and static:
                    raise IOError(f"{l!r}: {static!r}")
                if static:
                    opcode.extend(static[1:-1].split(" "))

                opcodes.append(opcode)

            # "Pseudocode" expected
            l = lines.pop(0).rstrip()
            prefix_lines += 1
            assert l.startswith("Pseudo-code:"), ("pseudocode found %s" % l)

            # whitespace expected
            l = lines.pop(0).strip()
            prefix_lines += 1
            if self.verbose:
                print(repr(l))
            assert len(l) == 0, ("blank line not found %s" % l)

            extra_uninit_regs = OrderedSet()

            # get pseudocode

            # fix parser line numbers by prepending the right number of
            # blank lines to the parser input
            li = [""] * (prefix_lines + 1)
            while True:
                l = lines.pop(0).rstrip()
                prefix_lines += 1
                if len(l) == 0:
                    li.append(l)
                    break
                re_match = re.fullmatch(r" *<!-- EXTRA_UNINIT_REGS:(.*)-->", l)
                if re_match:
                    for i in re_match[1].split(' '):
                        if i != "":
                            extra_uninit_regs.add(i)
                    li.append("")
                    continue
                if l.startswith("[[!inline "):
                    li.append(l)
                    continue
                if l.strip().startswith('<!--'):
                    li.append("")
                    continue
                assert l.startswith('    '), ("4spcs not found in line %s" % l)
                l = l[4:]  # lose 4 spaces
                li.append(l)
            inline_line = None
            other = False
            for l in li:
                if l.startswith("[[!inline "):
                    assert inline_line is None, \
                        "can't use multiple [[!inline]] directives"
                    inline_line = l
                elif l != "":
                    other = True
            if inline_line is not None:
                assert not other, \
                    "can't use [[!inline]] directive with other content"

                re_match = re.fullmatch(
                    r'\[\[!inline pagenames="openpower/isa/([^" ]*[^"/ ])" '
                    r'raw="yes"]]', inline_line)
                assert re_match, (
                    'invalid [[!inline]] directive, must be of the form:\n'
                    '[[!inline pagenames="openpower/isa/foo/bar" '
                    'raw="yes"]]')
                pcode_fname = re_match[1] + ".mdwn"
                pcode_fname = os.path.join(get_isa_dir(), pcode_fname)
                with open(pcode_fname) as f:
                    li = f.readlines()
                for i, l in enumerate(li):
                    l = l.rstrip()
                    if l.strip().startswith("<!--"):
                        l = ""
                    elif l != "":
                        assert l.startswith("    "), \
                            "line must start with 4 spaces"
                        l = l[4:]
                    li[i] = l
            d['pcode'] = li
            d['pcode_fname'] = pcode_fname
            d['extra_uninit_regs'] = extra_uninit_regs

            # "Special Registers Altered" expected
            l = lines.pop(0).rstrip()
            prefix_lines += 1
            assert l.startswith("Special"), ("special not found %s" % l)

            # whitespace expected
            l = lines.pop(0).strip()
            prefix_lines += 1
            assert len(l) == 0, ("blank line not found %s" % l)

            # get special regs
            li = []
            while lines:
                l = lines.pop(0).rstrip()
                prefix_lines += 1
                if len(l) == 0:
                    break
                assert l.startswith('    '), ("4spcs not found in line %s" % l)
                l = l[4:]  # lose 4 spaces
                li.append(l)
            d['sregs'] = li

            # add in opcode
            for o in opcodes:
                self.add_op(o, d)

            # expect and drop whitespace and comments
            while lines:
                l = lines.pop(0).rstrip()
                prefix_lines += 1
                if len(l) != 0 and not l.strip().startswith('<!--'):
                    break

    def add_op(self, o, d):
        opcode, regs = o[0], o[1:]
        op = copy(d)
        op['regs'] = regs
        op['opcode'] = opcode
        self.instr[opcode] = Ops(**op)

        # create list of instructions by form
        form = op['form']
        fl = self.forms.get(form, [])
        self.forms[form] = fl + [opcode]

        # create list of instructions by page
        page = op['page']
        pl = self.page.get(page, [])
        self.page[page] = pl + [opcode]

    def pprint_ops(self):
        for k, v in self.instr.items():
            print("# %s %s" % (v.opcode, v.desc))
            print("Form: %s Regs: %s" % (v.form, v.regs))
            print('\n'.join(map(lambda x: "    %s" % x, v.pcode)))
            print("Specials")
            print('\n'.join(map(lambda x: "    %s" % x, v.sregs)))
            print()
        for k, v in isa.forms.items():
            print(k, v)


if __name__ == '__main__':
    isa = ISA()
    isa.pprint_ops()
    # example on how to access cmp regs:
    print ("cmp regs:", isa.instr["cmp"].regs)
