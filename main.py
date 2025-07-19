#!/usr/bin/env python3
"""
Copy Trade - Main application entry point
"""
import os
import sys
import argparse
import logging
import configparser
from getpass import getpass

from src.broker_connection import BrokerConnection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Copy Trade - MT5 Trading Account Connection")
    parser.add_argument("--broker", default="FundedNext", help="Broker name (default: FundedNext)")
    parser.add_argument("--server", default="fundednext server 2", help="Broker server (default: fundednext server 2)")
    parser.add_argument("--platform", default="mt5", help="Trading platform (default: mt5)")
    parser.add_argument("--account", type=int, help="Account number")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    return parser.parse_args()


def load_config(config_path):
    """Load configuration from a file."""
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return None
    
    config = configparser.ConfigParser()
    try:
        config.read(config_path)
        return config
    except configparser.Error as e:
        logger.error(f"Error reading config file: {e}")
        return None


def main():
    """Main application entry point."""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration from file if specified
    config = None
    if args.config:
        config = load_config(args.config)
    
    # Get connection parameters
    broker = args.broker
    broker_server = args.server
    platform = args.platform
    account_number = args.account
    
    # If config is available, use it to override command line arguments
    if config and 'Connection' in config:
        conn_config = config['Connection']
        broker = conn_config.get('broker', broker)
        broker_server = conn_config.get('server', broker_server)
        platform = conn_config.get('platform', platform)
        if not account_number and 'account' in conn_config:
            try:
                account_number = int(conn_config['account'])
            except ValueError:
                logger.error("Account number in config must be an integer")
    
    # If account number is still not provided, prompt for it
    if not account_number:
        try:
            account_number = int(input("Account number: "))
        except ValueError:
            logger.error("Account number must be an integer")
            return 1
    
    # Get password
    password = None
    if config and 'Connection' in config and 'password' in config['Connection']:
        password = config['Connection']['password']
    
    if not password:
        password = getpass("Password: ")
    
    # Create broker connection
    try:
        broker_conn = BrokerConnection()
    except RuntimeError as e:
        logger.error(f"Failed to initialize MetaTrader5: {e}")
        return 1
    
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
        return 1
    
    # Display account information
    account_info = broker_conn.get_account_info()
    if account_info:
        logger.info(f"Connected to account {account_info['login']} on server {account_info['server']}")
        logger.info(f"Balance: {account_info['balance']} {account_info['currency']}")
    
    # TODO: Add copy trade functionality here
    
    # Keep the connection alive until user interrupts
    try:
        logger.info("Connection established. Press Ctrl+C to disconnect and exit.")
        while broker_conn.is_connected():
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("User interrupted. Disconnecting...")
    finally:
        broker_conn.disconnect()
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 