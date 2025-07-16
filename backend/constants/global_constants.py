from datetime import timedelta
from db_enums import PaidUserStatus
from enum import IntEnum

kSessionTokenExpirationTime = timedelta(days=90)
kPasswordResetExpirationTime = timedelta(minutes=15)

productHashMap = {
    "privategpt1": "price_1Ne91bAuWN19h35KS9n8iokr",
    "privategpt2": "price_1Ne91NAuWN19h35KHFQtLZsQ",
    "privategpt3": "price_1Ne90vAuWN19h35Kb3DIpkfu"
}

priceToPaymentPlan = {
    "price_1Ne91bAuWN19h35KS9n8iokr" : PaidUserStatus.BASIC_TIER,
    "price_1Ne91NAuWN19h35KHFQtLZsQ" : PaidUserStatus.STANDARD_TIER,
    "price_1Ne90vAuWN19h35Kb3DIpkfu" : PaidUserStatus.PREMIUM_TIER
}

planToCredits = {
    PaidUserStatus.FREE_TIER: 0,
    PaidUserStatus.BASIC_TIER: 200,
    PaidUserStatus.STANDARD_TIER: 500,
    PaidUserStatus.PREMIUM_TIER: 1500
}

planToSearches = {
    PaidUserStatus.FREE_TIER: 0,
    PaidUserStatus.BASIC_TIER: 750,
    PaidUserStatus.STANDARD_TIER: 2000,
    PaidUserStatus.PREMIUM_TIER: 6000
}

chatgptLimit = 10000

dbName = "agents"
dbHost = "db"  # Docker service name for the database container
dbPassword = ""
dbUser = "root"

# TODO: COMMENT OUT WHEN DEPLOY TO PROD
# dbName = "agents"