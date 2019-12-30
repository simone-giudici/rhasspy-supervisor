.PHONY: check test venv dist

check:
	flake8 rhasspysupervisor/*.py
	pylint rhasspysupervisor/*.py
	mypy rhasspysupervisor/*.py

venv:
	rm -rf .venv/
	python3 -m venv .venv
	.venv/bin/pip3 install wheel setuptools
	.venv/bin/pip3 install -r requirements_all.txt

dist:
	python3 setup.py sdist
