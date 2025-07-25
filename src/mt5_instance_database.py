"""
MT5 Instance Database - Tracks all MT5 clone instances created by the copy trading system.
Uses SQLite to store instance information persistently.
"""
import sqlite3
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class MT5InstanceDatabase:
    """Database to track MT5 clone instances."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the MT5 instance database.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses default path.
        """
        if db_path is None:
            # Store database in project root, will be added to .gitignore
            project_root = Path(__file__).parent.parent
            db_path = project_root / "mt5_instances.db"
        
        self.db_path = str(db_path)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize the database and create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create instances table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mt5_instances (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role TEXT NOT NULL,
                        account_number INTEGER,
                        instance_path TEXT NOT NULL UNIQUE,
                        data_path TEXT,
                        created_at TEXT NOT NULL,
                        last_used TEXT NOT NULL,
                        is_active BOOLEAN DEFAULT 1,
                        broker TEXT,
                        description TEXT
                    )
                ''')
                
                # Create index for faster lookups
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_role ON mt5_instances(role)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_account ON mt5_instances(account_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_path ON mt5_instances(instance_path)')
                
                conn.commit()
                logger.debug(f"Initialized MT5 instance database: {self.db_path}")
                
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def add_instance(self, 
                    role: str, 
                    instance_path: str, 
                    account_number: int = None,
                    data_path: str = None,
                    broker: str = None,
                    description: str = None) -> bool:
        """
        Add a new MT5 instance to the database.
        
        Args:
            role: Role of the instance (master, slave, slave1, etc.)
            instance_path: Path to the MT5 instance
            account_number: Account number associated with this instance
            data_path: Path to the data directory (if different from instance_path)
            broker: Broker name
            description: Optional description
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO mt5_instances 
                    (role, account_number, instance_path, data_path, created_at, last_used, 
                     is_active, broker, description)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                ''', (role, account_number, instance_path, data_path, current_time, 
                      current_time, broker, description))
                
                conn.commit()
                logger.info(f"Added MT5 instance to database: {role} -> {instance_path}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Failed to add instance to database: {e}")
            return False
    
    def get_instance(self, role: str) -> Optional[Dict]:
        """
        Get an MT5 instance by role.
        
        Args:
            role: Role to search for
            
        Returns:
            Dictionary with instance information or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT role, account_number, instance_path, data_path, created_at, 
                           last_used, is_active, broker, description
                    FROM mt5_instances 
                    WHERE role = ? AND is_active = 1
                    ORDER BY last_used DESC
                    LIMIT 1
                ''', (role,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'role': row[0],
                        'account_number': row[1],
                        'instance_path': row[2],
                        'data_path': row[3],
                        'created_at': row[4],
                        'last_used': row[5],
                        'is_active': bool(row[6]),
                        'broker': row[7],
                        'description': row[8]
                    }
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get instance from database: {e}")
            return None
    
    def get_all_instances(self, active_only: bool = True) -> List[Dict]:
        """
        Get all MT5 instances from the database.
        
        Args:
            active_only: If True, only return active instances
            
        Returns:
            List of dictionaries with instance information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT role, account_number, instance_path, data_path, created_at, 
                           last_used, is_active, broker, description
                    FROM mt5_instances
                '''
                params = []
                
                if active_only:
                    query += ' WHERE is_active = 1'
                
                query += ' ORDER BY created_at DESC'
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                instances = []
                for row in rows:
                    instances.append({
                        'role': row[0],
                        'account_number': row[1],
                        'instance_path': row[2],
                        'data_path': row[3],
                        'created_at': row[4],
                        'last_used': row[5],
                        'is_active': bool(row[6]),
                        'broker': row[7],
                        'description': row[8]
                    })
                
                return instances
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get instances from database: {e}")
            return []
    
    def update_last_used(self, instance_path: str) -> bool:
        """
        Update the last used timestamp for an instance.
        
        Args:
            instance_path: Path to the instance
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                cursor.execute('''
                    UPDATE mt5_instances 
                    SET last_used = ? 
                    WHERE instance_path = ?
                ''', (current_time, instance_path))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Failed to update last used time: {e}")
            return False
    
    def deactivate_instance(self, instance_path: str) -> bool:
        """
        Mark an instance as inactive (soft delete).
        
        Args:
            instance_path: Path to the instance
            
        Returns:
            True if deactivated successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE mt5_instances 
                    SET is_active = 0 
                    WHERE instance_path = ?
                ''', (instance_path,))
                
                conn.commit()
                logger.info(f"Deactivated MT5 instance: {instance_path}")
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Failed to deactivate instance: {e}")
            return False
    
    def remove_instance(self, instance_path: str) -> bool:
        """
        Completely remove an instance from the database.
        
        Args:
            instance_path: Path to the instance
            
        Returns:
            True if removed successfully, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM mt5_instances 
                    WHERE instance_path = ?
                ''', (instance_path,))
                
                conn.commit()
                logger.info(f"Removed MT5 instance from database: {instance_path}")
                return cursor.rowcount > 0
                
        except sqlite3.Error as e:
            logger.error(f"Failed to remove instance: {e}")
            return False
    
    def cleanup_missing_instances(self) -> int:
        """
        Remove instances from database where the path no longer exists.
        
        Returns:
            Number of instances removed
        """
        removed_count = 0
        
        try:
            instances = self.get_all_instances(active_only=False)
            
            for instance in instances:
                instance_path = instance['instance_path']
                if not os.path.exists(instance_path):
                    if self.remove_instance(instance_path):
                        removed_count += 1
                        logger.info(f"Cleaned up missing instance: {instance_path}")
            
            logger.info(f"Cleanup completed: removed {removed_count} missing instances")
            
        except Exception as e:
            logger.error(f"Failed to cleanup missing instances: {e}")
        
        return removed_count
    
    def get_instance_by_account(self, account_number: int) -> Optional[Dict]:
        """
        Get an MT5 instance by account number.
        
        Args:
            account_number: Account number to search for
            
        Returns:
            Dictionary with instance information or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT role, account_number, instance_path, data_path, created_at, 
                           last_used, is_active, broker, description
                    FROM mt5_instances 
                    WHERE account_number = ? AND is_active = 1
                    ORDER BY last_used DESC
                    LIMIT 1
                ''', (account_number,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'role': row[0],
                        'account_number': row[1],
                        'instance_path': row[2],
                        'data_path': row[3],
                        'created_at': row[4],
                        'last_used': row[5],
                        'is_active': bool(row[6]),
                        'broker': row[7],
                        'description': row[8]
                    }
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get instance by account: {e}")
            return None
    
    def get_database_stats(self) -> Dict:
        """
        Get statistics about the database.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total instances
                cursor.execute('SELECT COUNT(*) FROM mt5_instances')
                total_instances = cursor.fetchone()[0]
                
                # Active instances
                cursor.execute('SELECT COUNT(*) FROM mt5_instances WHERE is_active = 1')
                active_instances = cursor.fetchone()[0]
                
                # Instances by role
                cursor.execute('''
                    SELECT role, COUNT(*) 
                    FROM mt5_instances 
                    WHERE is_active = 1 
                    GROUP BY role
                ''')
                role_counts = dict(cursor.fetchall())
                
                return {
                    'total_instances': total_instances,
                    'active_instances': active_instances,
                    'inactive_instances': total_instances - active_instances,
                    'role_counts': role_counts,
                    'database_path': self.db_path
                }
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}


# Global database instance
_database = None


def get_mt5_database() -> MT5InstanceDatabase:
    """Get the global MT5 instance database."""
    global _database
    if _database is None:
        _database = MT5InstanceDatabase()
    return _database 