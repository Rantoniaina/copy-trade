# Copy Trade

A Python application for automated copy trading using MetaTrader 5 (MT5). This application connects to trading accounts headlessly and provides the foundation for implementing copy trading strategies.

## Features

- ✅ **Headless MT5 Connection** - Connects to MetaTrader 5 without opening the GUI
- ✅ **Multi-Broker Support** - Currently supports FundedNext with easy extensibility
- ✅ **Configuration-Based** - All connection settings via config files
- ✅ **Robust Error Handling** - Comprehensive logging and error management
- ✅ **Account Management** - Real-time account information and balance monitoring
- 🚧 **Copy Trading Logic** - Foundation ready, implementation in progress

## Prerequisites

- **Python 3.8+**
- **MetaTrader 5** installed and configured
- **Trading account** with API access enabled
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

1. **Copy the example configuration:**
   ```bash
   cp config.ini.example config.ini
   ```

2. **Edit `config.ini` with your account details:**
   ```ini
   [Connection]
   broker = FundedNext
   server = FundedNext-Server 2
   platform = MT5
   account = YOUR_ACCOUNT_NUMBER
   password = YOUR_PASSWORD

   [Logging]
   level = INFO
   # file = logs/copy_trade.log
   ```

## Usage

### Basic Connection Test

```bash
python main.py --config config.ini
```

### Command Line Options

```bash
# Use configuration file
python main.py --config config.ini

# Override with command line arguments
python main.py --broker FundedNext --server "FundedNext-Server 2" --account 123456

# Enable verbose logging
python main.py --config config.ini --verbose
```

### Example Output

```
2025-07-22 16:05:49 - INFO - Attempting to connect to FundedNext (FundedNext-Server 2) account 13662820
2025-07-22 16:06:07 - INFO - Successfully connected to account 13662820
2025-07-22 16:06:07 - INFO - Connected to account 13662820 on server FundedNext-Server 2
2025-07-22 16:06:07 - INFO - Balance: 15100.45 USD
2025-07-22 16:06:07 - INFO - Connection established. Press Ctrl+C to disconnect and exit.
```

## Project Structure

```
copy-trade/
├── src/
│   └── broker_connection.py    # Core MT5 connection logic
├── main.py                     # Application entry point
├── config.ini.example          # Configuration template
├── requirements.txt            # Python dependencies
├── DEVELOPMENT.md             # Development notes and roadmap
└── README.md                  # This file
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

2. **Configuration System**
   - INI-based configuration
   - Command-line argument support
   - Flexible server name mapping

3. **Logging & Monitoring**
   - Comprehensive logging system
   - Real-time account balance monitoring
   - Connection status tracking

### 🚧 In Progress

1. **Copy Trading Engine**
   - Trade monitoring and replication
   - Position management
   - Risk management rules

2. **Multi-Account Support**
   - Source account monitoring
   - Multiple destination accounts
   - Proportional scaling

### 📋 Planned Features

1. **Advanced Risk Management**
   - Stop-loss and take-profit rules
   - Maximum drawdown limits
   - Position sizing algorithms

2. **Web Interface**
   - Real-time monitoring dashboard
   - Configuration management
   - Trade history and analytics

3. **Notifications**
   - Email/SMS alerts
   - Trade execution notifications
   - Error and status updates

## Troubleshooting

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

1. Check the logs for detailed error messages
2. Verify MT5 settings and account status
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
