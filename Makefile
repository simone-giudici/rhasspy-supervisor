SOURCE = rhasspysupervisor
PYTHON_FILES = $(SOURCE)/*.py *.py

.PHONY: check test venv dist pyinstaller

version := $(shell cat VERSION)
architecture := $(shell dpkg-architecture | grep DEB_BUILD_ARCH= | sed 's/[^=]\+=//')

check:
	flake8 $(PYTHON_FILES)
	pylint $(PYTHON_FILES)
	mypy $(PYTHON_FILES)

venv:
	rm -rf .venv/
	python3 -m venv .venv
	.venv/bin/pip3 install wheel setuptools
	.venv/bin/pip3 install -r requirements.txt
	.venv/bin/pip3 install -r requirements_dev.txt

dist:
	python3 setup.py sdist

pyinstaller:
	mkdir -p dist
	pyinstaller -y --workpath pyinstaller/build --distpath pyinstaller/dist rhasspysupervisor.spec
	tar -C pyinstaller/dist -czf dist/rhasspy-supervisor_$(version)_$(architecture).tar.gz rhasspysupervisor/
