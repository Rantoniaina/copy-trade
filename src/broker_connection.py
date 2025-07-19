"""
Module for connecting to trading accounts via MetaTrader 5.
"""
import time
import logging
from typing import Dict, Optional, Tuple, Union

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


class BrokerConnection:
    """
    Class to manage connections to trading accounts via MetaTrader 5.
    """
    
    # Known broker servers
    BROKER_SERVERS = {
        "FundedNext": {
            "fundednext server 2": "FundedNext-Live2"
        }
    }
    
    def __init__(self):
        """Initialize the BrokerConnection instance."""
        self.connected = False
        self.account_info = None
        
        # Initialize MT5 if not already initialized
        if not mt5.initialize():
            logger.error(f"MetaTrader5 initialization failed. Error code: {mt5.last_error()}")
            raise RuntimeError(f"MetaTrader5 initialization failed: {mt5.last_error()}")
        else:
            logger.info("MetaTrader5 initialized successfully")
    
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
            broker_server: Broker server name (e.g., "fundednext server 2")
            platform: Trading platform (currently only "mt5" is supported)
            account_number: Trading account number
            password: Trading account password
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        if platform.lower() != "mt5":
            logger.error(f"Unsupported platform: {platform}. Only MT5 is currently supported.")
            return False
        
        # Disconnect from any existing connection
        self.disconnect()
        
        # Resolve server name
        server = self._resolve_server(broker, broker_server)
        if not server:
            logger.error(f"Unknown broker/server combination: {broker}/{broker_server}")
            return False
        
        # Login to the account
        logger.info(f"Attempting to connect to {broker} ({server}) account {account_number}")
        login_result = mt5.login(account_number, password=password, server=server)
        
        if not login_result:
            error_code = mt5.last_error()
            logger.error(f"Connection failed. Error code: {error_code}")
            return False
        
        # Store account information
        self.account_info = mt5.account_info()
        if not self.account_info:
            logger.error("Failed to get account info")
            return False
        
        self.connected = True
        logger.info(f"Successfully connected to account {account_number}")
        return True
    
    def disconnect(self) -> None:
        """Disconnect from the current trading account."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            self.account_info = None
            logger.info("Disconnected from trading account")
    
    def is_connected(self) -> bool:
        """Check if currently connected to a trading account."""
        return self.connected
    
    def get_account_info(self) -> Optional[Dict]:
        """
        Get information about the connected account.
        
        Returns:
            Dict containing account information or None if not connected
        """
        if not self.connected:
            logger.warning("Not connected to any account")
            return None
        
        # Refresh account info
        self.account_info = mt5.account_info()
        if not self.account_info:
            logger.error("Failed to get account info")
            return None
        
        # Convert named tuple to dictionary
        return self.account_info._asdict()
    
    def _resolve_server(self, broker: str, broker_server: str) -> Optional[str]:
        """
        Resolve broker and server name to the actual server address.
        
        Args:
            broker: Broker name
            broker_server: Broker server name
            
        Returns:
            str: Resolved server address or None if not found
        """
        broker = broker.strip()
        broker_server = broker_server.strip().lower()
        
        if broker not in self.BROKER_SERVERS:
            logger.error(f"Unknown broker: {broker}")
            return None
        
        if broker_server not in self.BROKER_SERVERS[broker]:
            logger.error(f"Unknown server for broker {broker}: {broker_server}")
            return None
        
        return self.BROKER_SERVERS[broker][broker_server] 