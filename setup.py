from setuptools import setup, find_packages
import sys
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()

version = '0.0.3'

# the only reason this is added is because it's become a part of python 3.9.
# the project standard is python 3.7 however in future that will be updated.
# for now, cached_property is RELUCTANTLY added but a *copy* is added so
# that the generation of HDL is not critically dependent on random crap
# off the internet. you're spending USD 16 *MILLION* on masks, you better
# be absolutely paranoid-level certain you know where every piece of the
# chain creating the HDL comes from.
cprop = "git+https://git.libre-soc.org/git/cached-property.git@1.5.2" \
        "#egg=cached-property-1.5.2"

# using pip3 for ongoing development is a royal pain.  seriously not
# recommended.  therefore a number of these dependencies have been
# commented out.  *they are still required* - they will need installing
# manually.

install_requires = [
    # NOT ok to install using pip3 https://git.libre-soc.org/?p=nmigen.git
    'nmigen>=0.0,<=0.5',
    # can be obtained with pip3, best done manually
    # https://git.libre-soc.org/?p=nmutil.git
    'libresoc-nmutil>=0.0.0,<=1.0',
    # these should be fine
    'pygdbmi==0.9.0.3',  # gdb machine interface, requires older version (sigh)
    'ply',     # python lex yacc. very cool
    'astor',   # python AST manipulation
    'cffi', # LuaJIT-style C FFI for Python

    # git url needed for having `pip3 install -e .` install from libre-soc git
    'cached-property@'+cprop,
]

test_requires = [
    'nose',
    # best to install pia from Libre-SOC:
    # https://git.libre-soc.org/?p=power-instruction-analyzer.git
    'power-instruction-analyzer'
]

setup(
    name='libresoc-openpower-isa',
    version=version,
    description="OpenPOWER ISA resources including a python-based simulator",
    long_description=README + '\n\n',
    long_description_content_type='text/markdown',
    classifiers=[
        "Topic :: Software Development",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    keywords='nmigen libre-soc openpower simulator',
    author='Luke Kenneth Casson Leighton',
    author_email='lkcl@libre-soc.org',
    url='http://git.libre-soc.org/?p=openpower-isa.git',
    license='LGPLv3+',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    tests_require=test_requires,
    test_suite='nose.collector',
    entry_points={
        'console_scripts': [
            'pywriter=openpower.decoder.pseudo.pywriter:pywriter',
            'pyfnwriter=openpower.decoder.pseudo.pyfnwriter:pyfnwriter',
            'sv_analysis=openpower.sv.sv_analysis:main',
            'pypowersim=openpower.decoder.isa.pypowersim:run_simulation',
            'pysvp64asm=openpower.sv.trans.svp64:asm_process'
        ]
    }
)
