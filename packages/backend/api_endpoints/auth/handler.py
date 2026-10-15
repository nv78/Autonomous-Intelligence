"""Authentication endpoints — register, login, refresh, Google and Microsoft sign-in."""
from __future__ import annotations

import os
import secrets
import urllib.parse
from typing import Any

import bcrypt
import requests as http_requests
from flask import Blueprint, current_app, jsonify, redirect, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from itsdangerous import BadData, URLSafeTimedSerializer

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
MICROSOFT_ME_URL = "https://graph.microsoft.com/v1.0/me?$select=userPrincipalName,displayName,givenName"


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


@auth_bp.post("/register")
def register() -> tuple:
    """Register a new user."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = data.get("name") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    try:
        from database.db import create_user, get_connection, get_user_by_email
        cnx = get_connection()
        if get_user_by_email(cnx, email):
            cnx.close()
            return jsonify({"error": "Email already registered"}), 409
        user_id = create_user(cnx, email, _hash_password(password), name)
        cnx.close()
        token = create_access_token(identity=str(user_id))
        return jsonify({"token": token, "userId": user_id, "isNewUser": True}), 201
    except Exception:
        return jsonify({"error": "Authentication service unavailable"}), 503


@auth_bp.post("/login")
def login() -> tuple:
    """Authenticate a user and return a JWT."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        from database.db import get_connection, get_user_by_email
        cnx = get_connection()
        user = get_user_by_email(cnx, email)
        cnx.close()
        if not user or not _check_password(password, user["password_hash"]):
            return jsonify({"error": "Invalid credentials"}), 401
        if _sso_required(email):
            return jsonify({"error": "Your organization requires signing in with Google or Microsoft.",
                            "code": "sso_required"}), 403
        token = create_access_token(identity=str(user["id"]))
        return jsonify({"token": token, "userId": user["id"]}), 200
    except Exception:
        return jsonify({"error": "Authentication service unavailable"}), 503


def _google_oauth_redirect_uri() -> str:
    return os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:5000/callback")


def _frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def _state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["JWT_SECRET_KEY"], salt="google-oauth-state")


def _build_google_auth_url(client_id: str) -> str:
    state = _state_serializer().dumps(secrets.token_urlsafe(16))
    params = {
        "client_id": client_id,
        "redirect_uri": _google_oauth_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        # Forces Google to show its credential entry screen instead of
        # silently reusing an existing browser session or the account
        # picker — Google has no "prompt=login"; max_auth_age=0 is the
        # documented way to force re-authentication.
        "max_auth_age": "0",
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


@auth_bp.get("/google/login")
def google_login_start():
    """Redirect the browser to Google's OAuth consent screen."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id:
        return jsonify({"error": "Google sign-in is not configured"}), 503

    return redirect(_build_google_auth_url(client_id))


@auth_bp.get("/google/url")
def google_login_url():
    """Return Google's OAuth consent screen URL as JSON, for client-driven redirects."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id:
        return jsonify({"error": "Google sign-in is not configured"}), 503

    return jsonify({"url": _build_google_auth_url(client_id)}), 200


def google_oauth_callback():
    """Handle Google's redirect back with an authorization code.

    Registered directly on the Flask app (not under the /auth blueprint) as
    /callback so its URL matches the redirect URI configured in Google Cloud
    Console exactly.
    """
    frontend_url = _frontend_url()

    if request.args.get("error"):
        return redirect(f"{frontend_url}/login?error=google_denied")

    code = request.args.get("code")
    state = request.args.get("state")
    if not code or not state:
        return redirect(f"{frontend_url}/login?error=missing_code")

    try:
        _state_serializer().loads(state, max_age=600)
    except BadData:
        return redirect(f"{frontend_url}/login?error=invalid_state")

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return redirect(f"{frontend_url}/login?error=not_configured")

    try:
        token_resp = http_requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": _google_oauth_redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
    except http_requests.RequestException:
        current_app.logger.exception("Google OAuth token request failed")
        return redirect(f"{frontend_url}/login?error=google_auth_failed")

    if not token_resp.ok:
        current_app.logger.error(
            "Google OAuth token exchange rejected (status %s): %s",
            token_resp.status_code, token_resp.text,
        )
        return redirect(f"{frontend_url}/login?error=google_auth_failed")

    try:
        id_token_str = token_resp.json().get("id_token", "")
        claims = google_id_token.verify_oauth2_token(
            id_token_str, google_requests.Request(), client_id, clock_skew_in_seconds=10
        )
    except ValueError:
        current_app.logger.exception("Google ID token verification failed")
        return redirect(f"{frontend_url}/login?error=google_auth_failed")

    email = (claims.get("email") or "").strip().lower()
    if not email or not claims.get("email_verified"):
        return redirect(f"{frontend_url}/login?error=unverified_email")
    # ``hd`` is set only for Google Workspace accounts the domain's admin manages;
    # a personal Google account registered on a company address has none.
    return _finish_sso(email, claims.get("given_name") or claims.get("name") or "", str(claims.get("hd") or ""))


def _sso_required(email: str) -> bool:
    try:
        from coworker import orgs
        from coworker.store import get_store

        return orgs.sso_required(get_store(), email)
    except Exception:  # the coworker store being down must not lock everyone out
        current_app.logger.exception("Couldn't check the organization's sign-in policy")
        return False


def _finish_sso(email: str, name: str, managed_domain: str) -> Any:
    """Sign in (or sign up) a user whose address the identity provider verified.

    ``managed_domain`` is the domain the provider says the account's
    organization controls; only that can auto-join an organization.
    """
    frontend_url = _frontend_url()
    try:
        from database.db import create_user, get_connection, get_user_by_email
        cnx = get_connection()
        user = get_user_by_email(cnx, email)
        is_new_user = not user
        if not user:
            random_password = _hash_password(secrets.token_urlsafe(32))
            user_id = create_user(cnx, email, random_password, name)
        else:
            user_id = user["id"]
        cnx.close()
    except Exception:
        return redirect(f"{frontend_url}/login?error=service_unavailable")

    try:  # a verified company address joins its organization if automatic joining is on
        from coworker import orgs
        from coworker.store import get_store

        joined = orgs.on_sso_login(get_store(), int(user_id), email, managed_domain)
        if joined:
            from coworker import billing

            billing.sync_seats(get_store(), joined)
    except Exception:
        current_app.logger.exception("Couldn't apply organization auto-join")

    token = create_access_token(identity=str(user_id))
    new_user_param = "&isNewUser=1" if is_new_user else ""
    return redirect(
        f"{frontend_url}/oauth/callback?token={urllib.parse.quote(token)}{new_user_param}"
    )


# -- Microsoft (Entra ID) sign-in --------------------------------------------------
# Uses the same app registration as the Outlook connector (MICROSOFT_CLIENT_ID /
# MICROSOFT_CLIENT_SECRET / MICROSOFT_TENANT); add this redirect URI to it.

def _microsoft_redirect_uri() -> str:
    default = f"{os.environ.get('BACKEND_URL', 'http://localhost:5000').rstrip('/')}/auth/microsoft/callback"
    return os.environ.get("MICROSOFT_LOGIN_REDIRECT_URI", default)


def _microsoft_state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["JWT_SECRET_KEY"], salt="microsoft-login-state")


