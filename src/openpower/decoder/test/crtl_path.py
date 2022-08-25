# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay


from contextlib import contextmanager
from itertools import count
import os
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile
from threading import local

__ctrl_path = local()


@contextmanager
def __try_lock_file(path):
    path = Path(path)
    try:
        file = path.open("xb")
    except FileExistsError:
        yield False
        return
    try:
        yield True
    finally:
        file.close()
        path.unlink()


def get_crtl_path():
    # type: () -> str
    path = getattr(__ctrl_path, "path", None)
    if path is not None:
        assert isinstance(path, str), "invalid state"
        return path
    for i in range(10000):
        path = f"crtl{i}"
        with __try_lock_file(f"crtl{i}.lock") as locked:
            if locked and next(Path(path).glob(".lock_*"), None) is None:
                shutil.rmtree(path, ignore_errors=True)
                Path(path).mkdir(parents=True, exist_ok=True)
                tmpfile = NamedTemporaryFile(prefix=".lock_", dir=path)
                __ctrl_path.tmpfile = tmpfile
                __ctrl_path.path = path
                return path
    assert False, "can't create crtl* path"
