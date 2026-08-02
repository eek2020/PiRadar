from __future__ import annotations

import argparse

from piradar.app import run
from piradar.config import Config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PiRadar appliance service")
    parser.add_argument("--config", help="path to a JSON configuration file")
    args = parser.parse_args()
    run(Config.load(args.config))


if __name__ == "__main__":
    main()