def _build_microsoft_auth_url() -> str:
    from coworker.connectors import microsoft

    params = {
        "client_id": os.environ.get("MICROSOFT_CLIENT_ID", ""),
        "redirect_uri": _microsoft_redirect_uri(),
        "response_type": "code",
        "response_mode": "query",
        "scope": "openid email profile User.Read",
        "state": _microsoft_state_serializer().dumps(secrets.token_urlsafe(16)),
        "prompt": "select_account",
    }
    return f"{microsoft._authority()}/authorize?{urllib.parse.urlencode(params)}"


@auth_bp.get("/microsoft/login")
def microsoft_login_start():
    from coworker.connectors import microsoft

    if not microsoft.is_configured():
        return jsonify({"error": "Microsoft sign-in is not configured"}), 503
    return redirect(_build_microsoft_auth_url())


@auth_bp.get("/microsoft/url")
def microsoft_login_url():
    from coworker.connectors import microsoft

    if not microsoft.is_configured():
        return jsonify({"error": "Microsoft sign-in is not configured"}), 503
    return jsonify({"url": _build_microsoft_auth_url()}), 200


@auth_bp.get("/microsoft/callback")
def microsoft_login_callback():
    """Exchange the code, then take the address from the user's userPrincipalName.

    The UPN must be on a domain the tenant verified; the ``email``/``mail``
    claims are not (any tenant admin can set them), so they're never trusted.
    Guest accounts (``#EXT#``) are refused for the same reason.
    """
    from coworker.connectors import microsoft

    frontend_url = _frontend_url()
    if request.args.get("error"):
        return redirect(f"{frontend_url}/login?error=microsoft_denied")
    code, state = request.args.get("code"), request.args.get("state")
    if not code or not state:
        return redirect(f"{frontend_url}/login?error=missing_code")
    try:
        _microsoft_state_serializer().loads(state, max_age=600)
    except BadData:
        return redirect(f"{frontend_url}/login?error=invalid_state")
    if not microsoft.is_configured():
        return redirect(f"{frontend_url}/login?error=not_configured")
    try:
        token_resp = http_requests.post(f"{microsoft._authority()}/token", data={
            "client_id": os.environ.get("MICROSOFT_CLIENT_ID", ""),
            "client_secret": os.environ.get("MICROSOFT_CLIENT_SECRET", ""),
            "code": code, "redirect_uri": _microsoft_redirect_uri(), "grant_type": "authorization_code",
            "scope": "openid email profile User.Read",
        }, timeout=10)
        if not token_resp.ok:
            current_app.logger.error("Microsoft token exchange rejected (status %s): %s", token_resp.status_code, token_resp.text)
            return redirect(f"{frontend_url}/login?error=microsoft_auth_failed")
        me = http_requests.get(MICROSOFT_ME_URL, timeout=10,
                               headers={"Authorization": f"Bearer {token_resp.json().get('access_token', '')}"})
        if not me.ok:
            current_app.logger.error("Microsoft profile lookup failed (status %s)", me.status_code)
            return redirect(f"{frontend_url}/login?error=microsoft_auth_failed")
        profile = me.json()
    except (http_requests.RequestException, ValueError):
        current_app.logger.exception("Microsoft sign-in failed")
        return redirect(f"{frontend_url}/login?error=microsoft_auth_failed")
    email = str(profile.get("userPrincipalName") or "").strip().lower()
    if "@" not in email or "#ext#" in email:
        return redirect(f"{frontend_url}/login?error=unverified_email")
    # A tenant can only issue UPNs on domains it verified, so the UPN's domain is managed.
    return _finish_sso(email, str(profile.get("givenName") or profile.get("displayName") or ""), email.split("@")[-1])


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh() -> tuple:
    """Refresh a JWT access token."""
    identity = get_jwt_identity()
    token = create_access_token(identity=identity)
    return jsonify({"token": token}), 200


@auth_bp.get("/me")
@jwt_required()
def me() -> tuple:
    """Return the current user's identity."""
    identity = get_jwt_identity()
    return jsonify({"userId": identity}), 200
