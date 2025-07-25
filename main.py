#!/usr/bin/env python3
"""
Copy Trade - Multi-Process Main Application Entry Point
Uses separate processes for master monitoring and slave execution.
Automatically manages MT5 instances.
"""
import os
import sys
import argparse
import logging
import configparser
from getpass import getpass
from typing import Dict, List

from src.multiprocess_copy_trading import CopyTradingOrchestrator
from src.mt5_instance_manager import auto_setup_mt5_instances, get_mt5_path_for_role, get_mt5_instance_manager
from src.mt5_instance_database import get_mt5_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [MAIN-%(process)d] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Copy Trade - Multi-Process MT5 Master/Slave Trading")
    parser.add_argument("--config", required=True, help="Path to config file for accounts")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--signal-broker", choices=['file', 'queue'], default='file', 
                       help="Signal broker type (default: file)")
    parser.add_argument("--auto-setup-mt5", action="store_true", default=True,
                       help="Automatically setup MT5 instances (default: true)")
    parser.add_argument("--no-auto-setup-mt5", dest="auto_setup_mt5", action="store_false",
                       help="Disable automatic MT5 instance setup")
    parser.add_argument("--db-stats", action="store_true",
                       help="Show MT5 instance database statistics and exit")
    parser.add_argument("--db-cleanup", action="store_true",
                       help="Clean up missing MT5 instances from database and exit")
    parser.add_argument("--list-instances", action="store_true",
                       help="List all tracked MT5 instances and exit")
    
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


def parse_metatrader_config(config):
    """
    Parse MetaTrader configuration section from config file.
    
    Args:
        config: ConfigParser object
        
    Returns:
        Dictionary containing MetaTrader paths configuration
    """
    metatrader_paths = {}
    
    if 'MetaTrader' in config:
        mt_config = config['MetaTrader']
        
        # Get original MT5 installation path
        if mt_config.get('original_path', '').strip():
            metatrader_paths['original_path'] = mt_config['original_path'].strip()
            logger.info(f"Configured original MT5 path: {metatrader_paths['original_path']}")
        
        # Get master path
        if mt_config.get('master_path', '').strip():
            metatrader_paths['master_path'] = mt_config['master_path'].strip()
            logger.info(f"Configured master MT5 path: {metatrader_paths['master_path']}")
        
        # Get slaves base path
        if mt_config.get('slaves_base_path', '').strip():
            metatrader_paths['slaves_base_path'] = mt_config['slaves_base_path'].strip()
            logger.info(f"Configured slaves base path: {metatrader_paths['slaves_base_path']}")
        
        # Get individual slave paths (slave_account2_path, slave_account3_path, etc.)
        for key in mt_config:
            if key.startswith('slave_account') and key.endswith('_path'):
                if mt_config.get(key, '').strip():
                    metatrader_paths[key] = mt_config[key].strip()
                    logger.info(f"Configured individual slave path {key}: {metatrader_paths[key]}")
    
    return metatrader_paths


def load_accounts_from_config(config):
    """
    Load account configurations from config file.
    
    Args:
        config: ConfigParser object
        
    Returns:
        Tuple of (master_account, slave_accounts)
    """
    master_account = None
    slave_accounts = []
    
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
            
            # Get role
            role_str = section.get('role', 'slave').strip().lower()
            
            # Get volume scale for slaves
            volume_scale = float(section.get('volume_scale', '1.0'))
            
            # Get custom MT5 path if specified
            mt5_path = section.get('mt5_path', '').strip() or None
            
            if role_str == 'master':
                if master_account is not None:
                    logger.error(f"Multiple master accounts found. Only one master allowed.")
                    return None, []
                
                master_account = {
                    'account_number': account_number,
                    'password': password,
                    'mt5_path': mt5_path
                }
                logger.info(f"Master account configured: {account_number}")
                
            elif role_str == 'slave':
                slave_accounts.append({
                    'account_number': account_number,
                    'password': password,
                    'volume_scale': volume_scale,
                    'mt5_path': mt5_path
                })
                logger.info(f"Slave account configured: {account_number} (scale: {volume_scale}x)")
                
            else:
                logger.error(f"Invalid role '{role_str}' in {section_name}. Must be 'master' or 'slave'")
                continue
    
    return master_account, slave_accounts


