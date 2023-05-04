# Reads OpenPOWER ISA pages from http://libre-soc.org/openpower/isafunctions
"""OpenPOWER ISA function reader

reads markdown files looking for indented code blocks
"""

from collections import OrderedDict
from copy import copy
import os


def get_isafn_dir():
    fdir = os.path.abspath(os.path.dirname(__file__))
    fdir = os.path.split(fdir)[0]
    fdir = os.path.split(fdir)[0]
    fdir = os.path.split(fdir)[0]
    fdir = os.path.split(fdir)[0]
    print (fdir)
    return os.path.join(fdir, "openpower", "isafunctions")


class ISAFunctions:

    def __init__(self):
        self.fns = OrderedDict()
        for pth in os.listdir(os.path.join(get_isafn_dir())):
            print("examining", get_isafn_dir(), pth)
            if "swp" in pth:
                continue
            if not pth.endswith(".mdwn"):
                print ("warning, file not .mdwn, skipping", pth)
                continue
            self.read_file(pth)

    def read_file(self, fname):
        pagename = fname.split('.')[0]
        fname = os.path.join(get_isafn_dir(), fname)
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

            # any lines not starting with space, ignore
            while True:
                l = lines.pop(0).rstrip()
                prefix_lines += 1
                print ("examining", repr(l))
                if l.startswith("    "):
                    break
                if l.startswith('<!--'):
                    continue

            # get pseudocode

            # fix parser line numbers by prepending the right number of
            # blank lines to the parser input
            li = [""] * prefix_lines
            li += [l[4:]]  # first line detected with 4-space
            while lines:
                l = lines.pop(0).rstrip()
                print ("examining", repr(l))
                if len(l) == 0:
                    li.append(l)
                    continue
                if l.strip().startswith('<!--'):
                    li.append("")
                    continue
                assert l.startswith('    '), ("4spcs not found in line %s" % l)
                l = l[4:]  # lose 4 spaces
                li.append(l)
            d['pcode'] = '\n'.join(li)
            break

        self.fns[pagename] = d

    def pprint(self):
        for k, v in self.fns.items():
            print("# %s %s" % (k, v['desc']))
            print(v['pcode'])
            print()


if __name__ == '__main__':
    isa = ISAFunctions()
    isa.pprint()
