import aiosqlite
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FunchosaDatabase:
    def __init__(self, db_path='data/funchosa.db'):
        self.db_path = db_path
    
    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id BIGINT UNIQUE NOT NULL,
                    channel_id BIGINT NOT NULL,
                    author_id BIGINT NOT NULL,
                    author_name TEXT NOT NULL,
                    content TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    message_url TEXT NOT NULL,
                    has_attachments BOOLEAN DEFAULT 0,
                    attachment_urls TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER,
                    url TEXT UNIQUE NOT NULL,
                    filename TEXT,
                    FOREIGN KEY (message_id) REFERENCES messages (id)
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS parsing_status (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    first_parse_done BOOLEAN DEFAULT 0,
                    last_parsed_message_id BIGINT,
                    last_parse_time TIMESTAMP
                )
            ''')
         
            await db.execute('CREATE INDEX IF NOT EXISTS idx_message_id ON messages(message_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_author_id ON messages(author_id)')
            await db.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp)')
            
            await db.commit()
            logger.info("[FunchosaDatabase] funchosa db initialized")
    
    async def get_parsing_status(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT first_parse_done, last_parsed_message_id FROM parsing_status WHERE id = 1'
            )
            result = await cursor.fetchone()
            
            if result:
                return {
                    'first_parse_done': bool(result[0]),
                    'last_parsed_message_id': result[1]
                }
            else:
                await db.execute(
                    'INSERT INTO parsing_status (id, first_parse_done, last_parsed_message_id) VALUES (1, 0, NULL)'
                )
                await db.commit()
                return {
                    'first_parse_done': False,
                    'last_parsed_message_id': None
                }
    
    async def update_parsing_status(self, first_parse_done=False, last_parsed_message_id=None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE parsing_status 
                SET first_parse_done = ?, 
                    last_parsed_message_id = ?,
                    last_parse_time = CURRENT_TIMESTAMP
                WHERE id = 1
            ''', (first_parse_done, last_parsed_message_id))
            await db.commit()
    
    async def get_last_message_in_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT message_id FROM messages ORDER BY message_id DESC LIMIT 1'
            )
            result = await cursor.fetchone()
            return result[0] if result else None
    
    async def save_message(self, message_data):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT OR IGNORE INTO messages 
                (message_id, channel_id, author_id, author_name, content, 
                 timestamp, message_url, has_attachments, attachment_urls)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_data['message_id'],
                message_data['channel_id'],
                message_data['author_id'],
                message_data['author_name'],
                message_data['content'],
                message_data['timestamp'],
                message_data['message_url'],
                message_data['has_attachments'],
                message_data['attachment_urls']
            ))
            
            if cursor.rowcount > 0:
                message_db_id = cursor.lastrowid
                
                if message_data['attachments']:
                    for attachment in message_data['attachments']:
                        await db.execute('''
                            INSERT OR IGNORE INTO attachments 
                            (message_id, url, filename)
                            VALUES (?, ?, ?)
                        ''', (
                            message_db_id,
                            attachment['url'],
                            attachment['filename']
                        ))
                
                await db.commit()
                return True
            return False
    
    async def message_exists(self, message_id):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT 1 FROM messages WHERE message_id = ? LIMIT 1',
                (message_id,)
            )
            result = await cursor.fetchone()
            return result is not None
    
    async def get_random_message(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT m.*, 
                       GROUP_CONCAT(a.url) as attachment_urls_list,
                       GROUP_CONCAT(a.filename) as attachment_filenames
                FROM messages m
                LEFT JOIN attachments a ON m.id = a.message_id
                GROUP BY m.id
                ORDER BY RANDOM()
                LIMIT 1
            ''')
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            columns = [description[0] for description in cursor.description]
            message = dict(zip(columns, row))
            
            if message['attachment_urls_list']:
                urls = message['attachment_urls_list'].split(',')
                filenames = message['attachment_filenames'].split(',') if message['attachment_filenames'] else []
                message['attachments'] = [
                    {'url': url, 'filename': filename}
                    for url, filename in zip(urls, filenames)
                ]
            else:
                message['attachments'] = []
            
            return message
    
    async def get_total_count(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) FROM messages')
            result = await cursor.fetchone()
            return result[0] if result else 0
    
    async def get_message_by_number(self, number):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT m.*, 
                       GROUP_CONCAT(a.url) as attachment_urls_list,
                       GROUP_CONCAT(a.filename) as attachment_filenames
                FROM messages m
                LEFT JOIN attachments a ON m.id = a.message_id
                WHERE m.id = ?
                GROUP BY m.id
            ''', (number,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            columns = [description[0] for description in cursor.description]
            message = dict(zip(columns, row))
            
            if message.get('attachment_urls_list'):
                urls = message['attachment_urls_list'].split(',')
                filenames = message['attachment_filenames'].split(',') if message['attachment_filenames'] else []
                message['attachments'] = [
                    {'url': url, 'filename': filename}
                    for url, filename in zip(urls, filenames)
                ]
            else:
                message['attachments'] = []
            
            return message