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

### 2. ✅ Handle connection to multiple brokers

**Implemented**: Extended the application to support multiple broker connections simultaneously with the same broker and server but different account credentials.

**New Features:**

- `MultiBrokerManager` class for managing multiple connections
- Thread-safe connection management with unique identifiers
- Updated configuration format supporting multiple accounts
- Enhanced logging with connection-specific prefixes
- Backward compatibility with single account mode

**Key Components:**

- `MultiBrokerManager`: Core class for managing multiple connections
- Updated `config.ini.example`: Shows multiple account configuration
- Enhanced `main.py`: Supports both single and multiple account modes
- `src/multi_account_example.py`: Interactive example for testing

**Configuration Example:**

```ini
[Connection]
broker = FundedNext
server = FundedNext-Server 2
platform = MT5

[Account1]
account = 12345678
password = password1

[Account2] 
account = 87654321
password = password2
```

**Usage:**

```bash
# Multiple accounts from config
python main.py --config config.ini

# Interactive multiple account example
python src/multi_account_example.py

# Single account (legacy mode)
python main.py --account 12345678
```

**Features:**
- Simultaneous connections to multiple accounts
- Same broker/server with different credentials
- Connection tracking and monitoring
- Individual account balance reporting
- Thread-safe operations
- Error isolation (one failed connection doesn't affect others)

### Next Steps

3. Implement trade copying functionality between accounts
4. Add master-slave account designation
5. Implement proportional scaling based on account sizes
6. Add monitoring and notification features
7. Create a user interface for easier management
