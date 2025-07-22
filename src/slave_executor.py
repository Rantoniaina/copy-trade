"""
Slave account executor that runs in a separate process.
Receives trade signals and executes them on slave accounts.
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

try:
    import MetaTrader5 as mt5
except ImportError:
    raise ImportError("MetaTrader5 package is required")

# Configure logging for this process
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [SLAVE-%(process)d] - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SlaveExecutor:
    """Execute trades on slave account based on signals from master."""
    
    def __init__(self,
                 broker: str,
                 broker_server: str,
                 platform: str,
                 account_number: int,
                 password: str,
                 master_account: int,
                 signal_broker_type: str = 'file',
                 volume_scale: float = 1.0,
                 mt5_path: str = None):
        """
        Initialize slave executor.
        
        Args:
            broker: Broker name
            broker_server: Broker server
            platform: Trading platform
            account_number: Slave account number
            password: Slave account password
            master_account: Master account number to follow
            signal_broker_type: Type of signal broker ('file' or 'queue')
            volume_scale: Volume scaling factor (1.0 = same volume, 0.5 = half volume)
            mt5_path: Path to specific MT5 installation
        """
        self.broker = broker
        self.broker_server = broker_server
        self.platform = platform
        self.account_number = account_number
        self.password = password
        self.master_account = master_account
        self.volume_scale = volume_scale
        self.mt5_path = mt5_path
        
        # Initialize signal broker
        self.signal_broker = get_signal_broker(signal_broker_type)
        
        # Initialize connection
        self.connection = None
        self.is_running = False
        self.open_positions = {}  # Track positions opened by this slave
        
        logger.info(f"Slave executor initialized for account {account_number} following master {master_account}" +
                   (f" with MT5 path: {mt5_path}" if mt5_path else ""))
    
    def start_execution(self, check_interval: float = 0.5) -> bool:
        """
        Start executing trades based on signals.
        
        Args:
            check_interval: Time between signal checks in seconds
            
        Returns:
            bool: True if execution started successfully
        """
        # Connect to slave account
        if not self._connect():
            logger.error("Failed to connect to slave account")
            return False
        
        logger.info(f"👥 SLAVE EXECUTION STARTED for account {self.account_number}")
        
        # Start execution loop
        self.is_running = True
        self._execution_loop(check_interval)
        
        return True
    
    def stop_execution(self) -> None:
        """Stop execution and disconnect."""
        self.is_running = False
        if self.connection:
            self.connection.disconnect()
            logger.info(f"👥 SLAVE EXECUTION STOPPED for account {self.account_number}")
    
    def _connect(self) -> bool:
        """Connect to the slave account."""
        try:
            self.connection = BrokerConnection(f"slave_{self.account_number}", AccountRole.SLAVE, self.mt5_path)
            success = self.connection.connect(
                broker=self.broker,
                broker_server=self.broker_server,
                platform=self.platform,
                account_number=self.account_number,
                password=self.password
            )
            
            if success:
                logger.info(f"👥 Connected to slave account {self.account_number}")
                
                # Check if AutoTrading is enabled
                self._check_autotrading_status()
                
                # Signal that this slave is ready
                self._signal_ready()
                
                return True
            else:
                logger.error(f"Failed to connect to slave account {self.account_number}")
                return False
                
        except Exception as e:
            logger.error(f"Exception connecting to slave account: {e}")
            return False
    
    def _signal_ready(self) -> None:
        """Signal that this slave is ready and connected."""
        try:
            import os
            import tempfile
            
            temp_dir = tempfile.gettempdir()
            ready_dir = os.path.join(temp_dir, "copy_trade_ready")
            os.makedirs(ready_dir, exist_ok=True)
            
            ready_file = os.path.join(ready_dir, f"slave_{self.account_number}_ready.txt")
            with open(ready_file, 'w') as f:
                f.write(f"Slave {self.account_number} ready at {time.time()}")
            
            logger.info(f"👥 Slave {self.account_number} signaled ready")
            
        except Exception as e:
            logger.warning(f"Failed to signal ready: {e}")
    
    def _check_autotrading_status(self) -> None:
        """Check if AutoTrading is enabled and warn if not."""
        try:
            import MetaTrader5 as mt5
            
            terminal_info = mt5.terminal_info()
            if terminal_info:
                trade_allowed = terminal_info.trade_allowed
                if not trade_allowed:
                    logger.error("🚨 AUTOTRADING DISABLED! 🚨")
                    logger.error(f"Account {self.account_number} has AutoTrading disabled.")
                    logger.error("To enable AutoTrading:")
                    logger.error("1. Open MT5 and login to this account")
                    logger.error("2. Go to Tools → Options → Expert Advisors")
                    logger.error("3. Check 'Allow automated trading'")
                    logger.error("4. Click OK")
                    logger.error("Or click the AutoTrading button in MT5 toolbar (make it green)")
                else:
                    logger.info(f"✅ AutoTrading is enabled for account {self.account_number}")
            else:
                logger.warning("Could not check AutoTrading status")
                
        except Exception as e:
            logger.warning(f"Failed to check AutoTrading status: {e}")
    
    def _execution_loop(self, check_interval: float) -> None:
        """Main execution loop."""
        logger.info(f"👥 Starting execution loop with {check_interval}s interval")
        
        while self.is_running:
            try:
                self._process_signals()
                time.sleep(check_interval)
            except KeyboardInterrupt:
                logger.info("👥 Execution interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in execution loop: {e}")
                time.sleep(check_interval)  # Continue despite errors
        
        logger.info("👥 Execution loop ended")
    
    def _process_signals(self) -> None:
        """Process pending signals from master account."""
        try:
            # Get pending signals for our master account
            pending_signals = self.signal_broker.get_pending_signals(self.master_account)
            
            for signal in pending_signals:
                success = self._execute_signal(signal)
                if success:
                    # Mark signal as processed
                    self.signal_broker.mark_signal_processed(signal, self.account_number)
                else:
                    logger.error(f"Failed to execute signal {signal.signal_id}")
                    # For now, still mark as processed to avoid infinite retries
                    # In production, you might want retry logic here
                    self.signal_broker.mark_signal_processed(signal, self.account_number)
                    
        except Exception as e:
            logger.error(f"Error processing signals: {e}")
    
    def _execute_signal(self, signal: TradeSignal) -> bool:
        """
        Execute a trade signal.
        
        Args:
            signal: Trade signal to execute
            
        Returns:
            bool: True if execution successful
        """
        try:
            if signal.action == 'OPEN':
                return self._execute_open_trade(signal)
            elif signal.action == 'CLOSE':
                return self._execute_close_trade(signal)
            elif signal.action == 'MODIFY':
                return self._execute_modify_trade(signal)
            elif signal.action == 'PENDING_ORDER':
                return self._execute_pending_order(signal)
            elif signal.action == 'ORDER_REMOVED':
                return self._execute_order_removal(signal)
            else:
                logger.warning(f"Unknown signal action: {signal.action}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing signal {signal.signal_id}: {e}")
            return False
    
    def _execute_open_trade(self, signal: TradeSignal) -> bool:
        """Execute an open trade signal."""
        try:
            # Ensure symbol is selected in Market Watch
            import MetaTrader5 as mt5
            if not mt5.symbol_select(signal.symbol, True):
                logger.warning(f"Failed to select symbol {signal.symbol} in Market Watch")
            
            # Calculate volume with scaling
            scaled_volume = signal.volume * self.volume_scale
            scaled_volume = round(scaled_volume, 2)  # Round to 2 decimal places
            
            # Prepare trade request
            trade_type = mt5.ORDER_TYPE_BUY if signal.trade_type == 0 else mt5.ORDER_TYPE_SELL
            
            request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'symbol': signal.symbol,
                'volume': scaled_volume,
                'type': trade_type,
                'deviation': 20,  # Price deviation in points
                'magic': 123456,  # Magic number for identification
                'comment': f'Copy-{signal.master_account}',
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_IOC,
            }
            
            # Execute trade
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"❌ Trade execution failed: {mt5.last_error()}")
                return False
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ Trade failed with retcode: {result.retcode}")
                return False
            
            # Track this position
            self.open_positions[signal.ticket] = {
                'slave_ticket': result.order,
                'signal': signal,
                'execution_time': datetime.now().isoformat()
            }
            
            pos_type = "BUY" if signal.trade_type == 0 else "SELL"
            logger.info(f"✅ TRADE EXECUTED: {signal.symbol} {pos_type} {scaled_volume} "
                       f"(Master: {signal.ticket} → Slave: {result.order})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing open trade: {e}")
            return False
    
    def _execute_close_trade(self, signal: TradeSignal) -> bool:
        """Execute a close trade signal."""
        try:
            # Find the corresponding slave position
            if signal.ticket not in self.open_positions:
                logger.warning(f"No corresponding slave position found for master ticket {signal.ticket}")
                return False
            
            slave_info = self.open_positions[signal.ticket]
            slave_ticket = slave_info['slave_ticket']
            
            # Get position info
            positions = mt5.positions_get(ticket=slave_ticket)
            if not positions:
                logger.warning(f"Slave position {slave_ticket} not found (already closed?)")
                # Remove from tracking
                del self.open_positions[signal.ticket]
                return True
            
            position = positions[0]
            
            # Prepare close request
            close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            
            request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'symbol': position.symbol,
                'volume': position.volume,
                'type': close_type,
                'position': slave_ticket,
                'deviation': 20,
                'magic': 123456,
                'comment': f'Close copy from master {signal.master_account}',
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_IOC,
            }
            
            # Execute close
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"❌ Close trade failed: {mt5.last_error()}")
                return False
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ Close failed with retcode: {result.retcode}")
                return False
            
            # Remove from tracking
            del self.open_positions[signal.ticket]
            
            logger.info(f"✅ TRADE CLOSED: {signal.symbol} (Master: {signal.ticket} → Slave: {slave_ticket})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing close trade: {e}")
            return False
    
    def _execute_modify_trade(self, signal: TradeSignal) -> bool:
        """Execute a modify trade signal (placeholder for future implementation)."""
        logger.warning("Trade modification not yet implemented")
        return False

    def _execute_pending_order(self, signal: TradeSignal) -> bool:
        """Execute a pending order signal."""
        try:
            # Ensure symbol is selected in Market Watch
            import MetaTrader5 as mt5
            if not mt5.symbol_select(signal.symbol, True):
                logger.warning(f"Failed to select symbol {signal.symbol} in Market Watch")
            
            # Calculate volume with scaling
            scaled_volume = signal.volume * self.volume_scale
            scaled_volume = round(scaled_volume, 2)
            
            # Map order types
            order_type_map = {
                2: mt5.ORDER_TYPE_BUY_LIMIT,   # BUY_LIMIT
                3: mt5.ORDER_TYPE_SELL_LIMIT,  # SELL_LIMIT
                4: mt5.ORDER_TYPE_BUY_STOP,    # BUY_STOP
                5: mt5.ORDER_TYPE_SELL_STOP,   # SELL_STOP
                6: mt5.ORDER_TYPE_BUY_STOP_LIMIT,   # BUY_STOP_LIMIT
                7: mt5.ORDER_TYPE_SELL_STOP_LIMIT   # SELL_STOP_LIMIT
            }
            
            order_type = order_type_map.get(signal.trade_type)
            if order_type is None:
                logger.error(f"Unsupported pending order type: {signal.trade_type}")
                return False
            
            # Prepare pending order request
            request = {
                'action': mt5.TRADE_ACTION_PENDING,
                'symbol': signal.symbol,
                'volume': scaled_volume,
                'type': order_type,
                'price': signal.price,
                'deviation': 20,
                'magic': 123456,
                'comment': f'Copy-{signal.master_account}',
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_IOC,
            }
            
            # Execute pending order
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"❌ Pending order failed: {mt5.last_error()}")
                return False
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"❌ Pending order failed with retcode: {result.retcode}"
                if hasattr(result, 'comment'):
                    error_msg += f" - {result.comment}"
                logger.error(error_msg)
                logger.debug(f"Request was: {request}")
                return False
            
            # Track this pending order
            self.open_positions[signal.ticket] = {
                'slave_ticket': result.order,
                'signal': signal,
                'execution_time': datetime.now().isoformat(),
                'type': 'pending_order'
            }
            
            order_type_str = self._get_order_type_str(signal.trade_type)
            logger.info(f"✅ PENDING ORDER PLACED: {signal.symbol} {order_type_str} {scaled_volume} @ {signal.price} "
                       f"(Master: {signal.ticket} → Slave: {result.order})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing pending order: {e}")
            return False
    
    def _execute_order_removal(self, signal: TradeSignal) -> bool:
        """Execute order removal (cancel pending order)."""
        try:
            # Find the corresponding slave order
            if signal.ticket not in self.open_positions:
                logger.warning(f"No corresponding slave order found for master ticket {signal.ticket}")
                return False
            
            slave_info = self.open_positions[signal.ticket]
            
            # Only cancel if it's a pending order
            if slave_info.get('type') != 'pending_order':
                logger.info(f"Order {signal.ticket} was not a pending order, skipping cancellation")
                return True
            
            slave_ticket = slave_info['slave_ticket']
            
            # Prepare cancel request
            request = {
                'action': mt5.TRADE_ACTION_REMOVE,
                'order': slave_ticket,
                'comment': f'Cancel copy from master {signal.master_account}',
            }
            
            # Cancel the order
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"❌ Order cancellation failed: {mt5.last_error()}")
                return False
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ Order cancellation failed with retcode: {result.retcode}")
                return False
            
            # Remove from tracking
            del self.open_positions[signal.ticket]
            
            logger.info(f"✅ PENDING ORDER CANCELLED: {signal.symbol} (Master: {signal.ticket} → Slave: {slave_ticket})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
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


def run_slave_executor(broker: str,
                      broker_server: str,
                      platform: str,
                      account_number: int,
                      password: str,
                      master_account: int,
                      check_interval: float = 0.5,
                      signal_broker_type: str = 'file',
                      volume_scale: float = 1.0,
                      mt5_path: str = None) -> None:
    """
    Run slave executor in a separate process.
    
    Args:
        broker: Broker name
        broker_server: Broker server
        platform: Trading platform
        account_number: Slave account number
        password: Slave account password
        master_account: Master account number to follow
        check_interval: Time between signal checks in seconds
        signal_broker_type: Type of signal broker ('file' or 'queue')
        volume_scale: Volume scaling factor
        mt5_path: Path to specific MT5 installation
    """
    logger.info(f"👥 SLAVE EXECUTOR PROCESS STARTED for account {account_number} following master {master_account}" +
               (f" with MT5 path: {mt5_path}" if mt5_path else ""))
    
    try:
        executor = SlaveExecutor(
            broker=broker,
            broker_server=broker_server,
            platform=platform,
            account_number=account_number,
            password=password,
            master_account=master_account,
            signal_broker_type=signal_broker_type,
            volume_scale=volume_scale,
            mt5_path=mt5_path
        )
        
        # Start execution (blocking call)
        executor.start_execution(check_interval)
        
    except KeyboardInterrupt:
        logger.info("👥 Slave executor interrupted by user")
    except Exception as e:
        logger.error(f"👥 Slave executor error: {e}")
    finally:
        logger.info(f"👥 SLAVE EXECUTOR PROCESS ENDED for account {account_number}")


if __name__ == "__main__":
    # For testing - can be run directly
    import sys
    
    if len(sys.argv) < 7:
        print("Usage: python slave_executor.py <broker> <server> <platform> <account> <password> <master_account> [check_interval] [volume_scale]")
        sys.exit(1)
    
    broker = sys.argv[1]
    broker_server = sys.argv[2]
    platform = sys.argv[3]
    account_number = int(sys.argv[4])
    password = sys.argv[5]
    master_account = int(sys.argv[6])
    check_interval = float(sys.argv[7]) if len(sys.argv) > 7 else 0.5
    volume_scale = float(sys.argv[8]) if len(sys.argv) > 8 else 1.0
    
    run_slave_executor(broker, broker_server, platform, account_number, password, master_account, check_interval, 'file', volume_scale) 