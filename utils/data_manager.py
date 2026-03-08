import json
import os
from config import roles_message_id

def save_message_id(message_id):
    os.makedirs('data', exist_ok=True)
    with open(roles_message_id, 'w') as f:
        json.dump({'message_id': message_id}, f)

def load_message_id():
    try:
        with open(roles_message_id, 'r') as f:
            data = json.load(f)
            return data.get('message_id')
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None