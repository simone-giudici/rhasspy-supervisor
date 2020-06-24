# Rhasspy Supervisor

[![Continous Integration](https://github.com/rhasspy/rhasspy-supervisor/workflows/Tests/badge.svg)](https://github.com/rhasspy/rhasspy-supervisor/actions)
[![PyPI package version](https://img.shields.io/pypi/v/rhasspy-supervisor.svg)](https://pypi.org/project/rhasspy-supervisor)
[![Python versions](https://img.shields.io/pypi/pyversions/rhasspy-supervisor.svg)](https://www.python.org)
[![GitHub license](https://img.shields.io/github/license/rhasspy/rhasspy-supervisor.svg)](https://github.com/rhasspy/rhasspy-supervisor/blob/master/LICENSE)

Generates a [supervisord](http://supervisord.org/) configuration from a Rhasspy profile.

## Requirements

* Python 3.7

## Installation

```bash
$ git clone https://github.com/rhasspy/rhasspy-supervisor
$ cd rhasspy-supervisor
$ ./configure
$ make
$ make install
```

## Running

```bash
$ bin/rhasspy-supervisor <ARGS>
```

## Command-Line Options

```
usage: rhasspysupervisor [-h] --profile PROFILE
                         [--system-profiles SYSTEM_PROFILES]
                         [--user-profiles USER_PROFILES]
                         [--supervisord-conf SUPERVISORD_CONF]
                         [--docker-compose DOCKER_COMPOSE]
                         [--local-mqtt-port LOCAL_MQTT_PORT] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --profile PROFILE, -p PROFILE
                        Name of profile to load
  --system-profiles SYSTEM_PROFILES
                        Directory with base profile files (read only,
                        default=bundled)
  --user-profiles USER_PROFILES
                        Directory with user profile files (read/write,
                        default=$HOME/.config/rhasspy/profiles)
  --supervisord-conf SUPERVISORD_CONF
                        Name of supervisord configuration file to write in
                        profile (default: supervisord.conf)
  --docker-compose DOCKER_COMPOSE
                        Name of docker-compose YAML file to write in profile
                        (default: docker-compose.yml)
  --local-mqtt-port LOCAL_MQTT_PORT
                        Port to use for internal MQTT broker (default: 12183)
  --debug               Print DEBUG message to console
```
