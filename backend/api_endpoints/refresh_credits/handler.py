from database.db import refresh_credits

def RefreshCreditsHandler(request, user_email):
    return refresh_credits(user_email)