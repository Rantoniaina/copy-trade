"""
Example script demonstrating how to use the BrokerConnection class.
"""
import os
import sys
import logging
from getpass import getpass

# Add the parent directory to the path to import the broker_connection module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.broker_connection import BrokerConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Main function to demonstrate the BrokerConnection class.
    """
    print("=== MT5 Account Connection Example ===")
    
    # Get connection parameters
    broker = input("Broker (default: FundedNext): ") or "FundedNext"
    broker_server = input("Broker server (default: fundednext server 2): ") or "fundednext server 2"
    platform = input("Platform (default: mt5): ") or "mt5"
    
    try:
        account_number = int(input("Account number: "))
    except ValueError:
        logger.error("Account number must be an integer")
        return
    
    password = getpass("Password: ")
    
    # Create broker connection
    try:
        broker_conn = BrokerConnection()
    except RuntimeError as e:
        logger.error(f"Failed to initialize MetaTrader5: {e}")
        return
    
    # Connect to the account
    connected = broker_conn.connect(
        broker=broker,
        broker_server=broker_server,
        platform=platform,
        account_number=account_number,
        password=password
    )
    
    if not connected:
        logger.error("Failed to connect to the trading account")
        return
    
    # Display account information
    account_info = broker_conn.get_account_info()
    if account_info:
        print("\n=== Account Information ===")
        print(f"Login: {account_info['login']}")
        print(f"Server: {account_info['server']}")
        print(f"Name: {account_info['name']}")
        print(f"Balance: {account_info['balance']}")
        print(f"Equity: {account_info['equity']}")
        print(f"Margin: {account_info['margin']}")
        print(f"Free Margin: {account_info['margin_free']}")
        print(f"Leverage: 1:{account_info['leverage']}")
        print(f"Currency: {account_info['currency']}")
    
    # Disconnect
    print("\nDisconnecting from the account...")
    broker_conn.disconnect()
    print("Disconnected.")


if __name__ == "__main__":
    main() 