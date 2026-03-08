import json
import os

MESSAGE_ID_FILE = 'data/message_id.json' #ts for roles

def save_message_id(message_id):
    os.makedirs('data', exist_ok=True)
    with open(MESSAGE_ID_FILE, 'w') as f:
        json.dump({'message_id': message_id}, f)

def load_message_id():
    try:
        with open(MESSAGE_ID_FILE, 'r') as f:
            data = json.load(f)
            return data.get('message_id')
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None