"""Command-line interface to rhasspysupervisor"""
import argparse
import logging
import sys
from pathlib import Path

from rhasspyprofile import Profile

from . import profile_to_conf

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
        type=str,
        help="Directory with base profile files (read only, default=$CWD/profiles)",
    )
    parser.add_argument(
        "--user-profiles",
        type=str,
        help="Directory with user profile files (read/write, default=$HOME/.config/rhasspy/profiles)",
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

    if not args.user_profiles:
        args.user_profiles = Path("~/.config/rhasspy/profiles").expanduser()

    _LOGGER.debug(args)

    # Load profile
    _LOGGER.debug("Loading profile %s", args.profile)
    profile = Profile(args.profile, args.system_profiles, args.user_profiles)

    # Convert to supervisord conf
    profile_to_conf(profile, sys.stdout)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()
