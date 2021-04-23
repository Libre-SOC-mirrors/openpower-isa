from setuptools import setup, find_packages
import sys
import os

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()
NEWS = open(os.path.join(here, 'NEWS.txt')).read()


version = '0.0.0'

# using pip3 for ongoing development is a royal pain.  seriously not
# recommended.  therefore a number of these dependencies have been
# commented out.  *they are still required* - they will need installing
# manually.

install_requires = [
    'nmigen', 
    'nmutil',  # can be obtained with pip3, best done manually
]

test_requires = [
    'nose',
    # install pia from https://salsa.debian.org/Kazan-team/power-instruction-analyzer
    'power-instruction-analyzer'
]

setup(
    name='libresoc-openpower-isa',
    version=version,
    description="OpenPOWER ISA resources including a python-based simulator",
    long_description=README + '\n\n' + NEWS,
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
    entry_points = {
        'console_scripts': [
            'pywriter=openpower.decoder.pseudo.pywriter:pywriter',
            'sv_analysis=openpower.sv:sv_analysis'
        ]
    }
)
