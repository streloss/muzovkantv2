import aiosqlite
import logging

logger = logging.getLogger(__name__)


class FunchosaDatabase:
    def __init__(self, db_path='data/funchosa.db'):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init_db(self):
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row

        await self._conn.executescript('''
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                url TEXT UNIQUE NOT NULL,
                filename TEXT,
                FOREIGN KEY (message_id) REFERENCES messages (id)
            );

            CREATE TABLE IF NOT EXISTS parsing_status (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                first_parse_done BOOLEAN DEFAULT 0,
                last_parsed_message_id BIGINT,
                last_parse_time TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_message_id ON messages(message_id);
            CREATE INDEX IF NOT EXISTS idx_author_id ON messages(author_id);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp);
        ''')
        await self._conn.commit()
        logger.info("Database initialized")

    async def close(self):
        if self._conn:
            await self._conn.close()

    def _parse_message_row(self, row) -> dict:
        message = dict(row)
        if message.get('attachment_urls_list'):
            urls = message['attachment_urls_list'].split(',')
            filenames = (message['attachment_filenames'] or '').split(',')
            message['attachments'] = [
                {'url': url, 'filename': filename}
                for url, filename in zip(urls, filenames)
            ]
        else:
            message['attachments'] = []
        return message

    async def get_parsing_status(self) -> dict:
        cursor = await self._conn.execute(
            'SELECT first_parse_done, last_parsed_message_id FROM parsing_status WHERE id = 1'
        )
        result = await cursor.fetchone()
        if result:
            return {'first_parse_done': bool(result[0]), 'last_parsed_message_id': result[1]}

        await self._conn.execute(
            'INSERT INTO parsing_status (id, first_parse_done, last_parsed_message_id) VALUES (1, 0, NULL)'
        )
        await self._conn.commit()
        return {'first_parse_done': False, 'last_parsed_message_id': None}

    async def update_parsing_status(self, first_parse_done=False, last_parsed_message_id=None):
        await self._conn.execute('''
            UPDATE parsing_status
            SET first_parse_done = ?,
                last_parsed_message_id = ?,
                last_parse_time = CURRENT_TIMESTAMP
            WHERE id = 1
        ''', (first_parse_done, last_parsed_message_id))
        await self._conn.commit()

    async def get_last_message_in_db(self):
        cursor = await self._conn.execute(
            'SELECT message_id FROM messages ORDER BY message_id DESC LIMIT 1'
        )
        result = await cursor.fetchone()
        return result[0] if result else None

    async def save_message(self, message_data: dict) -> bool:
        cursor = await self._conn.execute('''
            INSERT OR IGNORE INTO messages
            (message_id, channel_id, author_id, author_name, content,
             timestamp, message_url, has_attachments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message_data['message_id'],
            message_data['channel_id'],
            message_data['author_id'],
            message_data['author_name'],
            message_data['content'],
            message_data['timestamp'],
            message_data['message_url'],
            message_data['has_attachments'],
        ))

        if cursor.rowcount > 0:
            message_db_id = cursor.lastrowid
            for attachment in message_data.get('attachments', []):
                await self._conn.execute('''
                    INSERT OR IGNORE INTO attachments (message_id, url, filename)
                    VALUES (?, ?, ?)
                ''', (message_db_id, attachment['url'], attachment['filename']))
            await self._conn.commit()
            return True
        return False

    async def message_exists(self, message_id: int) -> bool:
        cursor = await self._conn.execute(
            'SELECT 1 FROM messages WHERE message_id = ? LIMIT 1', (message_id,)
        )
        return await cursor.fetchone() is not None

    async def get_random_message(self) -> dict | None:
        cursor = await self._conn.execute('''
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
        return self._parse_message_row(row) if row else None

    async def get_message_by_number(self, number: int) -> dict | None:
        cursor = await self._conn.execute('''
            SELECT m.*,
                   GROUP_CONCAT(a.url) as attachment_urls_list,
                   GROUP_CONCAT(a.filename) as attachment_filenames
            FROM messages m
            LEFT JOIN attachments a ON m.id = a.message_id
            WHERE m.id = ?
            GROUP BY m.id
        ''', (number,))
        row = await cursor.fetchone()
        return self._parse_message_row(row) if row else None

    async def get_total_count(self) -> int:
        cursor = await self._conn.execute('SELECT COUNT(*) FROM messages')
        result = await cursor.fetchone()
        return result[0] if result else 0