"""Command-line interface to rhasspysupervisor"""
import argparse
import logging
from pathlib import Path

from rhasspyprofile import Profile

from . import profile_to_conf, profile_to_docker

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------------


def main():
    """Main method"""
    parser = argparse.ArgumentParser("rhasspysupervisor")
    parser.add_argument(
        "--profile", "-p", required=True, type=str, help="Name of profile to load"
    )
    parser.add_argument(
        "--system-profiles",
        help="Directory with base profile files (read only, default=$CWD/profiles)",
    )
    parser.add_argument(
        "--user-profiles",
        help="Directory with user profile files (read/write, default=$HOME/.config/rhasspy/profiles)",
    )
    parser.add_argument(
        "--supervisord-conf",
        default="supervisord.conf",
        help="Name of supervisord configuration file to write in profile (default: supervisord.conf)",
    )
    parser.add_argument(
        "--docker-compose",
        default="docker-compose.yml",
        help="Name of docker-compose YAML file to write in profile (default: docker-compose.yml)",
    )
    parser.add_argument(
        "--local-mqtt-port",
        type=int,
        default=12183,
        help="Port to use for internal MQTT broker (default: 12183)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Print DEBUG message to console"
    )
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if not args.system_profiles:
        args.system_profiles = Path("profiles")
    else:
        args.system_profiles = Path(args.system_profiles)

    if not args.user_profiles:
        args.user_profiles = Path("~/.config/rhasspy/profiles").expanduser()
    else:
        args.user_profiles = Path(args.user_profiles)

    _LOGGER.debug(args)

    # Load profile
    _LOGGER.debug("Loading profile %s", args.profile)
    profile = Profile(args.profile, args.system_profiles, args.user_profiles)

    # Convert to supervisord conf
    supervisord_conf_path = args.user_profiles / args.profile / args.supervisord_conf

    with open(supervisord_conf_path, "w") as conf_file:
        profile_to_conf(profile, conf_file, local_mqtt_port=args.local_mqtt_port)

    _LOGGER.debug("Wrote %s", str(supervisord_conf_path))

    # Convert to docker compose
    docker_compose_path = args.user_profiles / args.profile / args.docker_compose

    with open(docker_compose_path, "w") as yml_file:
        profile_to_docker(profile, yml_file, local_mqtt_port=args.local_mqtt_port)

    _LOGGER.debug("Wrote %s", str(docker_compose_path))


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
