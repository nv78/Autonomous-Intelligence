from api_endpoints.financeGPT.chatbot_endpoints import retrieve_chats_from_db, retrieve_chats_url_from_db, retrieve_message_from_db
from database import get_db_connection
from api_endpoints.financeGPT.chatbot_endpoints import get_messages_by_chat_id, get_chat_url_by_id

def shareable_playbook_handler(chat_id):
    return get_chat_url_by_id(chat_id)

def get_previous_chat_by_url(url_id):
    conn, cursor = get_db_connection()

    cursor.execute("""
        SELECT id, chat_name, created, model_type, ticker, associated_task, custom_model_key
        FROM chats
        WHERE chat_sharable_url = %s
    """, (url_id,))
    chat = cursor.fetchone()

    if not chat:
        conn.close()
        return None

    chat_id = chat['id']
    messages = get_messages_by_chat_id(chat_id)

    chat_data = {
        "chat_id": chat_id,
        "chat_name": chat['chat_name'],
        "created": chat['created'],
        "model_type": chat['model_type'],
        "ticker": chat['ticker'],
        "associated_task": chat['associated_task'],
        "custom_model_key": chat['custom_model_key'],
        "messages": [
            {
                "message_id": m['message_id'],
                "text": m['message_text'],
                "sent_from_user": bool(m['sent_from_user']),
                "created": m['message_created'],
                "relevant_chunks": m['relevant_chunks']
            }
            for m in messages if m['message_text']
        ]
    }

    conn.close()
    return chat_data
