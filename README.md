# OpenPOWER ISA resources

OpenPOWER ISA resources, including a python-based simulator.
Includes machine-readable versions of the OpenPOWER v3.0B 
specification, from which the python-based simulator is
compiled (python-ply) into python.  Additional languages
(c, c++) are planned.

Part of the Libre-SOC Project (http://libre-soc.org)
Sponsored by http://nlnet.nl

# Installation

```
    python setup.py develop
    make svanalysis
    make pywriter
```

# Copyrights

All programs are written by Libre-SOC team members are LGPLv3+.
However the specification and the CSV files came from their
respective Copyright holders (IBM, OpenPOWER Foundation, Microwatt)
