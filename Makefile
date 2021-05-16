PYTHON3 ?= "python3"

.PHONY: help Makefile gitupdate svanalysis test htmlupload pypiupload \
        pyfnwriter pywriter

gitupdate:
	git submodule init
	git submodule update --init --recursive --remote

# now installed as a command (/usr/local/bin/svanalysis) by setup.py
svanalysis:
	sv_analysis

# now installed as a command (/usr/local/bin/pywriter) by setup.py
pywriter:
	pywriter

# likewise
pyfnwriter:
	pyfnwriter

develop:
	python3 setup.py develop # yes, develop, not install

# testing (usually done at install time)
test: develop
	python3 setup.py test # could just run nosetest3...

pypiupload:
	$(PYTHON3) setup.py sdist upload

# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = Libre-SOC
SOURCEDIR     = .
BUILDDIR      = build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# copies all documentation to libre-soc (libre-soc admins only)
htmlupload: clean html
	rsync -HPavz --delete build/html/* \
        libre-soc.org:/var/www/libre-soc.org/docs/openpower-isa/

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	echo "catch-all falling through to sphinx for document building"
	mkdir -p "$(SOURCEDIR)"/src/gen
	sphinx-apidoc --ext-autodoc -o "$(SOURCEDIR)"/src/gen ./src/openpower
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

