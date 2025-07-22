# Copy Trade

A Python application for automated copy trading using MetaTrader 5 (MT5). This application connects to trading accounts headlessly and implements **master/slave copy trading** functionality. **Now with full copy trading support!**

## Features

- ✅ **Headless MT5 Connection** - Connects to MetaTrader 5 without opening the GUI
- ✅ **Multi-Broker Support** - Currently supports FundedNext with easy extensibility
- ✅ **Master/Slave Copy Trading** - Automatically copy trades from master to slave accounts
- ✅ **Multiple Account Connections** - Connect to multiple accounts with the same broker/server
- ✅ **Real-time Trade Monitoring** - Monitor master account for new trades with configurable intervals
- ✅ **Configuration-Based** - All connection settings and roles via config files
- ✅ **Robust Error Handling** - Comprehensive logging and error management
- ✅ **Account Management** - Real-time account information and balance monitoring
- ✅ **Thread-safe Operations** - Safe concurrent management of multiple connections

## Prerequisites

- **Python 3.8+**
- **MetaTrader 5** installed and configured
- **Trading account(s)** with API access enabled
- **Algorithm trading enabled** in MT5 settings

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd copy-trade
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure MT5 for API access:**
   - Open MetaTrader 5
   - Go to Tools → Options → Expert Advisors
   - Enable "Allow algorithmic trading"
   - Enable "Allow DLL imports"
   - Apply settings and restart MT5

## Configuration

### Master/Slave Copy Trading (Recommended)

1. **Copy the example configuration:**
   ```bash
   cp config.ini.example config.ini
   ```

2. **Edit `config.ini` with your master and slave account details:**
   ```ini
   [Connection]
   # All accounts will use the same broker and server
   broker = FundedNext
   server = FundedNext-Server 2
   platform = MT5

   [CopyTrade]
   # Enable copy trading functionality
   enabled = true
   # Time interval between trade checks (in seconds)
   check_interval = 1.0

   [Account1]
   account = YOUR_MASTER_ACCOUNT_NUMBER
   password = YOUR_MASTER_PASSWORD
   role = master  # This account will be monitored for trades

   [Account2]
   account = YOUR_FIRST_SLAVE_ACCOUNT_NUMBER
   password = YOUR_FIRST_SLAVE_PASSWORD
   role = slave   # Trades will be copied to this account

   [Account3]
   account = YOUR_SECOND_SLAVE_ACCOUNT_NUMBER
   password = YOUR_SECOND_SLAVE_PASSWORD
   role = slave   # Trades will be copied to this account

   # Add more slave accounts as needed
   # password =  # Will prompt if not provided

   [Logging]
   level = INFO
   ```

   **Important Notes:**
   - You must have **exactly one** master account (`role = master`)
   - You must have **at least one** slave account (`role = slave`) 
   - All accounts must use the same broker and server

### Single Account (Legacy Mode)

For backward compatibility, you can still use the old single account configuration:

```ini
[Connection]
broker = FundedNext
server = FundedNext-Server 2
platform = MT5
account = YOUR_ACCOUNT_NUMBER
password = YOUR_PASSWORD
```

## Usage

### Master/Slave Copy Trading

```bash
# Start copy trading with master/slave accounts
python main.py --config config.ini

# Enable verbose logging for debugging
python main.py --config config.ini --verbose

# Connect to accounts without starting copy trading
python main.py --config config.ini --no-copy

# Interactive copy trading example
python src/copy_trade_example.py
```

### Single Account (Legacy)

```bash
# Use configuration file (legacy format)
python main.py --config config.ini

# Command line arguments
python main.py --broker FundedNext --server "FundedNext-Server 2" --account 123456

# No config file (will prompt for details)
python main.py
```

### Example Output - Copy Trading

```
2025-01-XX XX:XX:XX - INFO - Copy trading configuration: 1 master, 2 slaves
2025-01-XX XX:XX:XX - INFO - Connecting to account1 (master) (account 12345678)...
2025-01-XX XX:XX:XX - INFO - [account1] (master) Attempting to connect to FundedNext (FundedNext-Server 2) account 12345678
2025-01-XX XX:XX:XX - INFO - [account1] (master) Successfully connected to account 12345678
2025-01-XX XX:XX:XX - INFO - Added MASTER connection account1 successfully
2025-01-XX XX:XX:XX - INFO - Connecting to account2 (slave) (account 87654321)...
2025-01-XX XX:XX:XX - INFO - [account2] (slave) Successfully connected to account 87654321
2025-01-XX XX:XX:XX - INFO - Added SLAVE connection account2 successfully
2025-01-XX XX:XX:XX - INFO - Successfully connected to 2 out of 2 accounts
2025-01-XX XX:XX:XX - INFO - [account1] (MASTER) Account 12345678 on FundedNext-Server 2 - Balance: 15100.45 USD
2025-01-XX XX:XX:XX - INFO - [account2] (SLAVE) Account 87654321 on FundedNext-Server 2 - Balance: 25250.78 USD
2025-01-XX XX:XX:XX - INFO - Copy trade engine started monitoring
2025-01-XX XX:XX:XX - INFO - Copy trading started with 1.0s check interval
2025-01-XX XX:XX:XX - INFO - Copy trading active. Press Ctrl+C to stop and disconnect.
```

