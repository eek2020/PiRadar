"""Router scenarios for the PiRadar emulator.

Each scenario describes the Wi-Fi networks the emulated Pi can see and how
the router responds to a connection attempt from a Pi 3. The password for
every emulated network is the same, so it is easy to remember while
clicking through: ``radar-test-1``. Use ``--list`` on the launcher to see them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from emulator.device import COMPAT_OPTION, Network, Profile, SECRETS_ERROR

if TYPE_CHECKING:
    from emulator.device import EmulatedPi

PASSWORD = "radar-test-1"


@dataclass
class Scenario:
    name: str
    summary: str
    networks: list[Network]
    # Decides the outcome of a connection with this key: None means connected,
    # otherwise a failure kind from FAILURE_MESSAGES.
    rule: Callable[["EmulatedPi", Network, str], str | None]
    # Optional set-up, e.g. a stale profile left by earlier attempts.
    setup: Callable[["EmulatedPi"], None] | None = None
    notes: list[str] = field(default_factory=list)

    # What nmcli prints for each kind of failure (stderr), as on a real Pi.
    FAILURE_MESSAGES = {
        "wrong_key": SECRETS_ERROR,
        "sae_offload": SECRETS_ERROR,     # same text: that is what makes it hard
        "wpa3_only": "Error: Connection activation failed: (7) Secrets were required, but not provided.",
        "timeout": "Error: Timeout expired (30 seconds)",
        "no_dhcp": "Error: Connection activation failed: IP configuration could not be reserved (no available address, timeout, etc.).",
    }

    def network(self, ssid: str) -> Network | None:
        return next((n for n in self.networks if n.ssid == ssid), None)

    def outcome(self, pi: "EmulatedPi", network: Network, key: str) -> str | None:
        return self.rule(pi, network, key)

    def prepare(self, pi: "EmulatedPi") -> None:
        if self.setup:
            self.setup(pi)


def _right_key(rule: Callable[["EmulatedPi", Network], str | None]) -> Callable[["EmulatedPi", Network, str], str | None]:
    """Open networks connect; a wrong key fails; otherwise apply the scenario's rule."""
    def decide(pi: "EmulatedPi", network: Network, key: str) -> str | None:
        if network.security in {"", "--"}:
            return None                     # open networks need no key
        if key != PASSWORD:
            return "wrong_key"
        return rule(pi, network)
    return decide


def _pi3_handshake(pi: "EmulatedPi", network: Network) -> str | None:
    """WPA2/WPA3 mixed mode: a Pi 3's firmware handshake fails until
    compatibility mode is active, meaning saved AND restarted."""
    return None if COMPAT_OPTION in pi.running_line else "sae_offload"


def _stale_profile(pi: "EmulatedPi") -> None:
    # An earlier attempt with a typo left this saved, wrong key and all.
    import uuid
    stale = Profile(str(uuid.uuid4()), "802-11-wireless", "Neighbour-Hub", "radar-test-l")
    pi.profiles[stale.uuid] = stale
    pi.log("NetworkManager[612]", "<info>  device (wlan0): Activation: starting connection 'Neighbour-Hub' (earlier attempt)")
    pi.log("wpa_supplicant[540]", "wlan0: WPA: 4-Way Handshake failed - pre-shared key may be incorrect")


SCENARIOS: dict[str, Scenario] = {
    s.name: s
    for s in [
        Scenario(
            "home",
            "A normal WPA2 router. The right password connects first time.",
            [Network("Home-Hub", "WPA2", 78), Network("Next-Door-Guest", "--", 34, 11, "(none)", "AA:BB:CC:44:55:66")],
            _right_key(lambda pi, network: None),
        ),
        Scenario(
            "wpa3-mixed",
            "Router in WPA2/WPA3 mixed mode. A Pi 3 fails with the right password "
            "until Wi-Fi compatibility mode is on and the Pi has restarted.",
            [Network("BT-Hub", "WPA2 WPA3", 71, 6, "pair_ccmp group_ccmp psk sae")],
            _right_key(_pi3_handshake),
            notes=["Try: connect (fails) -> control panel 'Compat on' -> 'Restart Pi' -> connect (works)."],
        ),
        Scenario(
            "neighbour",
            "Your neighbour's symptom: WPA2 network, earlier failed attempts left a "
            "saved profile with a wrong key. Older PiRadar versions fail even with "
            "the right password; current ones clear the profile and connect.",
            [Network("Neighbour-Hub", "WPA2", 64, 1)],
            _right_key(lambda pi, network: None),
            setup=_stale_profile,
        ),
        Scenario(
            "wpa3-only",
            "Router set to WPA3 only. A Pi 3 cannot join it at all, compatibility mode or not.",
            [Network("Fibre-WPA3", "WPA3", 70, 11, "pair_ccmp group_ccmp sae")],
            _right_key(lambda pi, network: "wpa3_only"),
        ),
        Scenario(
            "weak-signal",
            "Router at the edge of range: attempts time out.",
            [Network("Garden-Office", "WPA2", 14, 1)],
            _right_key(lambda pi, network: "timeout"),
        ),
        Scenario(
            "no-dhcp",
            "Router accepts the password but gives PiRadar no address (MAC filter or device limit).",
            [Network("Locked-Down", "WPA2", 66, 6)],
            _right_key(lambda pi, network: "no_dhcp"),
        ),
    ]
}
