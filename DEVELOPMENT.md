# Copy Trade Development

Copy Trade is an application that can copy trade from an account to another one.

## Implementation Tasks

### 1. ✅ Connect to a trading account

**Implemented**: Created a Python module to connect to a MetaTrader 5 trading account using the following parameters:

- Broker (FundedNext)
- Broker server (fundednext server 2)
- Platform (mt5)
- Account number
- Account password

The implementation includes:

- `src/broker_connection.py`: Core module for MT5 connection
- `src/example.py`: Example script demonstrating connection
- `main.py`: Main application entry point with CLI support
- `config.ini.example`: Sample configuration file

**Usage**:

```bash
# Install dependencies
pip install -r requirements.txt

# Run with command line arguments
python main.py --broker FundedNext --server "fundednext server 2" --platform mt5 --account YOUR_ACCOUNT_NUMBER

# Or use a config file
python main.py --config config.ini
```

### Next Steps

2. Implement trade copying functionality between accounts
3. Add monitoring and notification features
4. Create a user interface for easier management
