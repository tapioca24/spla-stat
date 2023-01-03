from enum import Enum


class Lobby(Enum):
    REGULAR = "regular"
    BANKARA_OPEN = "bankara_open"
    BANKARA_CHALLENGE = "bankara_challenge"
    XMATCH = "xmatch"
    SPLATFEST_OPEN = "splatfest_open"
    SPLATFEST_CHALLENGE = "splatfest_challenge"
