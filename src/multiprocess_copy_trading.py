"""
Multi-process copy trading orchestrator.
Manages separate processes for master monitoring and slave execution.
"""
import os
import sys
import time
import logging
import signal
from typing import Dict, List, Optional, Tuple
from multiprocessing import Process

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.master_monitor import run_master_monitor
from src.slave_executor import run_slave_executor
from src.signal_broker import get_signal_broker

logger = logging.getLogger(__name__)


class CopyTradingOrchestrator:
    """Orchestrates multi-process copy trading system."""
    
    def __init__(self, signal_broker_type: str = 'file'):
        """
        Initialize the orchestrator.
        
        Args:
            signal_broker_type: Type of signal broker ('file' or 'queue')
        """
        self.signal_broker_type = signal_broker_type
        self.signal_broker = get_signal_broker(signal_broker_type)
        
        # Process management
        self.master_process: Optional[Process] = None
        self.slave_processes: List[Process] = []
        self.master_account_info: Optional[Dict] = None
        self.slave_accounts_info: List[Dict] = []
        
        # Configuration
        self.broker = None
        self.broker_server = None
        self.platform = None
        self.check_interval = 1.0
        
        logger.info(f"Copy trading orchestrator initialized with {signal_broker_type} signal broker")
    
    def configure(self, 
                  broker: str,
                  broker_server: str,
                  platform: str,
                  check_interval: float = 1.0) -> None:
        """
        Configure connection settings.
        
        Args:
            broker: Broker name
            broker_server: Broker server
            platform: Trading platform
            check_interval: Time between checks in seconds
        """
        self.broker = broker
        self.broker_server = broker_server
        self.platform = platform
        self.check_interval = check_interval
        
        logger.info(f"Orchestrator configured for {broker} on {broker_server}")
    
    def add_master_account(self, 
                          account_number: int,
                          password: str,
                          mt5_path: str = None) -> bool:
        """
        Add master account configuration.
        
        Args:
            account_number: Master account number
            password: Master account password
            mt5_path: Path to specific MT5 installation
            
        Returns:
            bool: True if added successfully
        """
        if self.master_account_info is not None:
            logger.error("Master account already configured")
            return False
        
        self.master_account_info = {
            'account_number': account_number,
            'password': password,
            'mt5_path': mt5_path
        }
        
        logger.info(f"Master account {account_number} configured" + 
                   (f" with MT5 path: {mt5_path}" if mt5_path else ""))
        return True
    
    def add_slave_account(self,
                         account_number: int,
                         password: str,
                         volume_scale: float = 1.0,
                         mt5_path: str = None) -> bool:
        """
        Add slave account configuration.
        
        Args:
            account_number: Slave account number
            password: Slave account password
            volume_scale: Volume scaling factor
            mt5_path: Path to specific MT5 installation
            
        Returns:
            bool: True if added successfully
        """
        slave_info = {
            'account_number': account_number,
            'password': password,
            'volume_scale': volume_scale,
            'mt5_path': mt5_path
        }
        
        self.slave_accounts_info.append(slave_info)
        
        logger.info(f"Slave account {account_number} configured with {volume_scale}x volume scaling" +
                   (f" and MT5 path: {mt5_path}" if mt5_path else ""))
        return True
    
    def start_copy_trading(self) -> bool:
        """
        Start the multi-process copy trading system.
        
        Returns:
            bool: True if started successfully
        """
        if not self._validate_configuration():
            return False
        
        logger.info("🚀 STARTING MULTI-PROCESS COPY TRADING SYSTEM")
        
        # Start slave executor processes FIRST (so they're ready to receive signals)
        started_slaves = self._start_slave_processes()
        if started_slaves == 0:
            logger.error("Failed to start any slave processes")
            return False
        
        # Wait for all slaves to be connected and ready
        logger.info("⏳ Waiting for all slaves to connect...")
        if not self._wait_for_slaves_ready():
            logger.error("Slaves failed to connect within timeout")
            self.stop_copy_trading()
            return False
        
        logger.info("✅ All slaves connected and ready")
        
        # Start master monitor process LAST (so it doesn't send signals before slaves are ready)
        if not self._start_master_process():
            logger.error("Failed to start master process")
            self.stop_copy_trading()
            return False
        
        logger.info(f"✅ Copy trading system started: 1 master + {started_slaves} slaves")
        return True
    
    def stop_copy_trading(self) -> None:
        """Stop all copy trading processes."""
        logger.info("🛑 STOPPING COPY TRADING SYSTEM")
        
        # Stop all slave processes
        for i, process in enumerate(self.slave_processes):
            if process.is_alive():
                logger.info(f"Stopping slave process {i+1}...")
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    logger.warning(f"Force killing slave process {i+1}")
                    process.kill()
                    process.join()
        
        # Stop master process
        if self.master_process and self.master_process.is_alive():
            logger.info("Stopping master process...")
            self.master_process.terminate()
            self.master_process.join(timeout=5)
            if self.master_process.is_alive():
                logger.warning("Force killing master process")
                self.master_process.kill()
                self.master_process.join()
        
        # Clear process lists
        self.master_process = None
        self.slave_processes.clear()
        
        logger.info("✅ All copy trading processes stopped")
    
    def is_running(self) -> bool:
        """Check if the copy trading system is running."""
        master_running = self.master_process and self.master_process.is_alive()
        slaves_running = sum(1 for p in self.slave_processes if p.is_alive())
        
        return master_running and slaves_running > 0
    
    def get_status(self) -> Dict:
        """Get status of the copy trading system."""
        master_running = self.master_process and self.master_process.is_alive()
        slaves_running = [p.is_alive() for p in self.slave_processes]
        
        return {
            'master_running': master_running,
            'slaves_running': sum(slaves_running),
            'total_slaves': len(self.slave_processes),
            'slave_statuses': slaves_running,
            'signal_broker_type': self.signal_broker_type,
            'configured_accounts': {
                'master': self.master_account_info['account_number'] if self.master_account_info else None,
                'slaves': [s['account_number'] for s in self.slave_accounts_info]
            }
        }
    
    def wait_for_interruption(self) -> None:
        """Wait for user interruption and handle graceful shutdown."""
        try:
            logger.info("Copy trading system running. Press Ctrl+C to stop.")
            
            while self.is_running():
                time.sleep(1)
                
                # Check if any processes died unexpectedly
                if self.master_process and not self.master_process.is_alive():
                    logger.error("Master process died unexpectedly")
                    break
                
                dead_slaves = [i for i, p in enumerate(self.slave_processes) if not p.is_alive()]
                if dead_slaves:
                    logger.error(f"Slave processes died unexpectedly: {dead_slaves}")
                    break
                    
        except KeyboardInterrupt:
            logger.info("User interrupted. Stopping copy trading system...")
        finally:
            self.stop_copy_trading()
    
    def _validate_configuration(self) -> bool:
        """Validate that the system is properly configured."""
        if not all([self.broker, self.broker_server, self.platform]):
            logger.error("Broker configuration missing")
            return False
        
        if self.master_account_info is None:
            logger.error("Master account not configured")
            return False
        
        if len(self.slave_accounts_info) == 0:
            logger.error("No slave accounts configured")
            return False
        
        return True
    
    def _start_master_process(self) -> bool:
        """Start the master monitor process."""
        try:
            logger.info("Starting master monitor process...")
            
            self.master_process = Process(
                target=run_master_monitor,
                args=(
                    self.broker,
                    self.broker_server,
                    self.platform,
                    self.master_account_info['account_number'],
                    self.master_account_info['password'],
                    self.check_interval,
                    self.signal_broker_type,
                    self.master_account_info.get('mt5_path')
                ),
                name=f"MasterMonitor-{self.master_account_info['account_number']}"
            )
            
            self.master_process.start()
            
            # Give it a moment to start
            time.sleep(2)
            
            if self.master_process.is_alive():
                logger.info(f"✅ Master process started (PID: {self.master_process.pid})")
                return True
            else:
                logger.error("Master process failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Error starting master process: {e}")
            return False
    
    def _start_slave_processes(self) -> int:
        """Start slave executor processes."""
        started_count = 0
        
        for i, slave_info in enumerate(self.slave_accounts_info):
            try:
                logger.info(f"Starting slave executor {i+1}/{len(self.slave_accounts_info)}...")
                
                process = Process(
                    target=run_slave_executor,
                    args=(
                        self.broker,
                        self.broker_server,
                        self.platform,
                        slave_info['account_number'],
                        slave_info['password'],
                        self.master_account_info['account_number'],
                        self.check_interval / 2,  # Slaves check more frequently
                        self.signal_broker_type,
                        slave_info['volume_scale'],
                        slave_info.get('mt5_path')
                    ),
                    name=f"SlaveExecutor-{slave_info['account_number']}"
                )
                
                process.start()
                self.slave_processes.append(process)
                
                # Give it a moment to start
                time.sleep(1)
                
                if process.is_alive():
                    logger.info(f"✅ Slave process {i+1} started (PID: {process.pid})")
                    started_count += 1
                else:
                    logger.error(f"Slave process {i+1} failed to start")
                    
            except Exception as e:
                logger.error(f"Error starting slave process {i+1}: {e}")
        
        return started_count
    
    def _wait_for_slaves_ready(self, timeout: int = 30) -> bool:
        """
        Wait for all slave processes to signal they are connected and ready.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if all slaves are ready, False if timeout
        """
        import os
        import tempfile
        
        # Create ready signal directory
        temp_dir = tempfile.gettempdir()
        ready_dir = os.path.join(temp_dir, "copy_trade_ready")
        os.makedirs(ready_dir, exist_ok=True)
        
        expected_slaves = len(self.slave_accounts_info)
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check for ready signals from all slaves
            ready_count = 0
            for slave_info in self.slave_accounts_info:
                ready_file = os.path.join(ready_dir, f"slave_{slave_info['account_number']}_ready.txt")
                if os.path.exists(ready_file):
                    ready_count += 1
            
            if ready_count >= expected_slaves:
                logger.info(f"All {expected_slaves} slaves are ready!")
                # Clean up ready files
                for slave_info in self.slave_accounts_info:
                    ready_file = os.path.join(ready_dir, f"slave_{slave_info['account_number']}_ready.txt")
                    try:
                        os.remove(ready_file)
                    except:
                        pass
                return True
            
            logger.debug(f"Waiting for slaves: {ready_count}/{expected_slaves} ready")
            time.sleep(0.5)
        
        logger.error(f"Timeout waiting for slaves. Only {ready_count}/{expected_slaves} ready")
        return False
    
    def cleanup_signal_files(self) -> None:
        """Clean up old signal files."""
        if self.signal_broker_type == 'file':
            try:
                self.signal_broker.cleanup_old_signals()
                logger.info("Signal files cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up signal files: {e}")
    
    def __del__(self):
        """Cleanup on destruction."""
        if hasattr(self, 'master_process') or hasattr(self, 'slave_processes'):
            self.stop_copy_trading() 