## Project Structure

```
copy-trade/
├── src/
│   ├── broker_connection.py       # Core MT5 connection management
│   ├── signal_broker.py           # Inter-process communication for trade signals
│   ├── master_monitor.py          # Master account monitoring process
│   ├── slave_executor.py          # Slave account trade execution process
│   ├── multiprocess_copy_trading.py # Multi-process orchestrator
│   └── mt5_instance_manager.py    # MT5 instance management (optional)
├── main.py                        # Application entry point (multi-process copy trading)
├── config.ini.example             # Configuration template (master/slave setup)
├── requirements.txt               # Python dependencies
├── DEVELOPMENT.md                 # Development notes and roadmap
└── README.md                      # This file
```

## Multi-Process Copy Trading Architecture

### Core Components

The system uses a **multi-process architecture** to overcome MT5's single-connection limitation:

- **Master Monitor Process** - Dedicated process for monitoring master account trades
- **Slave Executor Processes** - Separate processes for each slave account execution
- **Signal Broker** - Inter-process communication for trade signals (file-based or queue-based)
- **Copy Trading Orchestrator** - Manages and coordinates all processes

### Key Features

- **True Isolation** - Each account runs in its own process with dedicated MT5 connection
- **Slaves-First Connection** - Slaves connect first, then master starts monitoring
- **AutoTrading Detection** - Automatic detection and warnings for disabled AutoTrading
- **Symbol Management** - Automatic symbol selection for market data access
- **Volume Scaling** - Configurable volume scaling for slave accounts
- **Graceful Shutdown** - Clean termination of all processes

### Usage

```bash
# Start multi-process copy trading
python main.py --config config.ini

# Enable automatic MT5 instance setup (creates separate MT5 installations)
python main.py --config config.ini --auto-setup-mt5

# Use queue-based signal broker instead of files
python main.py --config config.ini --signal-broker queue

# Enable verbose logging
python main.py --config config.ini --verbose
```

## Supported Brokers

| Broker | Status | Server Examples |
|--------|--------|----------------|
| FundedNext | ✅ Working | `FundedNext-Server 2`, `FundedNext-Live2` |
| Others | 🚧 Planned | Easy to add via configuration |

## Development Status

### ✅ Completed Features

1. **Multi-Process Copy Trading**
   - Dedicated processes for master monitoring and slave execution
   - True MT5 connection isolation per account
   - Inter-process communication via signal broker
   - Slaves-first connection coordination

2. **Real-Time Trade Detection**
   - Market orders (open/close) detection and copying
   - Pending orders (all types) detection and copying
   - Symbol selection for market data access
   - Volume scaling with configurable ratios

3. **Robust Error Handling**
   - AutoTrading detection with clear instructions
   - Connection failure recovery
   - Process lifecycle management
   - Graceful shutdown with cleanup

4. **Configuration System**
   - INI-based configuration with master/slave role definitions
   - Copy trading settings (enabled/disabled, check intervals)
   - Command-line argument support with copy trading options
   - Backward compatibility with single account mode

5. **Logging & Monitoring**
   - Comprehensive logging system with connection IDs and roles
   - Real-time account balance monitoring
   - Copy trading status and engine monitoring
   - Deal processing tracking and duplicate prevention

### 🚧 In Progress

1. **Trade Execution Logic**
   - Actual trade replication implementation (currently logs only)
   - Order type conversion and execution
   - Volume scaling based on account sizes

### 📋 Planned Features

1. **Advanced Copy Trading**
   - Proportional scaling based on account balance ratios
   - Selective trade copying with symbol filters
   - Risk management rules (max trades, drawdown limits)
   - Stop-loss and take-profit copying

2. **Enhanced Trade Management**
   - Position modification copying (SL/TP changes)
   - Partial close operations
   - Order management (pending orders, modifications)

3. **Monitoring & Analytics**
   - Real-time monitoring dashboard
   - Trade performance analytics
   - Account synchronization status
   - Historical copy trading statistics

4. **Notifications & Alerts**
   - Email/SMS alerts for copy trading events
   - Trade execution notifications
   - Error and connection status updates
   - Performance reports

## Troubleshooting

### Multiple Account Issues

1. **Some Accounts Fail to Connect**
   - Check individual account credentials
   - Verify all accounts use the same broker/server
   - Review logs for specific error messages per account

2. **MT5 Resource Limits**
   - MT5 may limit concurrent connections
   - Consider connecting accounts sequentially if needed
   - Monitor system resources (CPU, memory)

### Common Issues

1. **IPC Timeout Errors**
   - Ensure MT5 is closed completely before running
   - Check that algorithmic trading is enabled in MT5
   - Verify account credentials are correct

2. **Connection Failures**
   - Confirm server name matches your broker exactly
   - Check network connectivity
   - Verify account has API access enabled

3. **Permission Errors**
   - Run as administrator if needed
   - Check antivirus/firewall settings
   - Ensure MT5 installation is complete

### Getting Help

1. Check the logs for detailed error messages (includes connection IDs)
2. Verify MT5 settings and account status for all accounts
3. Test manual login to MT5 first
4. Review the troubleshooting section in DEVELOPMENT.md

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes. Use at your own risk. Always test thoroughly before using with real trading accounts. The developers are not responsible for any financial losses.
