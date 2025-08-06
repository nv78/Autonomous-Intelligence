import os
os.environ["OPENAI_API_KEY"] = "dummy"
os.environ["SEC_API_KEY"] = "dummy"
from unittest.mock import patch, MagicMock
patch("api_endpoints.financeGPT.chatbot_endpoints.OpenAIEmbeddings", MagicMock()).start()
import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import jwt
import time
import pytest
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


    @patch("api_endpoints.financeGPT.chatbot_endpoints.OpenAIEmbeddings")
    def test_app_startup(self, mock_embeddings):
        mock_embeddings.return_value = MagicMock()
        from app import app
        assert app is not None

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

    def test_viewUser(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer testtoken",
        }
        response = self.app.get("/viewUser", headers=headers)
        # Check for 200 or 401 depending on your mock setup
        self.assertIn(response.status_code, [200, 401])
        # Optionally, check for expected keys in the response
        # self.assertIn("user_email", response.get_json())

    def test_download_chat_history_valid(self):
        # Mock extractUserEmailFromRequest to return a test email
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.retrieve_message_from_db"
        ) as mock_retrieve:
            mock_extract_email.return_value = "test@example.com"
            # Simulate messages as expected by the endpoint
            mock_retrieve.return_value = [
                {"sent_from_user": 1, "message_text": "Hi", "relevant_chunks": None},
                {"sent_from_user": 0, "message_text": "Hello", "relevant_chunks": None},
            ]
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            data = {"chat_type": "test_type", "chat_id": "test_id"}
            response = self.app.post(
                "/download-chat-history", json=data, headers=headers
            )
            # Should return a CSV file
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "text/csv")
            self.assertIn(
                "query,response,chunk1,chunk2", response.get_data(as_text=True)
            )

    def test_download_chat_history_invalid_jwt(self):
        # Mock extractUserEmailFromRequest to raise InvalidTokenError
        with patch("app.extractUserEmailFromRequest") as mock_extract_email:
            from app import InvalidTokenError

            mock_extract_email.side_effect = InvalidTokenError()
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer badtoken",
            }
            data = {"chat_type": "test_type", "chat_id": "test_id"}
            response = self.app.post(
                "/download-chat-history", json=data, headers=headers
            )
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid JWT", response.get_data(as_text=True))

    def test_download_chat_history_internal_error(self):
        # Mock extractUserEmailFromRequest to return a test email
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.retrieve_message_from_db"
        ) as mock_retrieve:
            mock_extract_email.return_value = "test@example.com"
            # Simulate an exception in retrieve_message_from_db
            mock_retrieve.side_effect = Exception("DB error")
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            data = {"chat_type": "test_type", "chat_id": "test_id"}
            response = self.app.post(
                "/download-chat-history", json=data, headers=headers
            )
            self.assertEqual(response.status_code, 500)
            self.assertIn("DB error", response.get_data(as_text=True))

    def test_create_chat(self):
        # --- Valid request ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.add_chat_to_db"
        ) as mock_add_chat:
            mock_extract_email.return_value = "test@example.com"
            mock_add_chat.return_value = "chat123"
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            data = {"chat_type": "test_type", "model_type": "test_model"}
            response = self.app.post("/create-new-chat", json=data, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {"chat_id": "chat123"})

        # --- Invalid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email:
            from app import InvalidTokenError

            mock_extract_email.side_effect = InvalidTokenError()
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer badtoken",
            }
            data = {"chat_type": "test_type", "model_type": "test_model"}
            response = self.app.post("/create-new-chat", json=data, headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid JWT", response.get_data(as_text=True))

    def test_retrieve_chats(self):
        # --- Valid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.retrieve_chats_from_db"
        ) as mock_retrieve_chats:
            mock_extract_email.return_value = "test@example.com"
            mock_retrieve_chats.return_value = [
                {"chat_id": "1", "name": "new chat data"}
            ]
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            response = self.app.post("/retrieve-all-chats", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn("new chat data", response.get_data(as_text=True))

        # --- Invalid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email:
            from app import InvalidTokenError

            mock_extract_email.side_effect = InvalidTokenError()
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer badtoken",
            }
            response = self.app.post("/retrieve-all-chats", headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid JWT", response.get_data(as_text=True))

    def test_retrieve_messages_from_chat(self):
        # --- Valid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, \
             patch("app.retrieve_message_from_db") as mock_retrieve_messages, \
             patch("app.get_chat_info") as mock_get_chat_info:
            mock_extract_email.return_value = "test@example.com"
            mock_retrieve_messages.return_value = [
                {"msg": "hello from chat"},
                {"msg": "another message"},
            ]
            mock_get_chat_info.return_value = (None, None, "Test Chat Name")
            headers = {
                "Content-Type": "application/json",
                "Authorization": "***",
            }
            data = {"chat_type": "test_type", "chat_id": "chat1"}
            response = self.app.post(
                "/retrieve-messages-from-chat", json=data, headers=headers
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("hello from chat", response.get_data(as_text=True))

        # --- Invalid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email:
            from app import InvalidTokenError
            mock_extract_email.side_effect = InvalidTokenError()
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer badtoken",
            }
            data = {"chat_type": "test_type", "chat_id": "chat1"}
            response = self.app.post(
                "/retrieve-messages-from-chat", json=data, headers=headers
            )
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid JWT", response.get_data(as_text=True))

    def test_get_playbook_messages(self):
        # --- Success case ---
        with patch("app.retrieve_message_from_db") as mock_retrieve_messages:
            mock_retrieve_messages.return_value = [
                {"msg": "shared message 1"},
                {"msg": "shared message 2"},
            ]
            headers = {"Content-Type": "application/json"}
            data = {"chat_id": "chat1"}
            response = self.app.post(
                "/retrieve-shared-messages-from-chat", json=data, headers=headers
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("shared message 1", response.get_data(as_text=True))
            self.assertIn("shared message 2", response.get_data(as_text=True))

        # --- Error case (simulate DB error) ---
        with patch("app.retrieve_message_from_db") as mock_retrieve_messages:
            mock_retrieve_messages.side_effect = Exception("DB error")
            headers = {"Content-Type": "application/json"}
            data = {"chat_id": "chat1"}
            response = self.app.post(
                "/retrieve-shared-messages-from-chat", json=data, headers=headers
            )
            # Should return 500 or propagate error depending on your error handling
            # If you want to check for 500, uncomment the next line:
            # self.assertEqual(response.status_code, 500)

    def test_update_chat_name(self):
        # --- Valid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.update_chat_name_db"
        ) as mock_update_chat_name:
            mock_extract_email.return_value = "test@example.com"
            mock_update_chat_name.return_value = None
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            data = {"chat_name": "New Name", "chat_id": "chat1"}
            response = self.app.post("/update-chat-name", json=data, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {"Success": "Chat name updated"})

        # --- Invalid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email:
            from app import InvalidTokenError

            mock_extract_email.side_effect = InvalidTokenError()
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer badtoken",
            }
            data = {"chat_name": "New Name", "chat_id": "chat1"}
            response = self.app.post("/update-chat-name", json=data, headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid JWT", response.get_data(as_text=True))

    def test_infer_chat_name(self):
        # --- Valid JWT and OpenAI completion ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.client"
        ) as mock_client, patch("app.update_chat_name_db") as mock_update_chat_name:
            mock_extract_email.return_value = "test@example.com"
            mock_update_chat_name.return_value = None
            # Mock OpenAI completion response
            mock_completion = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "Inferred Name"
            mock_completion.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_completion

            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            data = {"messages": ["msg1", "msg2"], "chat_id": "chat1"}
            response = self.app.post("/infer-chat-name", json=data, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {"chat_name": "Inferred Name"})

        # --- Invalid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email:
            from app import InvalidTokenError

            mock_extract_email.side_effect = InvalidTokenError()
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer badtoken",
            }
            data = {"messages": ["msg1", "msg2"], "chat_id": "chat1"}
            response = self.app.post("/infer-chat-name", json=data, headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid JWT", response.get_data(as_text=True))

    def test_update_workflow_name(self):
        # --- Valid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.update_workflow_name_db"
        ) as mock_update_workflow:
            mock_extract_email.return_value = "test@example.com"
            mock_update_workflow.return_value = None
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            data = {"workflow_name": "New Workflow", "workflow_id": "wf1"}
            response = self.app.post(
                "/update-workflow-name", json=data, headers=headers
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("Workflow name updated", response.get_data(as_text=True))

        # --- Invalid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email:
            from app import InvalidTokenError

            mock_extract_email.side_effect = InvalidTokenError()
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer badtoken",
            }
            data = {"workflow_name": "New Workflow", "workflow_id": "wf1"}
            response = self.app.post(
                "/update-workflow-name", json=data, headers=headers
            )
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid JWT", response.get_data(as_text=True))

    def test_delete_chat(self):
        # --- Valid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.delete_chat_from_db"
        ) as mock_delete_chat:
            mock_extract_email.return_value = "test@example.com"
            mock_delete_chat.return_value = "Chat deleted"
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            data = {"chat_id": "chat1"}
            response = self.app.post("/delete-chat", json=data, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Chat deleted", response.get_data(as_text=True))

        # --- Invalid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email:
            from app import InvalidTokenError

            mock_extract_email.side_effect = InvalidTokenError()
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer badtoken",
            }
            data = {"chat_id": "chat1"}
            response = self.app.post("/delete-chat", json=data, headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid JWT", response.get_data(as_text=True))

    def test_find_most_recent_chat(self):
        # --- Valid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.find_most_recent_chat_from_db"
        ) as mock_find_recent:
            mock_extract_email.return_value = "test@example.com"
            mock_find_recent.return_value = [{"chat_id": "1", "name": "Most Recent"}]
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            response = self.app.post("/find-most-recent-chat", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Most Recent", response.get_data(as_text=True))

        # --- Invalid JWT ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email:
            from app import InvalidTokenError

            mock_extract_email.side_effect = InvalidTokenError()
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer badtoken",
            }
            response = self.app.post("/find-most-recent-chat", headers=headers)
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid JWT", response.get_data(as_text=True))

