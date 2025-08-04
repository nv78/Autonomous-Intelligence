from enum import IntEnum

class PaidUserStatus(IntEnum):
    FREE_TIER = 0
    BASIC_TIER = 1
    STANDARD_TIER = 2
    PREMIUM_TIER = 3
    ENTERPRISE_TIER = 4