def setup_mt5_instances(master_count: int, slave_count: int, auto_setup: bool = True, config_paths: Dict[str, str] = None) -> Dict[str, str]:
    """Setup MT5 instances automatically if enabled."""
    mt5_paths = {}
    
    if auto_setup:
        try:
            logger.info("🔧 Setting up MT5 instances automatically...")
            if config_paths:
                logger.info("Using MetaTrader configuration paths from config file")
            mt5_paths = auto_setup_mt5_instances(master_count, slave_count, config_paths)
            
            if mt5_paths:
                logger.info("✅ MT5 instances ready:")
                for role, path in mt5_paths.items():
                    logger.info(f"  {role}: {path}")
            else:
                logger.warning("⚠️ No MT5 instances created - will use default installation")
                
        except Exception as e:
            logger.error(f"❌ Failed to setup MT5 instances automatically: {e}")
            logger.info("Continuing with default MT5 installation...")
    else:
        logger.info("MT5 instance auto-setup disabled")
    
    return mt5_paths


def show_database_stats():
    """Show MT5 instance database statistics."""
    db = get_mt5_database()
    stats = db.get_database_stats()
    
    print("🗄️ MT5 Instance Database Statistics:")
    print(f"   Database file: {stats.get('database_path', 'Unknown')}")
    print(f"   Total instances: {stats.get('total_instances', 0)}")
    print(f"   Active instances: {stats.get('active_instances', 0)}")
    print(f"   Inactive instances: {stats.get('inactive_instances', 0)}")
    
    role_counts = stats.get('role_counts', {})
    if role_counts:
        print("   Instances by role:")
        for role, count in role_counts.items():
            print(f"     {role}: {count}")
    else:
        print("   No active instances found")


def cleanup_database():
    """Clean up missing MT5 instances from database."""
    print("🧹 Cleaning up missing MT5 instances from database...")
    
    db = get_mt5_database()
    removed_count = db.cleanup_missing_instances()
    
    if removed_count > 0:
        print(f"✅ Removed {removed_count} missing instances from database")
    else:
        print("✅ No missing instances found - database is clean")


def list_tracked_instances():
    """List all tracked MT5 instances."""
    db = get_mt5_database()
    instances = db.get_all_instances(active_only=False)
    
    if not instances:
        print("📝 No MT5 instances tracked in database")
        return
    
    print(f"📝 Tracked MT5 Instances ({len(instances)} total):")
    print()
    
    for instance in instances:
        status = "🟢 Active" if instance['is_active'] else "🔴 Inactive"
        print(f"   {status} - {instance['role']}")
        print(f"     Path: {instance['instance_path']}")
        if instance['account_number']:
            print(f"     Account: {instance['account_number']}")
        if instance['broker']:
            print(f"     Broker: {instance['broker']}")
        if instance['description']:
            print(f"     Description: {instance['description']}")
        print(f"     Created: {instance['created_at']}")
        print(f"     Last used: {instance['last_used']}")
        print()


def assign_mt5_paths(master_account: Dict, slave_accounts: List[Dict], mt5_paths: Dict[str, str], config_paths: Dict[str, str] = None) -> None:
    """
    Assign MT5 paths to accounts if not already specified.
    
    Args:
        master_account: Master account configuration
        slave_accounts: List of slave account configurations
        mt5_paths: Dictionary of instance paths from MT5 manager
        config_paths: MetaTrader configuration paths from config file
    """
    
    # Assign master path if not specified
    if not master_account.get('mt5_path'):
        # Try configured master path first
        if config_paths and config_paths.get('master_path'):
            master_account['mt5_path'] = config_paths['master_path']
            logger.info(f"Assigned configured master MT5 path: {config_paths['master_path']}")
        # Fallback to auto-generated paths
        elif mt5_paths:
            master_path = mt5_paths.get('master') or mt5_paths.get('master1')
            if master_path:
                master_account['mt5_path'] = master_path
                logger.info(f"Assigned auto-generated master MT5 path: {master_path}")
    
    # Assign slave paths if not specified
    slave_index = 1
    for slave in slave_accounts:
        if not slave.get('mt5_path'):
            account_num = slave_index + 1  # Account2, Account3, etc.
            individual_slave_key = f"slave_account{account_num}_path"
            
            # Try individual configured slave path first
            if config_paths and config_paths.get(individual_slave_key):
                slave['mt5_path'] = config_paths[individual_slave_key]
                logger.info(f"Assigned configured individual slave {slave_index} MT5 path: {config_paths[individual_slave_key]}")
            # Try base slaves path with account directory
            elif config_paths and config_paths.get('slaves_base_path'):
                slave_path = os.path.join(config_paths['slaves_base_path'], f"Account{account_num}")
                slave['mt5_path'] = slave_path
                logger.info(f"Assigned configured base slave {slave_index} MT5 path: {slave_path}")
            # Fallback to auto-generated paths
            elif mt5_paths:
                if len(slave_accounts) == 1:
                    slave_path = mt5_paths.get('slave') or mt5_paths.get('slave1')
                else:
                    slave_path = mt5_paths.get(f'slave{slave_index}') or mt5_paths.get('slave')
                
                if slave_path:
                    slave['mt5_path'] = slave_path
                    logger.info(f"Assigned auto-generated slave {slave_index} MT5 path: {slave_path}")
        
        slave_index += 1