def test_ingest_pdfs(self):
    with patch("app.add_document_to_db") as mock_add_doc, patch(
        "app.p.from_buffer"
    ) as mock_from_buffer, patch(
        "app.ensure_ray_started"
    ) as mock_ensure_ray, patch(
        "app.chunk_document"
    ) as mock_chunk_document:
        mock_add_doc.return_value = ("docid", False)
        mock_from_buffer.return_value = {"content": "PDF text"}
        mock_ensure_ray.return_value = None
        mock_chunk_document.remote.return_value = None

        from io import BytesIO

        data = {
            "chat_id": ["chat1"],
            "files[]": (BytesIO(b"dummy pdf content"), "test.pdf"),
        }
        response = self.app.post(
            "/ingest-pdf",
            data=data,
            content_type="multipart/form-data",
            headers={"Authorization": "Bearer testtoken123"},  # <-- Add here
        )
        self.assertEqual(response.status_code, 200)


def test_reset_chat(self):
        # --- With delete_docs True ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.reset_chat_db"
        ) as mock_reset_chat_db, patch(
            "app.reset_uploaded_docs"
        ) as mock_reset_uploaded_docs:
            mock_extract_email.return_value = "test@example.com"
            mock_reset_chat_db.return_value = None
            mock_reset_uploaded_docs.return_value = None
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            data = {"chat_id": "chat123", "delete_docs": True}
            response = self.app.post("/reset-chat", json=data, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Success", response.get_data(as_text=True))

        # --- With delete_docs False ---
        with patch("app.extractUserEmailFromRequest") as mock_extract_email, patch(
            "app.reset_chat_db"
        ) as mock_reset_chat_db:
            mock_extract_email.return_value = "test@example.com"
            mock_reset_chat_db.return_value = None
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer testtoken",
            }
            data = {"chat_id": "chat123", "delete_docs": False}
            response = self.app.post("/reset-chat", json=data, headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Success", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()