"""
MT5 Instance Database - Tracks MT5 clone instances with two separate databases:
1. Permanent database: Stores all created MT5 clone paths (never deleted)
2. Session database: Stores current account-path pairings (purged on startup)
"""
import sqlite3
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class MT5PermanentDatabase:
    """Permanent database to track all MT5 clone paths ever created."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the permanent MT5 clone database.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses default path.
        """
        if db_path is None:
            # Store database in project root, will be added to .gitignore
            project_root = Path(__file__).parent.parent
            db_path = project_root / "mt5_clones_permanent.db"
        
        self.db_path = str(db_path)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create clones table - stores all MT5 clone paths ever created
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mt5_clones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        clone_path TEXT NOT NULL UNIQUE,
                        original_path TEXT,
                        created_at TEXT NOT NULL,
                        last_verified TEXT,
                        is_valid BOOLEAN DEFAULT 1,
                        description TEXT,
                        creation_method TEXT
                    )
                ''')
                
                # Create index for faster lookups
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_clone_path ON mt5_clones(clone_path)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_valid ON mt5_clones(is_valid)')
                
                conn.commit()
                logger.debug(f"Initialized permanent MT5 clones database: {self.db_path}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize permanent database: {e}")
            raise
    
    def add_clone(self, 
                  clone_path: str, 
                  original_path: str = None,
                  description: str = None,
                  creation_method: str = None) -> bool:
        """
        Add a new MT5 clone path to the permanent database.
        
        Args:
            clone_path: Path to the MT5 clone
            original_path: Path to the original MT5 installation
            description: Optional description
            creation_method: How the clone was created (config, auto, manual)
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO mt5_clones 
                    (clone_path, original_path, created_at, last_verified, is_valid, description, creation_method)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                ''', (clone_path, original_path, current_time, current_time, description, creation_method))
                
                conn.commit()
                logger.info(f"Added MT5 clone to permanent database: {clone_path}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to add clone to permanent database: {e}")
            return False
    
    def get_all_clones(self, valid_only: bool = True) -> List[Dict]:
        """
        Get all MT5 clone paths from the permanent database.
        
        Args:
            valid_only: If True, only return valid clones
            
        Returns:
            List of dictionaries with clone information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT clone_path, original_path, created_at, last_verified, 
                           is_valid, description, creation_method
                    FROM mt5_clones
                '''
                params = []
                
                if valid_only:
                    query += ' WHERE is_valid = 1'
                
                query += ' ORDER BY created_at DESC'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                clones = []
                for row in rows:
                    clones.append({
                        'clone_path': row[0],
                        'original_path': row[1],
                        'created_at': row[2],
                        'last_verified': row[3],
                        'is_valid': bool(row[4]),
                        'description': row[5],
                        'creation_method': row[6]
                    })
                
                return clones
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get clones from permanent database: {e}")
            return []
    
    def verify_clone_exists(self, clone_path: str) -> bool:
        """
        Verify that a clone path still exists on disk and update database.
        
        Args:
            clone_path: Path to verify
            
        Returns:
            True if clone exists, False otherwise
        """
        exists = os.path.exists(clone_path)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                cursor.execute('''
                    UPDATE mt5_clones 
                    SET last_verified = ?, is_valid = ? 
                    WHERE clone_path = ?
                ''', (current_time, exists, clone_path))
                
                conn.commit()
                
        except sqlite3.Error as e:
            logger.error(f"Failed to update clone verification: {e}")
        
        return exists
    
    def get_stats(self) -> Dict:
        """Get statistics about the permanent database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM mt5_clones')
                total_clones = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM mt5_clones WHERE is_valid = 1')
                valid_clones = cursor.fetchone()[0]
                
                return {
                    'total_clones': total_clones,
                    'valid_clones': valid_clones,
                    'invalid_clones': total_clones - valid_clones,
                    'database_path': self.db_path
                }
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get permanent database stats: {e}")
            return {}


