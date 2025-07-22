"""
Signal broker for inter-process communication in copy trading system.
Handles communication between master monitor and slave executors.
"""
import json
import os
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from queue import Queue, Empty
from multiprocessing import Manager
import tempfile

logger = logging.getLogger(__name__)


class TradeSignal:
    """Represents a trade signal to be copied."""
    
    def __init__(self, 
                 master_account: int,
                 action: str,
                 symbol: str,
                 trade_type: int,
                 volume: float,
                 price: float = 0.0,
                 ticket: int = 0,
                 timestamp: str = None):
        self.master_account = master_account
        self.action = action  # 'OPEN', 'CLOSE', 'MODIFY'
        self.symbol = symbol
        self.trade_type = trade_type  # 0=BUY, 1=SELL
        self.volume = volume
        self.price = price
        self.ticket = ticket
        self.timestamp = timestamp or datetime.now().isoformat()
        self.signal_id = f"{master_account}_{ticket}_{int(time.time())}"
    
    def to_dict(self) -> Dict:
        """Convert signal to dictionary for serialization."""
        return {
            'signal_id': self.signal_id,
            'master_account': self.master_account,
            'action': self.action,
            'symbol': self.symbol,
            'trade_type': self.trade_type,
            'volume': self.volume,
            'price': self.price,
            'ticket': self.ticket,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradeSignal':
        """Create signal from dictionary."""
        signal = cls(
            master_account=data['master_account'],
            action=data['action'],
            symbol=data['symbol'],
            trade_type=data['trade_type'],
            volume=data['volume'],
            price=data.get('price', 0.0),
            ticket=data.get('ticket', 0),
            timestamp=data.get('timestamp')
        )
        signal.signal_id = data.get('signal_id', signal.signal_id)
        return signal


class FileBasedSignalBroker:
    """File-based signal broker for inter-process communication."""
    
    def __init__(self, signals_dir: str = None):
        """Initialize file-based signal broker."""
        if signals_dir is None:
            # Create temp directory for signals
            self.signals_dir = os.path.join(tempfile.gettempdir(), 'copy_trade_signals')
        else:
            self.signals_dir = signals_dir
        
        # Create signals directory if it doesn't exist
        os.makedirs(self.signals_dir, exist_ok=True)
        os.makedirs(os.path.join(self.signals_dir, 'pending'), exist_ok=True)
        os.makedirs(os.path.join(self.signals_dir, 'processed'), exist_ok=True)
        
        logger.info(f"Signal broker using directory: {self.signals_dir}")
    
    def send_signal(self, signal: TradeSignal) -> bool:
        """Send a signal to all slave processes."""
        try:
            signal_file = os.path.join(self.signals_dir, 'pending', f"{signal.signal_id}.json")
            with open(signal_file, 'w') as f:
                json.dump(signal.to_dict(), f, indent=2)
            
            logger.info(f"📡 SIGNAL SENT: {signal.action} {signal.symbol} {signal.volume} (ID: {signal.signal_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to send signal: {e}")
            return False
    
    def get_pending_signals(self, master_account: int) -> List[TradeSignal]:
        """Get all pending signals for a specific master account."""
        signals = []
        pending_dir = os.path.join(self.signals_dir, 'pending')
        
        try:
            for filename in os.listdir(pending_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(pending_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        
                        # Check if this signal is for the specified master account
                        if data.get('master_account') == master_account:
                            signal = TradeSignal.from_dict(data)
                            signals.append(signal)
                    except Exception as e:
                        logger.error(f"Error reading signal file {filename}: {e}")
                        # Remove corrupted file
                        try:
                            os.remove(filepath)
                        except:
                            pass
        except Exception as e:
            logger.error(f"Error scanning pending signals: {e}")
        
        return signals
    
    def mark_signal_processed(self, signal: TradeSignal, slave_account: int) -> bool:
        """Mark a signal as processed by a slave account."""
        try:
            # Move signal from pending to processed
            pending_file = os.path.join(self.signals_dir, 'pending', f"{signal.signal_id}.json")
            processed_file = os.path.join(self.signals_dir, 'processed', f"{signal.signal_id}_{slave_account}.json")
            
            if os.path.exists(pending_file):
                # Add processing info
                data = signal.to_dict()
                data['processed_by'] = slave_account
                data['processed_at'] = datetime.now().isoformat()
                
                with open(processed_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Remove from pending only after successful processing
                os.remove(pending_file)
                
                logger.info(f"✅ SIGNAL PROCESSED: {signal.signal_id} by account {slave_account}")
                return True
        except Exception as e:
            logger.error(f"Failed to mark signal as processed: {e}")
        
        return False
    
    def cleanup_old_signals(self, max_age_hours: int = 24) -> None:
        """Clean up old processed signals."""
        try:
            cutoff_time = time.time() - (max_age_hours * 3600)
            processed_dir = os.path.join(self.signals_dir, 'processed')
            
            for filename in os.listdir(processed_dir):
                filepath = os.path.join(processed_dir, filename)
                if os.path.getmtime(filepath) < cutoff_time:
                    os.remove(filepath)
                    logger.debug(f"Cleaned up old signal: {filename}")
        except Exception as e:
            logger.error(f"Error cleaning up old signals: {e}")


class QueueBasedSignalBroker:
    """Queue-based signal broker using multiprocessing Manager."""
    
    def __init__(self):
        """Initialize queue-based signal broker."""
        self.manager = Manager()
        self.signal_queue = self.manager.Queue()
        self.processed_signals = self.manager.dict()
        logger.info("Queue-based signal broker initialized")
    
    def send_signal(self, signal: TradeSignal) -> bool:
        """Send a signal to the queue."""
        try:
            self.signal_queue.put(signal.to_dict())
            logger.info(f"📡 SIGNAL QUEUED: {signal.action} {signal.symbol} {signal.volume} (ID: {signal.signal_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to queue signal: {e}")
            return False
    
    def get_pending_signals(self, master_account: int, timeout: float = 1.0) -> List[TradeSignal]:
        """Get pending signals from queue (non-blocking with timeout)."""
        signals = []
        end_time = time.time() + timeout
        
        while time.time() < end_time:
            try:
                data = self.signal_queue.get(timeout=0.1)
                if data.get('master_account') == master_account:
                    signal = TradeSignal.from_dict(data)
                    signals.append(signal)
                else:
                    # Put back signal for other master accounts
                    self.signal_queue.put(data)
            except:
                break  # No more signals or timeout
        
        return signals
    
    def mark_signal_processed(self, signal: TradeSignal, slave_account: int) -> bool:
        """Mark signal as processed."""
        try:
            key = f"{signal.signal_id}_{slave_account}"
            self.processed_signals[key] = {
                'signal_id': signal.signal_id,
                'slave_account': slave_account,
                'processed_at': datetime.now().isoformat()
            }
            logger.info(f"✅ SIGNAL PROCESSED: {signal.signal_id} by account {slave_account}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark signal as processed: {e}")
            return False


# Default broker instance
default_broker = FileBasedSignalBroker()


def get_signal_broker(broker_type: str = 'file') -> Any:
    """Get a signal broker instance."""
    if broker_type == 'file':
        return FileBasedSignalBroker()
    elif broker_type == 'queue':
        return QueueBasedSignalBroker()
    else:
        raise ValueError(f"Unknown broker type: {broker_type}") 