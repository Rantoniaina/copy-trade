#!/usr/bin/env python3
"""
Example script demonstrating multiple broker connections using MultiBrokerManager.
"""
import os
import sys
import logging
from getpass import getpass

# Add the parent directory to the path to import the broker_connection module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.broker_connection import MultiBrokerManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_account_details(account_name):
    """
    Get account details from user input.
    
    Args:
        account_name: Display name for the account (e.g., "Account 1")
        
    Returns:
        tuple: (account_number, password) or (None, None) if cancelled
    """
    print(f"\n=== {account_name} Details ===")
    
    try:
        account_number = input(f"Account number for {account_name} (or 'skip' to skip): ").strip()
        if account_number.lower() == 'skip':
            return None, None
        
        account_number = int(account_number)
    except ValueError:
        logger.error("Account number must be an integer")
        return None, None
    
    password = getpass(f"Password for {account_name}: ")
    if not password:
        logger.error("Password cannot be empty")
        return None, None
    
    return account_number, password


def main():
    """
    Main function to demonstrate multiple broker connections.
    """
    print("=== MT5 Multiple Account Connection Example ===")
    
    # Get common broker settings
    broker = input("Broker (default: FundedNext): ").strip() or "FundedNext"
    broker_server = input("Broker server (default: FundedNext-Server 2): ").strip() or "FundedNext-Server 2"
    platform = input("Platform (default: mt5): ").strip() or "mt5"
    
    # Create MultiBrokerManager
    try:
        manager = MultiBrokerManager()
    except Exception as e:
        logger.error(f"Failed to initialize MultiBrokerManager: {e}")
        return
    
    # Collect account details
    accounts_to_connect = []
    account_count = 1
    
    while True:
        account_number, password = get_account_details(f"Account {account_count}")
        
        if account_number is None:
            if account_count == 1:
                logger.error("At least one account is required")
                return
            break
        
        accounts_to_connect.append({
            'id': f"account{account_count}",
            'number': account_number,
            'password': password
        })
        
        account_count += 1
        
        # Ask if user wants to add more accounts
        if account_count > 5:  # Reasonable limit
            logger.info("Maximum 5 accounts reached")
            break
        
        continue_adding = input(f"\nAdd another account? (y/N): ").strip().lower()
        if continue_adding not in ['y', 'yes']:
            break
    
    if not accounts_to_connect:
        logger.error("No accounts to connect")
        return
    
    print(f"\nAttempting to connect to {len(accounts_to_connect)} account(s)...")
    
    # Connect to all accounts
    connected_count = 0
    failed_accounts = []
    
    for account in accounts_to_connect:
        logger.info(f"Connecting to {account['id']} (account {account['number']})...")
        
        success = manager.add_connection(
            connection_id=account['id'],
            broker=broker,
            broker_server=broker_server,
            platform=platform,
            account_number=account['number'],
            password=account['password']
        )
        
        if success:
            connected_count += 1
        else:
            failed_accounts.append(account['id'])
    
    # Display results
    print(f"\n=== Connection Results ===")
    print(f"Successfully connected: {connected_count} out of {len(accounts_to_connect)} accounts")
    
    if failed_accounts:
        print(f"Failed connections: {', '.join(failed_accounts)}")
    
    if connected_count == 0:
        logger.error("No accounts connected successfully")
        return
    
    # Display account information
    print(f"\n=== Connected Account Details ===")
    connected_accounts = manager.get_connected_accounts()
    
    for account in connected_accounts:
        print(f"[{account['connection_id']}] Account: {account['login']}")
        print(f"  ├─ Server: {account['server']}")
        print(f"  ├─ Name: {account['name']}")
        print(f"  ├─ Balance: {account['balance']} {account['currency']}")
        print(f"  ├─ Equity: {account['equity']} {account['currency']}")
        print(f"  ├─ Margin: {account['margin']} {account['currency']}")
        print(f"  ├─ Free Margin: {account['margin_free']} {account['currency']}")
        print(f"  └─ Leverage: 1:{account['leverage']}")
        print()
    
    # Demonstrate manager functionality
    print(f"=== Manager Status ===")
    print(f"Total connections: {manager.get_connection_count()}")
    print(f"Any connected: {manager.is_any_connected()}")
    
    # Keep connections alive for demonstration
    try:
        print("Connections established. Press Ctrl+C to disconnect and exit.")
        while manager.is_any_connected():
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nUser interrupted. Disconnecting all accounts...")
    finally:
        manager.disconnect_all()
        print("All accounts disconnected.")


if __name__ == "__main__":
    main() 