class MT5SessionDatabase:
    """Session database to track current account-path pairings (purged on startup)."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the session MT5 database.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses default path.
        """
        if db_path is None:
            # Store database in project root, will be added to .gitignore
            project_root = Path(__file__).parent.parent
            db_path = project_root / "mt5_session.db"
        
        self.db_path = str(db_path)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create session table - current account-path pairings
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mt5_session (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT NOT NULL,
                        account_number INTEGER,
                        instance_path TEXT NOT NULL,
                        broker TEXT,
                        assigned_at TEXT NOT NULL,
                        last_used TEXT NOT NULL
                    )
                ''')
                
                # Create indexes
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_role ON mt5_session(role)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_account ON mt5_session(account_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_path ON mt5_session(instance_path)')
                
                conn.commit()
                logger.debug(f"Initialized session MT5 database: {self.db_path}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize session database: {e}")
            raise
    
    def purge_all(self) -> int:
        """
        Purge all session data (called on app startup).
        
        Returns:
            Number of records purged
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT COUNT(*) FROM mt5_session')
                count_before = cursor.fetchone()[0]
                
                cursor.execute('DELETE FROM mt5_session')
                conn.commit()
                
                logger.info(f"Purged {count_before} session records on startup")
                return count_before
                
        except sqlite3.Error as e:
            logger.error(f"Failed to purge session database: {e}")
            return 0
    
    def assign_account_to_path(self, 
                              role: str, 
                              account_number: int, 
                              instance_path: str,
                              broker: str = None) -> bool:
        """
        Assign an account to a specific MT5 instance path.
        
        Args:
            role: Role (master, slave, slave1, etc.)
            account_number: Account number
            instance_path: Path to MT5 instance
            broker: Broker name
            
        Returns:
            True if assigned successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                
                # Remove any existing assignment for this role/account
                cursor.execute('DELETE FROM mt5_session WHERE role = ? OR account_number = ?', 
                             (role, account_number))
                
                # Add new assignment
                cursor.execute('''
                    INSERT INTO mt5_session 
                    (role, account_number, instance_path, broker, assigned_at, last_used)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (role, account_number, instance_path, broker, current_time, current_time))
                
                conn.commit()
                logger.info(f"Assigned account {account_number} ({role}) to path: {instance_path}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to assign account to path: {e}")
            return False
    
    def get_assignment(self, role: str) -> Optional[Dict]:
        """
        Get the current assignment for a role.
        
        Args:
            role: Role to search for
            
        Returns:
            Dictionary with assignment information or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT role, account_number, instance_path, broker, assigned_at, last_used
                    FROM mt5_session 
                    WHERE role = ?
                    LIMIT 1
                ''', (role,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'role': row[0],
                        'account_number': row[1],
                        'instance_path': row[2],
                        'broker': row[3],
                        'assigned_at': row[4],
                        'last_used': row[5]
                    }
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get assignment from session database: {e}")
            return None
    
    def get_all_assignments(self) -> List[Dict]:
        """Get all current assignments."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT role, account_number, instance_path, broker, assigned_at, last_used
                    FROM mt5_session 
                    ORDER BY assigned_at DESC
                ''')
                
                rows = cursor.fetchall()
                assignments = []
                for row in rows:
                    assignments.append({
                        'role': row[0],
                        'account_number': row[1],
                        'instance_path': row[2],
                        'broker': row[3],
                        'assigned_at': row[4],
                        'last_used': row[5]
                    })
                
                return assignments
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get assignments from session database: {e}")
            return []
    
    def update_last_used(self, role: str) -> bool:
        """Update the last used timestamp for a role."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                cursor.execute('''
                    UPDATE mt5_session 
                    SET last_used = ? 
                    WHERE role = ?
                ''', (current_time, role))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Failed to update last used time: {e}")
            return False


# Global database instances
_permanent_db = None
_session_db = None


def get_permanent_database() -> MT5PermanentDatabase:
    """Get the global permanent MT5 database."""
    global _permanent_db
    if _permanent_db is None:
        _permanent_db = MT5PermanentDatabase()
    return _permanent_db


def get_session_database() -> MT5SessionDatabase:
    """Get the global session MT5 database."""
    global _session_db
    if _session_db is None:
        _session_db = MT5SessionDatabase()
    return _session_db


# Backward compatibility - keep the old interface
def get_mt5_database():
    """Backward compatibility - returns session database."""
    return get_session_database() 