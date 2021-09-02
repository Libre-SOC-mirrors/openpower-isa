import os
import platform

# set up environment variable overrides, can use for different versions
# as well as native (TALOS-II POWER9) builds.  detects ppc64le and
# assumes "native"
cmds = {}
for cmd in ['objcopy', 'as', 'ld', 'gcc', 'ar', 'gdb']:
    if platform.machine() == 'ppc64le':
        default = cmd
    else:
        default = "powerpc64-linux-gnu-%s" % cmd
    cmds[cmd] = os.environ.get(cmd.upper(), actual)


