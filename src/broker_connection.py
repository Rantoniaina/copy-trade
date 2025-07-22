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
    
    def __init__(self):
        """Initialize the BrokerConnection instance."""
        self.connected = False
        self.account_info = None
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
            logger.error(f"Unsupported platform: {platform}. Only MT5 is currently supported.")
            return False
        
        # Disconnect from any existing connection
        self.disconnect()
        
        # Use the server name directly from config
        server = broker_server.strip()
        
        # Initialize MT5 with login credentials directly (headless mode)
        logger.info(f"Attempting to connect to {broker} ({server}) account {account_number}")
        
        # Try to initialize with credentials directly - this should avoid the GUI
        if not mt5.initialize(login=account_number, password=password, server=server):
            error_code = mt5.last_error()
            logger.error(f"MT5 initialization with credentials failed. Error: {error_code}")
            
            # Fallback: try regular initialize then login
            logger.info("Trying fallback initialization method...")
            if not mt5.initialize():
                error_code = mt5.last_error()
                logger.error(f"MT5 initialization failed. Error: {error_code}")
                return False
            
            # Now try to login
            if not mt5.login(account_number, password=password, server=server):
                error_code = mt5.last_error()
                logger.error(f"Login failed. Error: {error_code}")
                mt5.shutdown()
                return False
        
        # Store account information
        self.account_info = mt5.account_info()
        if not self.account_info:
            logger.error("Failed to get account info")
            mt5.shutdown()
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