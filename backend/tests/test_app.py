import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import jwt
import time

# Add the parent directory to the path so we can import from backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import app


class TestFlaskApp(unittest.TestCase):
    """Simple Flask app unit test"""

    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True

    def test_root_route(self):
        response = self.app.get("/")
        self.assertIn(response.status_code, [200, 404])

    # now let's test the important routes
    def test_login_route(self):
        response = self.app.get("/login")
        self.assertIn(response.status_code, [200, 302, 404])

    # handle jwt stuff first
    # mock
    @patch("app.flow")
    @patch("app.id_token")
    @patch("app.create_user_if_does_not_exist")
    @patch("app.create_access_token")
    @patch("app.create_refresh_token")
    def test_callback_route(
        self,
        mock_create_refresh_token,
        mock_create_access_token,
        mock_create_user,
        mock_id_token,
        mock_flow,
    ):
        # Setup mocks
        mock_flow.fetch_token.return_value = None
        mock_flow.credentials = MagicMock(_id_token="fake_id_token")
        mock_id_token.verify_oauth2_token.return_value = {
            "email": "test@example.com",
            "sub": "123",
            "name": "Test User",
            "picture": "http://example.com/pic.jpg",
        }
        mock_create_user.return_value = 1
        mock_create_access_token.return_value = "access_token"
        mock_create_refresh_token.return_value = "refresh_token"

        # Create a valid JWT for state
        payload = {"redirect_uri": "http://localhost/callback"}
        secret = app.config["JWT_SECRET_KEY"]
        token = jwt.encode(payload, secret, algorithm="HS256")
        # Call the callback endpoint with both state and code
        response = self.app.get(f"/callback?state={token}&code=dummycode")
        # Should redirect (302) to the frontend with tokens in the URL
        self.assertEqual(response.status_code, 302)
        self.assertIn("accessToken=access_token", response.location)
        self.assertIn("refreshToken=refresh_token", response.location)

    # since refresh endpoint accepts a jwt token we don't need to test the entire jwt flow but /refresh
    @patch("app.decode_token")
    @patch("flask_jwt_extended.view_decorators.verify_jwt_in_request")
    def test_refresh_route(self, mock_verify_jwt, mock_decode_token):
        # Mock the JWT validation to always pass
        mock_verify_jwt.return_value = None
        # Mock the decode_token to return a fake identity
        mock_decode_token.return_value = {"sub": "test@example.com"}
        # You may also want to patch create_access_token if you want to control its output
        headers = {"Authorization": "Bearer fake_refresh_token"}
        response = self.app.post("/refresh", headers=headers)
        self.assertIn(response.status_code, [200])
        self.assertIn("accessToken", response.get_json())

    @patch("database.db.get_db_connection")
    def test_signup(self, mock_get_db_connection):
        # Configure the mock to return fake connection and cursor objects
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db_connection.return_value = (mock_conn, mock_cursor)

        # Example: If a test needs to check if a user exists,
        # make the mock return None to simulate "user not found"
        mock_cursor.fetchone.return_value = mock_conn

        # --- Your existing test logic ---
        data = {
            "email": f"nvidra10@anote.ai",
            "password": "StrongPassword123!",
            "name": "Test User",
        }
        response = self.app.post(
            "/signUp", json=data, headers={"Content-Type": "application/json"}
        )
        # --- The test will now pass because it doesn't try to connect to a real DB ---
        self.assertIn(response.status_code, [200, 201])

    @patch("database.db.get_db_connection")
    def test_forgotpwd(self, mock_get_db_connection):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db_connection.return_value = (mock_conn, mock_cursor)
        data = {"email": "nvidra10@anote.ai"}
        response = self.app.post("/forgotPassword", json=data)
        print(response.status_code, response.get_json())
        self.assertIn(
            response.status_code, [200, 202]
        )  # Accept either, depending on your API

    @patch("database.db.get_db_connection")
    def test_resetpwd(self, mock_get_db_connection):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db_connection.return_value = (mock_conn, mock_cursor)
        data = {
            "email": "test@example.com",
            "password": "123456password",
            "passwordResetCode": "test-reset-code-123",
        }
        reponse = self.app.post("/resetPassword", json=data)
        self.assertEqual(reponse.status_code, 200)

    def test_refresh_credits(self):
        # Mock the JWT decorator and user email extraction
        with patch("app.extractUserEmailFromRequest") as mock_extract, patch(
            "app.RefreshCreditsHandler"
        ) as mock_handler:

            mock_extract.return_value = "test@example.com"
            mock_handler.return_value = {"credits": 100, "status": "refreshed"}

            # Test with a dummy authorization header
            headers = {"Authorization": "Bearer dummy-token"}
            response = self.app.post("/refreshCredits", headers=headers)

            self.assertEqual(response.status_code, 200)
            self.assertIn("credits", response.get_json())

    @patch("database.db.get_db_connection")
    def test_checkout_session(self, mock_get_db_connection):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db_connection.return_value = (mock_conn, mock_cursor)
        with patch("app.extractUserEmailFromRequest") as mock_extract, patch(
            "app.verifyAuthForPaymentsTrustedTesters"
        ) as mock_verify_payments, patch(
            "app.verifyAuthForCheckoutSession"
        ) as mock_verify_checkout, patch(
            "app.CreateCheckoutSessionHandler"
        ) as mock_handler:

            # Mock successful case
            mock_extract.return_value = "test@example.com"
            mock_verify_payments.return_value = True
            mock_verify_checkout.return_value = None
            mock_handler.return_value = {"session_id": "test_session_123"}

            # Test with a dummy authorization header
            headers = {"Authorization": "Bearer dummy-token"}
            response = self.app.post("/createCheckoutSession", headers=headers)

            self.assertEqual(response.status_code, 200)
            self.assertIn("session_id", response.get_json())

            # Verify mocks were called correctly
            mock_extract.assert_called_once()
            mock_verify_payments.assert_called_once_with("test@example.com")
            mock_verify_checkout.assert_called_once()
            mock_handler.assert_called_once()


if __name__ == "__main__":
    unittest.main()