"""
Sistem de bază de date pentru tracking-ul cazărilor și istoricul căutărilor
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
from scraper import Accommodation
from config import SearchCriteria

@dataclass
class SearchRecord:
    """Înregistrare pentru o căutare efectuată"""
    id: Optional[int] = None
    timestamp: datetime = None
    criteria_hash: str = ""
    results_count: int = 0
    criteria_json: str = ""
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class AccommodationDatabase:
    """Clasa pentru gestionarea bazei de date"""
    
    def __init__(self, db_path: str = "accommodation_agent.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inițializează baza de date cu tabelele necesare"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS accommodations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT NOT NULL,
                    rating REAL DEFAULT 0,
                    location TEXT NOT NULL,
                    url TEXT,
                    image_url TEXT,
                    description TEXT,
                    amenities TEXT,  -- JSON string
                    platform TEXT NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    times_seen INTEGER DEFAULT 1,
                    accommodation_hash TEXT UNIQUE NOT NULL,
                    is_notified BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criteria_hash TEXT NOT NULL,
                    results_count INTEGER DEFAULT 0,
                    criteria_json TEXT NOT NULL,
                    execution_time_ms INTEGER DEFAULT 0
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    accommodation_id INTEGER,
                    price REAL NOT NULL,
                    currency TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (accommodation_id) REFERENCES accommodations (id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    accommodation_ids TEXT NOT NULL,  -- JSON array
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notification_type TEXT NOT NULL,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT
                )
            ''')
            
            # Indexuri pentru performanță
            conn.execute('CREATE INDEX IF NOT EXISTS idx_acc_hash ON accommodations(accommodation_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_search_hash ON searches(criteria_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_price_hist ON price_history(accommodation_id, timestamp)')
            
            conn.commit()
    
    def _create_accommodation_hash(self, accommodation: Accommodation) -> str:
        """Creează un hash unic pentru cazare"""
        unique_string = f"{accommodation.title.lower().strip()}_{accommodation.location.lower().strip()}_{accommodation.platform}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def _create_criteria_hash(self, criteria: SearchCriteria) -> str:
        """Creează un hash pentru criteriile de căutare"""
        criteria_dict = asdict(criteria)
        # Exclude datele pentru hash (sunt specifice fiecărei căutări)
        criteria_dict.pop('check_in', None)
        criteria_dict.pop('check_out', None)
        criteria_str = json.dumps(criteria_dict, sort_keys=True)
        return hashlib.md5(criteria_str.encode()).hexdigest()
    
    def save_accommodation(self, accommodation: Accommodation) -> int:
        """Salvează o cazare în baza de date"""
        acc_hash = self._create_accommodation_hash(accommodation)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Verifică dacă cazarea există deja
            existing = conn.execute(
                "SELECT id, price, currency FROM accommodations WHERE accommodation_hash = ?",
                (acc_hash,)
            ).fetchone()
            
            if existing:
                # Actualizează cazarea existentă
                accommodation_id = existing['id']
                
                # Salvează istoricul prețului dacă s-a schimbat
                if existing['price'] != accommodation.price or existing['currency'] != accommodation.currency:
                    self.save_price_history(accommodation_id, accommodation.price, accommodation.currency)
                
                conn.execute('''
                    UPDATE accommodations 
                    SET last_seen = CURRENT_TIMESTAMP, 
                        times_seen = times_seen + 1,
                        price = ?, currency = ?, rating = ?
                    WHERE id = ?
                ''', (accommodation.price, accommodation.currency, accommodation.rating, accommodation_id))
                
                return accommodation_id
            else:
                # Inserează cazare nouă
                cursor = conn.execute('''
                    INSERT INTO accommodations 
                    (title, price, currency, rating, location, url, image_url, 
                     description, amenities, platform, accommodation_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    accommodation.title, accommodation.price, accommodation.currency,
                    accommodation.rating, accommodation.location, accommodation.url,
                    accommodation.image_url, accommodation.description,
                    json.dumps(accommodation.amenities), accommodation.platform, acc_hash
                ))
                
                accommodation_id = cursor.lastrowid
                
                # Salvează primul preț în istoric
                self.save_price_history(accommodation_id, accommodation.price, accommodation.currency)
                
                return accommodation_id
    
    def save_price_history(self, accommodation_id: int, price: float, currency: str):
        """Salvează istoricul prețurilor"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO price_history (accommodation_id, price, currency) VALUES (?, ?, ?)",
                (accommodation_id, price, currency)
            )
    
    def save_search_record(self, criteria: SearchCriteria, results_count: int, 
                          execution_time_ms: int = 0) -> int:
        """Salvează o înregistrare de căutare"""
        criteria_hash = self._create_criteria_hash(criteria)
        criteria_json = json.dumps(asdict(criteria), default=str)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO searches (criteria_hash, results_count, criteria_json, execution_time_ms)
                VALUES (?, ?, ?, ?)
            ''', (criteria_hash, results_count, criteria_json, execution_time_ms))
            
            return cursor.lastrowid
    
    def get_new_accommodations(self, hours_back: int = 24) -> List[Accommodation]:
        """Returnează cazările noi din ultimele X ore"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('''
                SELECT * FROM accommodations 
                WHERE first_seen >= ? AND is_notified = FALSE
                ORDER BY first_seen DESC
            ''', (cutoff_time,)).fetchall()
            
            return [self._row_to_accommodation(row) for row in rows]
    
    def get_price_drops(self, percentage_threshold: float = 10.0) -> List[Dict[str, Any]]:
        """Găsește cazările cu scăderi semnificative de preț"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Query complex pentru a găsi scăderile de preț
            rows = conn.execute('''
                WITH price_changes AS (
                    SELECT 
                        a.id,
                        a.title,
                        a.location,
                        a.platform,
                        ph1.price as current_price,
                        ph1.currency,
                        ph2.price as previous_price,
                        ph1.timestamp as current_time,
                        ph2.timestamp as previous_time,
                        ((ph2.price - ph1.price) / ph2.price * 100) as price_drop_percentage
                    FROM accommodations a
                    JOIN price_history ph1 ON a.id = ph1.accommodation_id
                    JOIN price_history ph2 ON a.id = ph2.accommodation_id
                    WHERE ph1.timestamp > ph2.timestamp
                    AND ph1.timestamp >= datetime('now', '-7 days')
                    AND ph2.timestamp >= datetime('now', '-14 days')
                )
                SELECT * FROM price_changes 
                WHERE price_drop_percentage >= ?
                ORDER BY price_drop_percentage DESC
            ''', (percentage_threshold,)).fetchall()
            
            return [dict(row) for row in rows]
    
    def mark_as_notified(self, accommodation_ids: List[int]):
        """Marchează cazările ca fiind notificate"""
        if not accommodation_ids:
            return
        
        placeholders = ','.join(['?' for _ in accommodation_ids])
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f'''
                UPDATE accommodations 
                SET is_notified = TRUE 
                WHERE id IN ({placeholders})
            ''', accommodation_ids)
    
    def save_notification_record(self, accommodation_ids: List[int], 
                               notification_type: str, success: bool, 
                               error_message: str = None):
        """Salvează o înregistrare de notificare"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO notifications 
                (accommodation_ids, notification_type, success, error_message)
                VALUES (?, ?, ?, ?)
            ''', (json.dumps(accommodation_ids), notification_type, success, error_message))
    
    def get_search_statistics(self, days_back: int = 7) -> Dict[str, Any]:
        """Returnează statistici despre căutările efectuate"""
        cutoff_time = datetime.now() - timedelta(days=days_back)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            stats = {}
            
            # Total căutări
            result = conn.execute(
                "SELECT COUNT(*) as total FROM searches WHERE timestamp >= ?",
                (cutoff_time,)
            ).fetchone()
            stats['total_searches'] = result['total']
            
            # Média rezultatelor
            result = conn.execute(
                "SELECT AVG(results_count) as avg FROM searches WHERE timestamp >= ?",
                (cutoff_time,)
            ).fetchone()
            stats['avg_results'] = result['avg'] or 0
            
            # Căutări pe platformă
            platform_stats = conn.execute('''
                SELECT a.platform, COUNT(*) as count
                FROM accommodations a
                WHERE a.first_seen >= ?
                GROUP BY a.platform
                ORDER BY count DESC
            ''', (cutoff_time,)).fetchall()
            stats['platform_breakdown'] = {row['platform']: row['count'] for row in platform_stats}
            
            return stats
    
    def _row_to_accommodation(self, row: sqlite3.Row) -> Accommodation:
        """Convertește un rând din baza de date în obiect Accommodation"""
        amenities = json.loads(row['amenities']) if row['amenities'] else []
        
        return Accommodation(
            title=row['title'],
            price=row['price'],
            currency=row['currency'],
            rating=row['rating'],
            location=row['location'],
            url=row['url'],
            image_url=row['image_url'],
            description=row['description'],
            amenities=amenities,
            platform=row['platform']
        )
    
    def clean_old_data(self, days_to_keep: int = 30):
        """Curăță datele vechi din baza de date"""
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        
        with sqlite3.connect(self.db_path) as conn:
            # Șterge căutările vechi
            conn.execute("DELETE FROM searches WHERE timestamp < ?", (cutoff_time,))
            
            # Șterge istoricul vechi de prețuri
            conn.execute("DELETE FROM price_history WHERE timestamp < ?", (cutoff_time,))
            
            # Șterge notificările vechi
            conn.execute("DELETE FROM notifications WHERE timestamp < ?", (cutoff_time,))
            
            conn.commit()
    
    def get_accommodation_by_id(self, accommodation_id: int) -> Optional[Accommodation]:
        """Returnează o cazare după ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM accommodations WHERE id = ?",
                (accommodation_id,)
            ).fetchone()
            
            return self._row_to_accommodation(row) if row else None

# Funcții utilitare
def backup_database(db_path: str, backup_path: str = None):
    """Creează o copie de rezervă a bazei de date"""
    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"accommodation_agent_backup_{timestamp}.db"
    
    import shutil
    shutil.copy2(db_path, backup_path)
    return backup_path

def restore_database(backup_path: str, db_path: str):
    """Restaurează baza de date din backup"""
    import shutil
    shutil.copy2(backup_path, db_path)