def main():
    """Main application entry point."""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Handle database management commands
    if args.db_stats:
        show_database_stats()
        return 0
    
    if args.db_cleanup:
        cleanup_database()
        return 0
    
    if args.list_instances:
        list_tracked_instances()
        return 0
    
    logger.info("🚀 STARTING MULTI-PROCESS COPY TRADING SYSTEM with AUTO MT5 SETUP")
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        return 1
    
    # Get broker settings
    if 'Connection' not in config:
        logger.error("Missing [Connection] section in config file")
        return 1
    
    conn_config = config['Connection']
    broker = conn_config.get('broker', 'FundedNext')
    broker_server = conn_config.get('server', 'FundedNext-Server 2')
    platform = conn_config.get('platform', 'MT5')
    
    # Get copy trade settings
    check_interval = 1.0
    if 'CopyTrade' in config:
        copy_config = config['CopyTrade']
        check_interval = copy_config.getfloat('check_interval', 1.0)
    
    # Parse MetaTrader configuration paths
    metatrader_paths = parse_metatrader_config(config)
    
    # Load accounts
    master_account, slave_accounts = load_accounts_from_config(config)
    
    if master_account is None:
        logger.error("No master account found. Please set one account with role=master")
        return 1
    
    if len(slave_accounts) == 0:
        logger.error("No slave accounts found. Please set at least one account with role=slave")
        return 1
    
    logger.info(f"Configuration loaded: 1 master, {len(slave_accounts)} slaves")
    
    # Setup MT5 instances automatically
    mt5_paths = setup_mt5_instances(
        master_count=1, 
        slave_count=len(slave_accounts), 
        auto_setup=args.auto_setup_mt5,
        config_paths=metatrader_paths # Pass parsed paths to setup_mt5_instances
    )
    
    # Assign MT5 paths to accounts
    assign_mt5_paths(master_account, slave_accounts, mt5_paths, metatrader_paths)
    
    # Create orchestrator
    orchestrator = CopyTradingOrchestrator(signal_broker_type=args.signal_broker)
    
    # Configure orchestrator
    orchestrator.configure(
        broker=broker,
        broker_server=broker_server,
        platform=platform,
        check_interval=check_interval
    )
    
    # Add slave accounts FIRST (consistent with process startup order)
    for i, slave in enumerate(slave_accounts):
        success = orchestrator.add_slave_account(
            account_number=slave['account_number'],
            password=slave['password'],
            volume_scale=slave['volume_scale'],
            mt5_path=slave.get('mt5_path')
        )
        if not success:
            logger.error(f"Failed to add slave account {slave['account_number']}")
            return 1
    
    # Add master account LAST (consistent with process startup order)
    success = orchestrator.add_master_account(
        account_number=master_account['account_number'],
        password=master_account['password'],
        mt5_path=master_account.get('mt5_path')
    )
    if not success:
        logger.error("Failed to add master account")
        return 1
    
    # Start copy trading system
    if not orchestrator.start_copy_trading():
        logger.error("Failed to start copy trading system")
        return 1
    
    # Display status
    status = orchestrator.get_status()
    logger.info(f"System Status: Master={status['master_running']}, Slaves={status['slaves_running']}/{status['total_slaves']}")
    
    # Display MT5 instance information
    logger.info("🔧 MT5 Instance Information:")
    logger.info(f"  Master: {master_account.get('mt5_path', 'Default installation')}")
    for i, slave in enumerate(slave_accounts):
        logger.info(f"  Slave {i+1}: {slave.get('mt5_path', 'Default installation')}")
    
    # Wait for interruption and handle shutdown
    try:
        orchestrator.wait_for_interruption()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        orchestrator.stop_copy_trading()
        return 1
    
    # Cleanup
    orchestrator.cleanup_signal_files()
    
    logger.info("🏁 COPY TRADING SYSTEM SHUTDOWN COMPLETE")
    return 0


if __name__ == "__main__":
    # Set multiprocessing start method for Windows compatibility
    import multiprocessing
    try:
        multiprocessing.set_start_method('spawn')
    except RuntimeError:
        pass  # Already set
    
    sys.exit(main()) 