PYTHON_NAME = rhasspysupervisor
PACKAGE_NAME = rhasspy-supervisor
PYTHON_FILES = $(PYTHON_NAME)/*.py *.py
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

venv: rhasspy-libs
	scripts/create-venv.sh

dist:
	python3 setup.py sdist

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------

docker: requirements_rhasspy.txt
	docker build . -t "rhasspy/$(PACKAGE_NAME):$(version)" -t "rhasspy/$(PACKAGE_NAME):latest"

deploy:
	echo "$$DOCKER_PASSWORD" | docker login -u "$$DOCKER_USERNAME" --password-stdin
	docker push "rhasspy/$(PACKAGE_NAME):$(version)"

# -----------------------------------------------------------------------------
# Debian
# -----------------------------------------------------------------------------

pyinstaller:
	scripts/build-pyinstaller.sh "${architecture}" "${version}"

debian:
	scripts/build-debian.sh "${architecture}" "${version}"

# -----------------------------------------------------------------------------
# Downloads
# -----------------------------------------------------------------------------

requirements_rhasspy.txt: requirements.txt
	grep '^rhasspy-' $< | sed -e 's|=.\+|/archive/master.tar.gz|' | sed 's|^|https://github.com/rhasspy/|' > $@

# Rhasspy development dependencies
rhasspy-libs: $(DOWNLOAD_DIR)/rhasspy-profile-0.1.3.tar.gz

$(DOWNLOAD_DIR)/rhasspy-profile-0.1.3.tar.gz:
	mkdir -p "$(DOWNLOAD_DIR)"
	curl -sSfL -o $@ "https://github.com/rhasspy/rhasspy-profile/archive/master.tar.gz"

$(DOWNLOAD_DIR)/rhasspy-nlu-0.1.6.tar.gz:
	mkdir -p "$(DOWNLOAD_DIR)"
	curl -sSfL -o $@ "https://github.com/rhasspy/rhasspy-nlu/archive/master.tar.gz"
