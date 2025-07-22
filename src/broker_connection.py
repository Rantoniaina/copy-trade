"""
Module for connecting to trading accounts via MetaTrader 5.
"""
import time
import logging
from typing import Dict, Optional, Tuple, Union, List, Literal
from enum import Enum

try:
    import MetaTrader5 as mt5
except ImportError:
    raise ImportError(
        "MetaTrader5 package is not installed. Please install it with: pip install MetaTrader5"
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AccountRole(Enum):
    """Enum for account roles in copy trading."""
    MASTER = "master"
    SLAVE = "slave"


class BrokerConnection:
    """
    Class to manage connections to trading accounts via MetaTrader 5.
    """
    
    def __init__(self, connection_id: str = "default", role: AccountRole = AccountRole.SLAVE, mt5_path: str = None):
        """Initialize the BrokerConnection instance."""
        self.connection_id = connection_id
        self.role = role
        self.mt5_path = mt5_path  # Path to specific MT5 installation
        self.connected = False
        self.account_info = None
        self.broker = None
        self.broker_server = None
        self.account_number = None
        # Note: We'll initialize MT5 when connecting, not in constructor
        
    def __del__(self):
        """Clean up resources when object is destroyed."""
        self.disconnect()
    
    def connect(self, 
                broker: str, 
                broker_server: str, 
                platform: str, 
                account_number: int, 
                password: str) -> bool:
        """
        Connect to a trading account.
        
        Args:
            broker: Broker name (e.g., "FundedNext")
            broker_server: Broker server name (e.g., "FundedNext-Server 2")
            platform: Trading platform (currently only "mt5" is supported)
            account_number: Trading account number
            password: Trading account password
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        if platform.lower() != "mt5":
            logger.error(f"[{self.connection_id}] Unsupported platform: {platform}. Only MT5 is currently supported.")
            return False
        
        # Disconnect from any existing connection
        self.disconnect()
        
        # Use the server name directly from config
        server = broker_server.strip()
        
        # Initialize MT5 with specific path if provided
        logger.info(f"[{self.connection_id}] ({self.role.value}) Attempting to connect to {broker} ({server}) account {account_number}")
        
        # Initialize MT5 (with specific path if provided)
        if self.mt5_path:
            logger.info(f"[{self.connection_id}] Using MT5 installation at: {self.mt5_path}")
            if not mt5.initialize(path=self.mt5_path, login=account_number, password=password, server=server):
                error_code = mt5.last_error()
                logger.error(f"[{self.connection_id}] MT5 initialization with custom path failed. Error: {error_code}")
                
                # Fallback: try regular initialize then login
                logger.info(f"[{self.connection_id}] Trying fallback initialization method...")
                if not mt5.initialize(path=self.mt5_path):
                    error_code = mt5.last_error()
                    logger.error(f"[{self.connection_id}] MT5 initialization failed. Error: {error_code}")
                    return False
                
                # Now try to login
                if not mt5.login(account_number, password=password, server=server):
                    error_code = mt5.last_error()
                    logger.error(f"[{self.connection_id}] Login failed. Error: {error_code}")
                    mt5.shutdown()
                    return False
        else:
            # Use default MT5 installation
            if not mt5.initialize(login=account_number, password=password, server=server):
                error_code = mt5.last_error()
                logger.error(f"[{self.connection_id}] MT5 initialization with credentials failed. Error: {error_code}")
                
                # Fallback: try regular initialize then login
                logger.info(f"[{self.connection_id}] Trying fallback initialization method...")
                if not mt5.initialize():
                    error_code = mt5.last_error()
                    logger.error(f"[{self.connection_id}] MT5 initialization failed. Error: {error_code}")
                    return False
                
                # Now try to login
                if not mt5.login(account_number, password=password, server=server):
                    error_code = mt5.last_error()
                    logger.error(f"[{self.connection_id}] Login failed. Error: {error_code}")
                    mt5.shutdown()
                    return False
        
        # Store account information
        self.account_info = mt5.account_info()
        if not self.account_info:
            logger.error(f"[{self.connection_id}] Failed to get account info")
            mt5.shutdown()
            return False
        
        # Store connection details
        self.broker = broker
        self.broker_server = broker_server
        self.account_number = account_number
        self.connected = True
        logger.info(f"[{self.connection_id}] ({self.role.value}) Successfully connected to account {account_number}")
        return True
    
    def disconnect(self) -> None:
        """Disconnect from the current trading account."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            self.account_info = None
            self.broker = None
            self.broker_server = None
            self.account_number = None
            logger.info(f"[{self.connection_id}] ({self.role.value}) Disconnected from trading account")
    
    def is_connected(self) -> bool:
        """Check if currently connected to a trading account."""
        return self.connected
    
    def get_account_info(self) -> Optional[Dict]:
        """
        Get information about the connected account.
        
        Returns:
            Dict containing account information or None if not connected
        """
        if not self.connected or not self.account_info:
            logger.warning(f"[{self.connection_id}] Not connected to any account")
            return None
        
        # Use stored account info instead of refreshing since MT5 can only 
        # be connected to one account at a time per process
        account_dict = self.account_info._asdict()
        account_dict['role'] = self.role.value
        return account_dict
    
    def get_open_positions(self) -> List[Dict]:
        """
        Get all open positions for this account.
        
        Returns:
            List of dictionaries containing position information
        """
        if not self.connected:
            logger.warning(f"[{self.connection_id}] Not connected to any account")
            return []
        
        positions = mt5.positions_get()
        if positions is None:
            logger.error(f"[{self.connection_id}] Failed to get positions")
            return []
        
        return [pos._asdict() for pos in positions]
    
    def get_deals_history(self, date_from, date_to=None) -> List[Dict]:
        """
        Get deals history for this account.
        
        Args:
            date_from: Start date for history
            date_to: End date for history (default: current time)
            
        Returns:
            List of dictionaries containing deal information
        """
        if not self.connected:
            logger.warning(f"[{self.connection_id}] Not connected to any account")
            return []
        
        if date_to is None:
            import datetime
            date_to = datetime.datetime.now()
        
        deals = mt5.history_deals_get(date_from, date_to)
        if deals is None:
            logger.error(f"[{self.connection_id}] Failed to get deals history")
            return []
        
        return [deal._asdict() for deal in deals]


class MultiBrokerManager:
    """
    Manager class for handling multiple broker connections simultaneously with master/slave support.
    """
    
    def __init__(self):
        """Initialize the MultiBrokerManager."""
        self.connections: Dict[str, BrokerConnection] = {}
        self._lock = threading.RLock()
        self.master_account_id: Optional[str] = None
        self.slave_account_ids: List[str] = []
    
    def add_connection(self, 
                      connection_id: str,
                      broker: str,
                      broker_server: str,
                      platform: str,
                      account_number: int,
                      password: str,
                      role: AccountRole = AccountRole.SLAVE) -> bool:
        """
        Add and connect to a new broker account.
        
        Args:
            connection_id: Unique identifier for this connection
            broker: Broker name (e.g., "FundedNext")
            broker_server: Broker server name (e.g., "FundedNext-Server 2")
            platform: Trading platform (currently only "mt5" is supported)
            account_number: Trading account number
            password: Trading account password
            role: Account role (master or slave)
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        with self._lock:
            # Validate master/slave configuration
            if role == AccountRole.MASTER:
                if self.master_account_id is not None:
                    logger.error(f"Cannot add {connection_id} as master. Master account {self.master_account_id} already exists.")
                    return False
            
            # Check if connection already exists
            if connection_id in self.connections:
                logger.warning(f"Connection {connection_id} already exists. Disconnecting old connection.")
                self.remove_connection(connection_id)
            
            # Create new connection
            conn = BrokerConnection(connection_id, role)
            success = conn.connect(broker, broker_server, platform, account_number, password)
            
            if success:
                self.connections[connection_id] = conn
                
                # Update role tracking
                if role == AccountRole.MASTER:
                    self.master_account_id = connection_id
                    logger.info(f"Added MASTER connection {connection_id} successfully")
                else:
                    self.slave_account_ids.append(connection_id)
                    logger.info(f"Added SLAVE connection {connection_id} successfully")
                
                return True
            else:
                logger.error(f"Failed to add connection {connection_id}")
                return False
    
    def remove_connection(self, connection_id: str) -> bool:
        """
        Remove and disconnect a broker connection.
        
        Args:
            connection_id: Unique identifier for the connection to remove
            
        Returns:
            bool: True if connection was removed, False if not found
        """
        with self._lock:
            if connection_id in self.connections:
                conn = self.connections[connection_id]
                
                # Update role tracking
                if conn.role == AccountRole.MASTER and self.master_account_id == connection_id:
                    self.master_account_id = None
                    logger.info(f"Removed MASTER connection {connection_id}")
                elif conn.role == AccountRole.SLAVE and connection_id in self.slave_account_ids:
                    self.slave_account_ids.remove(connection_id)
                    logger.info(f"Removed SLAVE connection {connection_id}")
                
                conn.disconnect()
                del self.connections[connection_id]
                return True
            else:
                logger.warning(f"Connection {connection_id} not found")
                return False
    
    def get_connection(self, connection_id: str) -> Optional[BrokerConnection]:
        """
        Get a specific broker connection.
        
        Args:
            connection_id: Unique identifier for the connection
            
        Returns:
            BrokerConnection instance or None if not found
        """
        return self.connections.get(connection_id)
    
    def get_master_connection(self) -> Optional[BrokerConnection]:
        """
        Get the master connection.
        
        Returns:
            BrokerConnection instance for master account or None if no master
        """
        if self.master_account_id:
            return self.connections.get(self.master_account_id)
        return None
    
    def get_slave_connections(self) -> List[BrokerConnection]:
        """
        Get all slave connections.
        
        Returns:
            List of BrokerConnection instances for slave accounts
        """
        slave_connections = []
        for slave_id in self.slave_account_ids:
            if slave_id in self.connections:
                slave_connections.append(self.connections[slave_id])
        return slave_connections
    
    def get_all_connections(self) -> Dict[str, BrokerConnection]:
        """
        Get all broker connections.
        
        Returns:
            Dictionary of connection_id -> BrokerConnection
        """
        return self.connections.copy()
    
    def get_connected_accounts(self) -> List[Dict]:
        """
        Get information about all connected accounts.
        
        Returns:
            List of dictionaries containing account information
        """
        accounts = []
        with self._lock:
            for connection_id, conn in self.connections.items():
                if conn.is_connected():
                    account_info = conn.get_account_info()
                    if account_info:
                        account_info['connection_id'] = connection_id
                        account_info['broker'] = conn.broker
                        account_info['broker_server'] = conn.broker_server
                        accounts.append(account_info)
        return accounts
    
    def get_copy_trade_status(self) -> Dict:
        """
        Get status of copy trading setup.
        
        Returns:
            Dictionary with master/slave status information
        """
        master_conn = self.get_master_connection()
        slave_conns = self.get_slave_connections()
        
        return {
            'has_master': master_conn is not None,
            'master_id': self.master_account_id,
            'master_connected': master_conn.is_connected() if master_conn else False,
            'slave_count': len(slave_conns),
            'slaves_connected': sum(1 for conn in slave_conns if conn.is_connected()),
            'slave_ids': self.slave_account_ids.copy(),
            'ready_for_copy_trading': master_conn is not None and master_conn.is_connected() and any(conn.is_connected() for conn in slave_conns)
        }
    
    def disconnect_all(self) -> None:
        """Disconnect all broker connections."""
        with self._lock:
            for connection_id in list(self.connections.keys()):
                self.remove_connection(connection_id)
            self.master_account_id = None
            self.slave_account_ids.clear()
        logger.info("Disconnected all broker connections")
    
    def is_any_connected(self) -> bool:
        """
        Check if any connections are active.
        
        Returns:
            bool: True if at least one connection is active
        """
        return any(conn.is_connected() for conn in self.connections.values())
    
    def get_connection_count(self) -> int:
        """
        Get the number of active connections.
        
        Returns:
            int: Number of active connections
        """
        return len([conn for conn in self.connections.values() if conn.is_connected()])
    
    def __del__(self):
        """Clean up all connections when manager is destroyed."""
        self.disconnect_all() 

