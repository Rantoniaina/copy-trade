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

from src.broker_connection import BrokerConnection, MultiBrokerManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Copy Trade - MT5 Multiple Trading Account Connection")
    parser.add_argument("--broker", default="FundedNext", help="Broker name (default: FundedNext)")
    parser.add_argument("--server", default="fundednext server 2", help="Broker server (default: fundednext server 2)")
    parser.add_argument("--platform", default="mt5", help="Trading platform (default: mt5)")
    parser.add_argument("--account", type=int, help="Single account number (legacy mode)")
    parser.add_argument("--config", help="Path to config file for multiple accounts")
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


def load_multiple_accounts_from_config(config):
    """
    Load multiple account configurations from config file.
    
    Args:
        config: ConfigParser object
        
    Returns:
        List of tuples (connection_id, account_number, password)
    """
    accounts = []
    
    # Look for Account sections (Account1, Account2, etc.)
    for section_name in config.sections():
        if section_name.startswith('Account'):
            section = config[section_name]
            
            # Get account number
            if 'account' not in section or not section['account'].strip():
                logger.warning(f"Skipping {section_name}: missing account number")
                continue
            
            try:
                account_number = int(section['account'])
            except ValueError:
                logger.error(f"Skipping {section_name}: account number must be an integer")
                continue
            
            # Get password
            password = section.get('password', '').strip()
            if not password:
                password = getpass(f"Password for {section_name} (account {account_number}): ")
            
            accounts.append((section_name.lower(), account_number, password))
    
    return accounts


def connect_single_account():
    """Connect to a single account (legacy mode)."""
    args = parse_args()
    
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
    
    # If account number is still not provided, prompt for it
    if not account_number:
        try:
            account_number = int(input("Account number: "))
        except ValueError:
            logger.error("Account number must be an integer")
            return 1
    
    # Get password
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


def main():
    """Main application entry point."""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # If config file is not provided or single account mode, use legacy mode
    if not args.config:
        logger.info("No config file provided. Using single account mode.")
        return connect_single_account()
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        return 1
    
    # Check if this is a multiple account configuration
    account_sections = [s for s in config.sections() if s.startswith('Account')]
    if not account_sections:
        logger.info("No Account sections found in config. Using single account mode.")
        return connect_single_account()
    
    # Get default broker settings
    if 'Connection' not in config:
        logger.error("Missing [Connection] section in config file")
        return 1
    
    conn_config = config['Connection']
    broker = conn_config.get('broker', 'FundedNext')
    broker_server = conn_config.get('server', 'FundedNext-Server 2')
    platform = conn_config.get('platform', 'MT5')
    
    # Load multiple accounts from config
    accounts = load_multiple_accounts_from_config(config)
    if not accounts:
        logger.error("No valid accounts found in configuration")
        return 1
    
    # Create multi-broker manager
    manager = MultiBrokerManager()
    
    # Connect to all accounts
    connected_count = 0
    for connection_id, account_number, password in accounts:
        logger.info(f"Connecting to {connection_id} (account {account_number})...")
        
        success = manager.add_connection(
            connection_id=connection_id,
            broker=broker,
            broker_server=broker_server,
            platform=platform,
            account_number=account_number,
            password=password
        )
        
        if success:
            connected_count += 1
        else:
            logger.error(f"Failed to connect to {connection_id}")
    
    if connected_count == 0:
        logger.error("Failed to connect to any accounts")
        return 1
    
    # Display information about all connected accounts
    logger.info(f"Successfully connected to {connected_count} out of {len(accounts)} accounts")
    
    connected_accounts = manager.get_connected_accounts()
    for account in connected_accounts:
        logger.info(f"[{account['connection_id']}] Account {account['login']} on {account['server']} - Balance: {account['balance']} {account['currency']}")
    
    # TODO: Add copy trade functionality here
    
    # Keep connections alive until user interrupts
    try:
        logger.info("All connections established. Press Ctrl+C to disconnect and exit.")
        while manager.is_any_connected():
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("User interrupted. Disconnecting all accounts...")
    finally:
        manager.disconnect_all()
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 