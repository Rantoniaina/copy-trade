# Copy Trade

A Python application for automated copy trading using MetaTrader 5 (MT5). This application connects to trading accounts headlessly and provides the foundation for implementing copy trading strategies. **Now supports multiple broker connections simultaneously!**

## Features

- ✅ **Headless MT5 Connection** - Connects to MetaTrader 5 without opening the GUI
- ✅ **Multi-Broker Support** - Currently supports FundedNext with easy extensibility
- ✅ **Multiple Account Connections** - Connect to multiple accounts with the same broker/server
- ✅ **Configuration-Based** - All connection settings via config files
- ✅ **Robust Error Handling** - Comprehensive logging and error management
- ✅ **Account Management** - Real-time account information and balance monitoring
- 🚧 **Copy Trading Logic** - Foundation ready, implementation in progress

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

### Multiple Accounts (Recommended)

1. **Copy the example configuration:**
   ```bash
   cp config.ini.example config.ini
   ```

2. **Edit `config.ini` with your account details:**
   ```ini
   [Connection]
   # All accounts will use the same broker and server
   broker = FundedNext
   server = FundedNext-Server 2
   platform = MT5

   [Account1]
   account = YOUR_FIRST_ACCOUNT_NUMBER
   password = YOUR_FIRST_PASSWORD

   [Account2]
   account = YOUR_SECOND_ACCOUNT_NUMBER
   password = YOUR_SECOND_PASSWORD

   # Add more accounts as needed
   [Account3]
   account = YOUR_THIRD_ACCOUNT_NUMBER
   # password =  # Will prompt if not provided

   [Logging]
   level = INFO
   ```

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

### Multiple Accounts

```bash
# Connect to multiple accounts using config file
python main.py --config config.ini

# Enable verbose logging for debugging
python main.py --config config.ini --verbose
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

### Example Output - Multiple Accounts

```
2025-01-XX XX:XX:XX - INFO - Connecting to account1 (account 12345678)...
2025-01-XX XX:XX:XX - INFO - [account1] Attempting to connect to FundedNext (FundedNext-Server 2) account 12345678
2025-01-XX XX:XX:XX - INFO - [account1] Successfully connected to account 12345678
2025-01-XX XX:XX:XX - INFO - Added connection account1 successfully
2025-01-XX XX:XX:XX - INFO - Connecting to account2 (account 87654321)...
2025-01-XX XX:XX:XX - INFO - [account2] Attempting to connect to FundedNext (FundedNext-Server 2) account 87654321
2025-01-XX XX:XX:XX - INFO - [account2] Successfully connected to account 87654321
2025-01-XX XX:XX:XX - INFO - Added connection account2 successfully
2025-01-XX XX:XX:XX - INFO - Successfully connected to 2 out of 2 accounts
2025-01-XX XX:XX:XX - INFO - [account1] Account 12345678 on FundedNext-Server 2 - Balance: 15100.45 USD
2025-01-XX XX:XX:XX - INFO - [account2] Account 87654321 on FundedNext-Server 2 - Balance: 25250.78 USD
2025-01-XX XX:XX:XX - INFO - All connections established. Press Ctrl+C to disconnect and exit.
```

## Project Structure

```
copy-trade/
├── src/
│   ├── broker_connection.py       # Core MT5 connection logic + MultiBrokerManager
│   └── example.py                 # Example usage (single account)
├── main.py                        # Application entry point (supports multiple accounts)
├── config.ini.example             # Configuration template (multiple accounts)
├── requirements.txt               # Python dependencies
├── DEVELOPMENT.md                 # Development notes and roadmap
└── README.md                      # This file
```

## Multiple Account Management

### MultiBrokerManager Class

The `MultiBrokerManager` class provides:

- **Thread-safe operations** for managing multiple connections
- **Connection tracking** with unique identifiers
- **Bulk operations** for connecting/disconnecting all accounts
- **Account monitoring** with real-time status updates
- **Error isolation** - one failing connection doesn't affect others

### Key Methods

```python
# Create manager
manager = MultiBrokerManager()

# Add connections
manager.add_connection("account1", broker, server, platform, account_num, password)

# Get specific connection
conn = manager.get_connection("account1")

# Get all connected accounts info
accounts = manager.get_connected_accounts()

# Disconnect all
manager.disconnect_all()
```

## Supported Brokers

| Broker | Status | Server Examples |
|--------|--------|----------------|
| FundedNext | ✅ Working | `FundedNext-Server 2`, `FundedNext-Live2` |
| Others | 🚧 Planned | Easy to add via configuration |

## Development Status

### ✅ Completed Features

1. **MT5 Connection Management**
   - Headless initialization with credentials
   - Robust error handling and retry logic
   - Account information retrieval
   - Clean connection lifecycle management

2. **Multiple Account Support**
   - Simultaneous connections to multiple accounts
   - Same broker/server with different credentials
   - Thread-safe connection management
   - Individual connection monitoring

3. **Configuration System**
   - INI-based configuration for multiple accounts
   - Command-line argument support
   - Backward compatibility with single account mode
   - Flexible server name mapping

4. **Logging & Monitoring**
   - Comprehensive logging system with connection IDs
   - Real-time account balance monitoring
   - Connection status tracking for all accounts

### 🚧 In Progress

1. **Copy Trading Engine**
   - Trade monitoring and replication between accounts
   - Position management across multiple accounts
   - Risk management rules

### 📋 Planned Features

1. **Advanced Copy Trading**
   - Master-slave account designation
   - Proportional scaling based on account size
   - Selective trade copying with filters

2. **Advanced Risk Management**
   - Stop-loss and take-profit rules
   - Maximum drawdown limits per account
   - Position sizing algorithms

3. **Web Interface**
   - Real-time monitoring dashboard for all accounts
   - Configuration management
   - Trade history and analytics

4. **Notifications**
   - Email/SMS alerts for all accounts
   - Trade execution notifications
   - Error and status updates

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
