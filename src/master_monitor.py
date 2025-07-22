"""
Master account monitor that runs in a separate process.
Monitors the master account for new trades and sends signals to slaves.
"""
import os
import sys
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.broker_connection import BrokerConnection, AccountRole
from src.signal_broker import TradeSignal, get_signal_broker

# Configure logging for this process
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [MASTER-%(process)d] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MasterMonitor:
    """Monitor master account for trades and send signals to slaves."""
    
    def __init__(self, 
                 broker: str,
                 broker_server: str,
                 platform: str,
                 account_number: int,
                 password: str,
                 signal_broker_type: str = 'file',
                 mt5_path: str = None):
        """
        Initialize master monitor.
        
        Args:
            broker: Broker name
            broker_server: Broker server
            platform: Trading platform
            account_number: Master account number
            password: Master account password
            signal_broker_type: Type of signal broker ('file' or 'queue')
            mt5_path: Path to specific MT5 installation
        """
        self.broker = broker
        self.broker_server = broker_server
        self.platform = platform
        self.account_number = account_number
        self.password = password
        self.mt5_path = mt5_path
        
        # Initialize signal broker
        self.signal_broker = get_signal_broker(signal_broker_type)
        
        # Initialize connection
        self.connection = None
        self.is_running = False
        self.last_positions = {}
        self.last_orders = {}  # Track pending orders
        
        logger.info(f"Master monitor initialized for account {account_number}" + 
                   (f" with MT5 path: {mt5_path}" if mt5_path else ""))
    
    def start_monitoring(self, check_interval: float = 1.0) -> bool:
        """
        Start monitoring the master account.
        
        Args:
            check_interval: Time between position checks in seconds
            
        Returns:
            bool: True if monitoring started successfully
        """
        # Connect to master account
        if not self._connect():
            logger.error("Failed to connect to master account")
            return False
        
        # Get initial positions and orders
        try:
            initial_positions = self.connection.get_open_positions()
            self.last_positions = {pos['ticket']: pos for pos in initial_positions}
            
            initial_orders = self._get_pending_orders()
            self.last_orders = {order['ticket']: order for order in initial_orders}
            
            logger.info(f"👑 MASTER MONITORING STARTED - {len(self.last_positions)} positions, {len(self.last_orders)} pending orders")
        except Exception as e:
            logger.error(f"Failed to get initial positions/orders: {e}")
            self.last_positions = {}
            self.last_orders = {}
        
        # Start monitoring loop
        self.is_running = True
        self._monitoring_loop(check_interval)
        
        return True
    
    def stop_monitoring(self) -> None:
        """Stop monitoring and disconnect."""
        self.is_running = False
        if self.connection:
            self.connection.disconnect()
            logger.info("👑 MASTER MONITORING STOPPED")
    
    def _connect(self) -> bool:
        """Connect to the master account."""
        try:
            self.connection = BrokerConnection("master", AccountRole.MASTER, self.mt5_path)
            success = self.connection.connect(
                broker=self.broker,
                broker_server=self.broker_server,
                platform=self.platform,
                account_number=self.account_number,
                password=self.password
            )
            
            if success:
                logger.info(f"👑 Connected to master account {self.account_number}")
                return True
            else:
                logger.error(f"Failed to connect to master account {self.account_number}")
                return False
                
        except Exception as e:
            logger.error(f"Exception connecting to master account: {e}")
            return False
    
    def _monitoring_loop(self, check_interval: float) -> None:
        """Main monitoring loop."""
        logger.info(f"👑 Starting monitoring loop with {check_interval}s interval")
        
        while self.is_running:
            try:
                self._check_for_position_changes()
                time.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("👑 Monitoring interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(check_interval)  # Continue despite errors
        
        logger.info("👑 Monitoring loop ended")
    
    def _get_pending_orders(self) -> List[Dict]:
        """Get pending orders from the account."""
        if not self.connection or not self.connection.is_connected():
            return []
        
        try:
            import MetaTrader5 as mt5
            orders = mt5.orders_get()
            if orders is None:
                return []
            return [order._asdict() for order in orders]
        except Exception as e:
            logger.error(f"Error getting pending orders: {e}")
            return []
    
    def _check_for_position_changes(self) -> None:
        """Check for position changes and send signals."""
        if not self.connection or not self.connection.is_connected():
            logger.warning("Master connection not available")
            return
        
        try:
            # Check positions
            current_positions = self.connection.get_open_positions()
            current_tickets = {pos['ticket']: pos for pos in current_positions}
            
            # Check pending orders
            current_orders = self._get_pending_orders()
            current_order_tickets = {order['ticket']: order for order in current_orders}
            
            # Find new positions
            new_positions = []
            for ticket, position in current_tickets.items():
                if ticket not in self.last_positions:
                    new_positions.append(position)
            
            # Find closed positions
            closed_positions = []
            for ticket, position in self.last_positions.items():
                if ticket not in current_tickets:
                    closed_positions.append(position)
            
            # Find new pending orders
            new_orders = []
            for ticket, order in current_order_tickets.items():
                if ticket not in self.last_orders:
                    new_orders.append(order)
            
            # Find cancelled/filled orders
            removed_orders = []
            for ticket, order in self.last_orders.items():
                if ticket not in current_order_tickets:
                    removed_orders.append(order)
            
            # Process new positions
            for position in new_positions:
                self._send_open_signal(position)
            
            # Process closed positions
            for position in closed_positions:
                self._send_close_signal(position)
            
            # Process new pending orders
            for order in new_orders:
                self._send_pending_order_signal(order)
            
            # Process removed orders (cancelled or filled)
            for order in removed_orders:
                self._send_order_removed_signal(order)
            
            # Update tracked positions and orders
            self.last_positions = current_tickets
            self.last_orders = current_order_tickets
            
        except Exception as e:
            logger.error(f"Error checking position changes: {e}")
    
    def _send_open_signal(self, position: Dict) -> None:
        """Send signal for a new position."""
        try:
            signal = TradeSignal(
                master_account=self.account_number,
                action='OPEN',
                symbol=position.get('symbol', ''),
                trade_type=position.get('type', 0),
                volume=position.get('volume', 0.0),
                price=position.get('price_open', 0.0),
                ticket=position.get('ticket', 0)
            )
            
            success = self.signal_broker.send_signal(signal)
            if success:
                pos_type = "BUY" if position.get('type') == 0 else "SELL"
                logger.info(f"🆕 NEW POSITION SIGNAL: {signal.symbol} {pos_type} {signal.volume} (Ticket: {signal.ticket})")
            else:
                logger.error(f"Failed to send open signal for ticket {signal.ticket}")
                
        except Exception as e:
            logger.error(f"Error sending open signal: {e}")
    
    def _send_close_signal(self, position: Dict) -> None:
        """Send signal for a closed position."""
        try:
            signal = TradeSignal(
                master_account=self.account_number,
                action='CLOSE',
                symbol=position.get('symbol', ''),
                trade_type=position.get('type', 0),
                volume=position.get('volume', 0.0),
                price=position.get('price_current', 0.0),
                ticket=position.get('ticket', 0)
            )
            
            success = self.signal_broker.send_signal(signal)
            if success:
                logger.info(f"🔴 CLOSE POSITION SIGNAL: {signal.symbol} (Ticket: {signal.ticket})")
            else:
                logger.error(f"Failed to send close signal for ticket {signal.ticket}")
                
        except Exception as e:
            logger.error(f"Error sending close signal: {e}")
    
    def _send_pending_order_signal(self, order: Dict) -> None:
        """Send signal for a new pending order."""
        try:
            signal = TradeSignal(
                master_account=self.account_number,
                action='PENDING_ORDER',
                symbol=order.get('symbol', ''),
                trade_type=order.get('type', 0),
                volume=order.get('volume_initial', 0.0),
                price=order.get('price_open', 0.0),
                ticket=order.get('ticket', 0)
            )
            
            success = self.signal_broker.send_signal(signal)
            if success:
                order_type = self._get_order_type_str(order.get('type', 0))
                logger.info(f"📋 NEW PENDING ORDER SIGNAL: {signal.symbol} {order_type} {signal.volume} @ {signal.price} (Ticket: {signal.ticket})")
            else:
                logger.error(f"Failed to send pending order signal for ticket {signal.ticket}")
                
        except Exception as e:
            logger.error(f"Error sending pending order signal: {e}")
    
    def _send_order_removed_signal(self, order: Dict) -> None:
        """Send signal for a removed (cancelled or filled) pending order."""
        try:
            signal = TradeSignal(
                master_account=self.account_number,
                action='ORDER_REMOVED',
                symbol=order.get('symbol', ''),
                trade_type=order.get('type', 0),
                volume=order.get('volume_initial', 0.0),
                price=order.get('price_open', 0.0),
                ticket=order.get('ticket', 0)
            )
            
            success = self.signal_broker.send_signal(signal)
            if success:
                logger.info(f"❌ ORDER REMOVED SIGNAL: {signal.symbol} (Ticket: {signal.ticket})")
            else:
                logger.error(f"Failed to send order removed signal for ticket {signal.ticket}")
                
        except Exception as e:
            logger.error(f"Error sending order removed signal: {e}")
    
    def _get_order_type_str(self, order_type: int) -> str:
        """Get human readable order type string."""
        order_types = {
            0: "BUY",
            1: "SELL", 
            2: "BUY_LIMIT",
            3: "SELL_LIMIT",
            4: "BUY_STOP",
            5: "SELL_STOP",
            6: "BUY_STOP_LIMIT",
            7: "SELL_STOP_LIMIT"
        }
        return order_types.get(order_type, f"UNKNOWN({order_type})")


def run_master_monitor(broker: str,
                      broker_server: str,
                      platform: str,
                      account_number: int,
                      password: str,
                      check_interval: float = 1.0,
                      signal_broker_type: str = 'file',
                      mt5_path: str = None) -> None:
    """
    Run master monitor in a separate process.
    
    Args:
        broker: Broker name
        broker_server: Broker server
        platform: Trading platform
        account_number: Master account number
        password: Master account password
        check_interval: Time between checks in seconds
        signal_broker_type: Type of signal broker ('file' or 'queue')
        mt5_path: Path to specific MT5 installation
    """
    logger.info(f"👑 MASTER MONITOR PROCESS STARTED for account {account_number}" + 
               (f" with MT5 path: {mt5_path}" if mt5_path else ""))
    
    try:
        monitor = MasterMonitor(
            broker=broker,
            broker_server=broker_server,
            platform=platform,
            account_number=account_number,
            password=password,
            signal_broker_type=signal_broker_type,
            mt5_path=mt5_path
        )
        
        # Start monitoring (blocking call)
        monitor.start_monitoring(check_interval)
        
    except KeyboardInterrupt:
        logger.info("👑 Master monitor interrupted by user")
    except Exception as e:
        logger.error(f"👑 Master monitor error: {e}")
    finally:
        logger.info("👑 MASTER MONITOR PROCESS ENDED")


if __name__ == "__main__":
    # For testing - can be run directly
    import sys
    
    if len(sys.argv) < 6:
        print("Usage: python master_monitor.py <broker> <server> <platform> <account> <password> [check_interval]")
        sys.exit(1)
    
    broker = sys.argv[1]
    broker_server = sys.argv[2] 
    platform = sys.argv[3]
    account_number = int(sys.argv[4])
    password = sys.argv[5]
    check_interval = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
    
    run_master_monitor(broker, broker_server, platform, account_number, password, check_interval) 