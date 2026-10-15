import os
import json
import sqlite3
from datetime import datetime
from contextlib import closing
from utils.helpers import get_data_path
from utils.logger import logger

class HistoryManager:
    def __init__(self):
        self.data_dir = get_data_path('data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_file = os.path.join(self.data_dir, 'history.db')
        self.old_json_file = os.path.join(self.data_dir, 'history.json')
        self._init_db()
        self._migrate_from_json()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=2.0)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL;')
        conn.execute('PRAGMA synchronous=NORMAL;')
        return conn

    def _init_db(self):
        with closing(self._get_connection()) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS downloads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT,
                        title TEXT,
                        duration TEXT,
                        size TEXT,
                        type TEXT,
                        date TEXT,
                        thumb_path TEXT,
                        save_path TEXT,
                        UNIQUE(url, type)
                    )
                ''')
                # Migrate legacy table if it had UNIQUE(url) only
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='downloads'")
                row = cursor.fetchone()
                if row and "url TEXT UNIQUE" in (row['sql'] or ""):
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS downloads_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            url TEXT,
                            title TEXT,
                            duration TEXT,
                            size TEXT,
                            type TEXT,
                            date TEXT,
                            thumb_path TEXT,
                            save_path TEXT,
                            UNIQUE(url, type)
                        )
                    ''')
                    cursor.execute('''
                        INSERT OR REPLACE INTO downloads_new (id, url, title, duration, size, type, date, thumb_path, save_path)
                        SELECT id, url, title, duration, size, type, date, thumb_path, save_path FROM downloads
                    ''')
                    cursor.execute('DROP TABLE downloads')
                    cursor.execute('ALTER TABLE downloads_new RENAME TO downloads')

                cursor.execute('CREATE INDEX IF NOT EXISTS idx_url_date ON downloads (url, date)')

    def _migrate_from_json(self):
        if not os.path.exists(self.old_json_file):
            return
            
        try:
            with open(self.old_json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if isinstance(data, list) and data:
                with closing(self._get_connection()) as conn:
                    with conn:
                        cursor = conn.cursor()
                        for entry in data:
                            cursor.execute('''
                                INSERT OR REPLACE INTO downloads 
                                (url, title, duration, size, type, date, thumb_path, save_path)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                entry.get('url', ''),
                                entry.get('title', ''),
                                entry.get('duration', ''),
                                entry.get('size', ''),
                                entry.get('type', ''),
                                entry.get('date', ''),
                                entry.get('thumb_path', ''),
                                entry.get('save_path', '')
                            ))
            
            bak_file = self.old_json_file + ".bak"
            if os.path.exists(bak_file):
                try:
                    os.remove(bak_file)
                except OSError:
                    pass
            os.rename(self.old_json_file, bak_file)
        except Exception as e:
            logger.error(f"Error migrating history JSON to SQLite: {e}")

    def load_history(self, limit=150):
        try:
            with closing(self._get_connection()) as conn:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM downloads ORDER BY id DESC LIMIT ?', (limit,))
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return []

    def add_to_history(self, title, duration, size, url, media_type, thumb_path="", save_path=""):
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            with closing(self._get_connection()) as conn:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO downloads 
                        (url, title, duration, size, type, date, thumb_path, save_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (url, title, duration, size, media_type, date_str, thumb_path, save_path))
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding to history: {e}")
            return None

    def _cleanup_orphan_thumb(self, cursor, thumb_path):
        if not thumb_path or not os.path.exists(thumb_path):
            return
        cursor.execute('SELECT COUNT(*) as cnt FROM downloads WHERE thumb_path = ?', (thumb_path,))
        row = cursor.fetchone()
        if not row or row['cnt'] == 0:
            try:
                os.remove(thumb_path)
            except OSError:
                pass

    def clear_history(self):
        try:
            with closing(self._get_connection()) as conn:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT DISTINCT thumb_path FROM downloads')
                    thumbs = [r['thumb_path'] for r in cursor.fetchall() if r['thumb_path']]
                    cursor.execute('DELETE FROM downloads')
                    cursor.execute('DELETE FROM sqlite_sequence WHERE name="downloads"')
                    for t_path in thumbs:
                        if os.path.exists(t_path):
                            try:
                                os.remove(t_path)
                            except OSError:
                                pass
            return True
        except Exception as e:
            logger.error(f"Error clearing history: {e}")
            return False

    def remove_entries(self, entries_to_remove, delete_files=False, is_active_cb=None):
        if not entries_to_remove:
            return False

        try:
            with closing(self._get_connection()) as conn:
                with conn:
                    cursor = conn.cursor()
                    
                    for item in entries_to_remove:
                        item_id = item.get('id') if isinstance(item, dict) else None
                        
                        if item_id is not None:
                            cursor.execute('SELECT save_path, thumb_path FROM downloads WHERE id = ?', (item_id,))
                            row = cursor.fetchone()
                            thumb_path = row['thumb_path'] if row else None
                            if delete_files and row:
                                save_path = row['save_path']
                                if save_path and os.path.exists(save_path) and os.path.isfile(save_path):
                                    if is_active_cb and is_active_cb(save_path):
                                        logger.warning(f"Skipping deletion of actively downloading file: {save_path}")
                                    else:
                                        try:
                                            os.remove(save_path)
                                        except OSError as e:
                                            logger.warning(f"Error deleting file {save_path}: {e}")
                            
                            cursor.execute('DELETE FROM downloads WHERE id = ?', (item_id,))
                            self._cleanup_orphan_thumb(cursor, thumb_path)
                        elif isinstance(item, dict):
                            url = item.get('url')
                            date_str = item.get('date')
                            media_type = item.get('type')
                            if url and date_str:
                                cursor.execute(
                                    'SELECT id, save_path, thumb_path FROM downloads WHERE url = ? AND date = ? AND type = ?',
                                    (url, date_str, media_type)
                                )
                                row = cursor.fetchone()
                                if not row:
                                    cursor.execute(
                                        'SELECT id, save_path, thumb_path FROM downloads WHERE url = ? AND date = ?',
                                        (url, date_str)
                                    )
                                    row = cursor.fetchone()
                                if row:
                                    thumb_path = row['thumb_path']
                                    if delete_files:
                                        save_path = row['save_path']
                                        if save_path and os.path.exists(save_path) and os.path.isfile(save_path):
                                            if is_active_cb and is_active_cb(save_path):
                                                logger.warning(f"Skipping deletion of actively downloading file: {save_path}")
                                            else:
                                                try:
                                                    os.remove(save_path)
                                                except OSError as e:
                                                    logger.warning(f"Error deleting file {save_path}: {e}")
                                    cursor.execute('DELETE FROM downloads WHERE id = ?', (row['id'],))
                                    self._cleanup_orphan_thumb(cursor, thumb_path)
            return True
        except Exception as e:
            logger.error(f"Error removing entries: {e}")
            return False