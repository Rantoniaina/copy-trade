"""
MT5 Instance Manager - Automatically manages multiple MT5 installations for copy trading.
Detects existing instances and creates new ones as needed.
"""
import os
import shutil
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .mt5_instance_database import get_permanent_database, get_session_database

logger = logging.getLogger(__name__)


class MT5InstanceManager:
    """Manages multiple MT5 installations for copy trading."""
    
    def __init__(self, config_paths: Dict[str, str] = None):
        """
        Initialize the MT5 instance manager.
        
        Args:
            config_paths: Dictionary containing MetaTrader paths from configuration:
                - 'original_path': Original MT5 installation directory
                - 'master_path': Master account instance directory
                - 'slaves_base_path': Base directory for slave instances
                - 'slave_account{N}_path': Individual slave paths (optional)
        """
        self.base_mt5_path = None
        self.config_paths = config_paths or {}
        self.instances = {}  # role -> path mapping
        self._discover_mt5_installation()
    
    def _discover_mt5_installation(self) -> None:
        """Discover the base MT5 installation path using config or auto-discovery."""
        # First, try to use the configured original path
        if self.config_paths.get('original_path'):
            configured_path = self.config_paths['original_path']
            logger.info(f"Using configured MT5 original path: {configured_path}")
            if self._is_valid_mt5_installation(configured_path):
                self.base_mt5_path = configured_path
                logger.info(f"Configured MT5 installation validated: {configured_path}")
                return
            else:
                logger.warning(f"Configured MT5 path is not valid, falling back to auto-discovery: {configured_path}")
        
        # Fallback to auto-discovery if no config path or config path is invalid
        logger.info("Auto-discovering MT5 installation...")
        common_paths = [
            r"C:\Program Files\MetaTrader 5",
            r"C:\Program Files (x86)\MetaTrader 5",
            r"C:\Users\{}\AppData\Roaming\MetaQuotes\Terminal".format(os.getenv('USERNAME')),
            r"C:\Users\{}\Desktop\MetaTrader 5".format(os.getenv('USERNAME')),
            # Check for existing custom installations
            r"C:\Program Files\MetaTrader5_Master",
            r"C:\Program Files\MetaTrader5_Slave"
        ]
        
        for path in common_paths:
            logger.debug(f"Checking MT5 path: {path}")
            if self._is_valid_mt5_installation(path):
                self.base_mt5_path = path
                logger.info(f"Found MT5 installation at: {path}")
                break
            else:
                logger.debug(f"Path not valid MT5 installation: {path}")
        
        if not self.base_mt5_path:
            logger.warning("No MT5 installation found automatically")
            # Try to find any MetaTrader directories
            for drive in ['C:', 'D:']:
                for root_dir in ['Program Files', 'Program Files (x86)']:
                    search_path = f"{drive}\\{root_dir}"
                    if os.path.exists(search_path):
                        for item in os.listdir(search_path):
                            if 'metatrader' in item.lower() and 'trader 5' in item.lower():
                                potential_path = os.path.join(search_path, item)
                                logger.debug(f"Found potential MT5 path: {potential_path}")
                                if self._is_valid_mt5_installation(potential_path):
                                    self.base_mt5_path = potential_path
                                    logger.info(f"Found MT5 installation at: {potential_path}")
                                    return
    
    def _is_valid_mt5_installation(self, path: str) -> bool:
        """Check if path contains a valid MT5 installation."""
        if not os.path.exists(path):
            logger.debug(f"Path does not exist: {path}")
            return False
        
        if not os.path.isdir(path):
            logger.debug(f"Path is not a directory: {path}")
            return False
        
        # Check for key MT5 files (try different variations)
        required_files = [
            ["terminal64.exe", "MetaEditor64.exe"],  # Standard 64-bit
            ["terminal64.exe", "MetaEditor.exe"],    # Mixed case
            ["terminal.exe", "MetaEditor.exe"],      # 32-bit fallback
        ]
        
        for file_set in required_files:
            all_found = True
            for file in file_set:
                file_path = os.path.join(path, file)
                if not os.path.exists(file_path):
                    logger.debug(f"Missing file: {file_path}")
                    all_found = False
                    break
                else:
                    logger.debug(f"Found file: {file_path}")
            
            if all_found:
                logger.debug(f"Valid MT5 installation confirmed at: {path}")
                return True
        
        logger.debug(f"No valid MT5 file set found in: {path}")
        return False
    
    def _scan_existing_instances(self) -> Dict[str, str]:
        """Scan for existing MT5 instances."""
        instances = {}
        
        if not self.base_mt5_path:
            return instances
        
        base_dir = os.path.dirname(self.base_mt5_path)
        
        # Look for existing instances
        patterns = {
            'master': ['MetaTrader5_Master', 'MetaTrader 5_Master', 'MT5_Master'],
            'slave': ['MetaTrader5_Slave', 'MetaTrader 5_Slave', 'MT5_Slave'],
            'slave1': ['MetaTrader5_Slave1', 'MetaTrader 5_Slave1', 'MT5_Slave1'],
            'slave2': ['MetaTrader5_Slave2', 'MetaTrader 5_Slave2', 'MT5_Slave2'],
        }
        
        for role, pattern_list in patterns.items():
            for pattern in pattern_list:
                potential_path = os.path.join(base_dir, pattern)
                if self._is_valid_mt5_installation(potential_path):
                    instances[role] = potential_path
                    logger.info(f"Found existing {role} MT5 instance: {potential_path}")
                    break
        
        return instances
    
    def ensure_instances(self, master_count: int = 1, slave_count: int = 1) -> Dict[str, str]:
        """
        Ensure the required MT5 instances exist, creating them if necessary.
        
        Args:
            master_count: Number of master instances needed
            slave_count: Number of slave instances needed
            
        Returns:
            Dictionary mapping roles to paths
        """
        logger.info(f"Ensuring MT5 instances: {master_count} master(s), {slave_count} slave(s)")
        
        if not self.base_mt5_path:
            raise RuntimeError("No base MT5 installation found. Please install MT5 first.")
        
        instances = {}
        permanent_db = get_permanent_database()
        session_db = get_session_database()
        
        # Handle master instances using configured paths
        for i in range(master_count):
            role = "master" if master_count == 1 else f"master{i+1}"
            
            # Check session database for existing assignment first
            existing_assignment = session_db.get_assignment(role)
            if existing_assignment and os.path.exists(existing_assignment['instance_path']):
                instances[role] = existing_assignment['instance_path']
                session_db.update_last_used(role)
                logger.info(f"Using existing {role} assignment from session: {existing_assignment['instance_path']}")
                continue
            
            # Use configured master path if available
            if self.config_paths.get('master_path'):
                master_path = self.config_paths['master_path']
                if self._ensure_directory_exists(master_path):
                    instances[role] = master_path
                    # Track in permanent database
                    permanent_db.add_clone(master_path, self.base_mt5_path, 
                                         description="Configured master path", 
                                         creation_method="config")
                    logger.info(f"Using configured {role} path: {master_path}")
                else:
                    logger.error(f"Failed to create configured {role} directory: {master_path}")
            else:
                # Fallback to old behavior if no config path
                existing = self._scan_existing_instances()
                if role in existing:
                    instances[role] = existing[role]
                    # Track in permanent database
                    permanent_db.add_clone(existing[role], self.base_mt5_path,
                                         description="Auto-discovered master instance", 
                                         creation_method="auto")
                    logger.info(f"Using existing {role} instance: {existing[role]}")
                else:
                    # Create new instance using old method
                    path = self._create_instance(role, "master")
                    if path:
                        instances[role] = path
                        # Track in permanent database
                        permanent_db.add_clone(path, self.base_mt5_path,
                                             description="Auto-created master instance", 
                                             creation_method="auto")
                        logger.info(f"Created new {role} instance: {path}")
                    else:
                        logger.error(f"Failed to create {role} instance")
        
        # Handle slave instances using configured paths
        for i in range(slave_count):
            role = "slave" if slave_count == 1 else f"slave{i+1}"
            account_num = i + 2  # Account2, Account3, etc. (Account1 is master)
            
            # Check session database for existing assignment first
            existing_assignment = session_db.get_assignment(role)
            if existing_assignment and os.path.exists(existing_assignment['instance_path']):
                instances[role] = existing_assignment['instance_path']
                session_db.update_last_used(role)
                logger.info(f"Using existing {role} assignment from session: {existing_assignment['instance_path']}")
                continue
            
            # Check for individual slave path first
            individual_slave_key = f"slave_account{account_num}_path"
            if self.config_paths.get(individual_slave_key):
                slave_path = self.config_paths[individual_slave_key]
                if self._ensure_directory_exists(slave_path):
                    instances[role] = slave_path
                    # Track in permanent database
                    permanent_db.add_clone(slave_path, self.base_mt5_path,
                                         description=f"Configured individual slave path for account {account_num}",
                                         creation_method="config")
                    logger.info(f"Using configured individual {role} path: {slave_path}")
                else:
                    logger.error(f"Failed to create configured {role} directory: {slave_path}")
                continue
            
            # Use base slaves path if available
            if self.config_paths.get('slaves_base_path'):
                slaves_base = self.config_paths['slaves_base_path']
                slave_path = os.path.join(slaves_base, f"Account{account_num}")
                if self._ensure_directory_exists(slave_path):
                    instances[role] = slave_path
                    # Track in permanent database
                    permanent_db.add_clone(slave_path, self.base_mt5_path,
                                         description=f"Configured base slave path for account {account_num}",
                                         creation_method="config")
                    logger.info(f"Using configured {role} path under base: {slave_path}")
                else:
                    logger.error(f"Failed to create {role} directory under base: {slave_path}")
            else:
                # Fallback to old behavior if no config path
                existing = self._scan_existing_instances()
                if role in existing:
                    instances[role] = existing[role]
                    # Track in permanent database
                    permanent_db.add_clone(existing[role], self.base_mt5_path,
                                         description="Auto-discovered slave instance",
                                         creation_method="auto")
                    logger.info(f"Using existing {role} instance: {existing[role]}")
                else:
                    # Create new instance using old method
                    path = self._create_instance(role, "slave")
                    if path:
                        instances[role] = path
                        # Track in permanent database
                        permanent_db.add_clone(path, self.base_mt5_path,
                                             description="Auto-created slave instance",
                                             creation_method="auto")
                        logger.info(f"Created new {role} instance: {path}")
                    else:
                        logger.error(f"Failed to create {role} instance")
        
        self.instances = instances
        
        # Log database statistics
        perm_stats = permanent_db.get_stats()
        session_assignments = session_db.get_all_assignments()
        logger.info(f"Permanent DB: {perm_stats.get('valid_clones', 0)} valid clones tracked")
        logger.info(f"Session DB: {len(session_assignments)} current assignments")
        
        return instances
    
    def _create_instance(self, role: str, role_type: str) -> Optional[str]:
        """
        Create a new MT5 instance using separate data directories.
        
        Args:
            role: Specific role name (e.g., "master", "slave1")
            role_type: General role type ("master" or "slave")
            
        Returns:
            Path to created instance or None if failed
        """
        if not self.base_mt5_path:
            logger.error("No base MT5 installation to copy from")
            return None
        
        # For now, let's just return the base path and use separate data directories
        # This is a simpler approach that avoids copying entire installations
        
        # Create a unique data directory for this instance
        base_dir = os.path.dirname(self.base_mt5_path)
        data_dir_name = f"MT5_Data_{role.title()}"
        data_dir_path = os.path.join(base_dir, data_dir_name)
        
        try:
            # Create data directory if it doesn't exist
            if not os.path.exists(data_dir_path):
                os.makedirs(data_dir_path, exist_ok=True)
                logger.info(f"Created MT5 data directory: {data_dir_path}")
            
            # For simplicity, return the base MT5 path but with a special marker
            # indicating which data directory to use
            return f"{self.base_mt5_path}|{data_dir_path}"
            
        except Exception as e:
            logger.error(f"❌ Failed to create {role} MT5 data directory: {e}")
            return None
    
    def _ensure_directory_exists(self, path: str) -> bool:
        """
        Ensure that a directory exists, creating it if necessary.
        
        Args:
            path: Directory path to ensure exists
            
        Returns:
            True if directory exists or was created successfully, False otherwise
        """
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                logger.info(f"Created directory: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False
    
    def get_instance_path(self, role: str) -> Optional[str]:
        """Get the path for a specific role."""
        return self.instances.get(role)
    
    def get_master_path(self) -> Optional[str]:
        """Get the master instance path."""
        return self.instances.get("master") or self.instances.get("master1")
    
    def get_slave_path(self, index: int = 1) -> Optional[str]:
        """Get a slave instance path by index."""
        if index == 1:
            return self.instances.get("slave") or self.instances.get("slave1")
        else:
            return self.instances.get(f"slave{index}")
    
    def list_instances(self) -> Dict[str, str]:
        """List all managed instances."""
        return self.instances.copy()
    
    def cleanup_unused_instances(self, keep_roles: List[str]) -> None:
        """Clean up MT5 instances that are no longer needed."""
        base_dir = os.path.dirname(self.base_mt5_path) if self.base_mt5_path else None
        if not base_dir:
            return
        
        # Find all MT5-like directories
        mt5_dirs = []
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if (os.path.isdir(item_path) and 
                ("MetaTrader" in item or "MT5" in item) and 
                item != os.path.basename(self.base_mt5_path) and
                self._is_valid_mt5_installation(item_path)):
                mt5_dirs.append(item_path)
        
        # Remove instances not in keep_roles
        for dir_path in mt5_dirs:
            dir_name = os.path.basename(dir_path)
            should_keep = False
            
            for role in keep_roles:
                if role.lower() in dir_name.lower():
                    should_keep = True
                    break
            
            if not should_keep:
                try:
                    logger.info(f"Cleaning up unused MT5 instance: {dir_path}")
                    shutil.rmtree(dir_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up {dir_path}: {e}")

    def get_database_stats(self) -> Dict:
        """Get database statistics."""
        db = get_permanent_database()
        return db.get_database_stats()
    
    def cleanup_missing_instances(self) -> int:
        """Clean up instances from database that no longer exist on disk."""
        db = get_permanent_database()
        return db.cleanup_missing_instances()
    
    def get_tracked_instances(self, active_only: bool = True) -> List[Dict]:
        """Get all tracked instances from the database."""
        db = get_permanent_database()
        return db.get_all_instances(active_only)
    
    def deactivate_instance(self, instance_path: str) -> bool:
        """Mark an instance as inactive in the database."""
        db = get_permanent_database()
        return db.deactivate_instance(instance_path)

    def assign_account_to_instance(self, role: str, account_number: int, broker: str = None) -> bool:
        """
        Assign an account to an instance in the session database.
        
        Args:
            role: Role (master, slave, etc.)
            account_number: Account number
            broker: Broker name
            
        Returns:
            True if assigned successfully, False otherwise
        """
        if role not in self.instances:
            logger.error(f"No instance found for role: {role}")
            return False
        
        session_db = get_session_database()
        instance_path = self.instances[role]
        
        return session_db.assign_account_to_path(role, account_number, instance_path, broker)


# Global instance manager
_instance_manager = None


def get_mt5_instance_manager(config_paths: Dict[str, str] = None) -> MT5InstanceManager:
    """
    Get the global MT5 instance manager.
    
    Args:
        config_paths: Configuration paths for MetaTrader instances
        
    Returns:
        MT5InstanceManager instance
    """
    global _instance_manager
    if _instance_manager is None:
        _instance_manager = MT5InstanceManager(config_paths)
    return _instance_manager


def auto_setup_mt5_instances(master_count: int = 1, slave_count: int = 1, config_paths: Dict[str, str] = None) -> Dict[str, str]:
    """
    Automatically set up MT5 instances for copy trading.
    
    Args:
        master_count: Number of master accounts
        slave_count: Number of slave accounts
        config_paths: Configuration paths for MetaTrader instances
        
    Returns:
        Dictionary mapping roles to MT5 paths
    """
    manager = get_mt5_instance_manager(config_paths)
    return manager.ensure_instances(master_count, slave_count)


def get_mt5_path_for_role(role: str, account_index: int = 1, config_paths: Dict[str, str] = None) -> Optional[str]:
    """
    Get MT5 path for a specific role.
    
    Args:
        role: "master" or "slave"
        account_index: Index for multiple accounts of same role
        config_paths: Configuration paths for MetaTrader instances
        
    Returns:
        Path to MT5 installation or None
    """
    manager = get_mt5_instance_manager(config_paths)
    
    if role.lower() == "master":
        if account_index == 1:
            return manager.get_master_path()
        else:
            return manager.get_instance_path(f"master{account_index}")
    elif role.lower() == "slave":
        return manager.get_slave_path(account_index)
    
    return None 