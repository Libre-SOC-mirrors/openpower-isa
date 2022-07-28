#!/usr/bin/env python3
""" handy script for re-indenting text to be in multiples of `    `"""
import sys

indent_unit = "    "


def ind_print(v):
    print(indent_unit * (len(indent_stack) - 1) + v)


with open(sys.argv[1]) as f:
    indent_stack = [""]
    for line in f:
        line = line.rstrip().expandtabs()
        indent = line[:-len(line.lstrip())]
        unindented = line[len(indent):]
        if unindented == '':
            print()
            continue
        while len(indent_stack[-1]) > len(indent):
            indent_stack.pop()
            assert len(indent_stack[-1]) >= len(indent), \
                "popped intermediate indentation"
        if len(indent_stack[-1]) < len(indent):
            indent_stack.append(indent)
        ind_print(unindented)
