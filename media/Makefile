.PHONY: all wget tests

EXPECTED_VER = 1
VER = $(shell cat data/VERSION)

all:
ifneq ($(VER), $(EXPECTED_VER))
	$(error Data not found, or version mismatch. Please run "make wget")
endif
	@$(MAKE) tests

wget:
	mkdir -p data
	rm -f media-test-data.txz
	wget https://ftp.libre-soc.org/media-test-data.txz
	tar -C data -xvf media-test-data.txz

tests:
	echo juuh
