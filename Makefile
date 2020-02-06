SOURCE = rhasspysupervisor
PYTHON_FILES = $(SOURCE)/*.py *.py
SHELL_FILES = bin/*

.PHONY: reformat check test venv dist pyinstaller debian

version := $(shell cat VERSION)
architecture := $(shell dpkg-architecture | grep DEB_BUILD_ARCH= | sed 's/[^=]\+=//')

# -----------------------------------------------------------------------------
# Python
# -----------------------------------------------------------------------------

reformat:
	scripts/format-code.sh $(PYTHON_FILES)

check:
	scripts/check-code.sh $(PYTHON_FILES)

venv:
	scripts/create-venv.sh

dist:
	python3 setup.py sdist

# -----------------------------------------------------------------------------
# Debian
# -----------------------------------------------------------------------------

pyinstaller:
	scripts/build-pyinstaller.sh "${architecture}" "${version}"

debian:
	scripts/build-debian.sh "${architecture}" "${version}"
