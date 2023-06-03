import argparse
import contextlib
import sys

from openpower.decoder.power_enums import (
    find_wiki_dir,
)
from openpower.insndb.types import (
    Database,
    Visitor,
)


def main():
    class ListVisitor(Visitor):
        @contextlib.contextmanager
        def record(self, record):
            print(record.name)
            yield record

    visitors = {
        "list": ListVisitor,
    }
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="command", required=True)
    parser_list = subparser.add_parser("list")
    args = vars(parser.parse_args())
    command = args.pop("command")
    visitor = visitors[command]()

    db = Database(find_wiki_dir())
    db.visit(visitor=visitor)
