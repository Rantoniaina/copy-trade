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

### 3. ✅ Implement master-slave account designation

**Implemented**: Added comprehensive master/slave functionality to the copy trading system.

**New Features:**

- `AccountRole` enum with MASTER and SLAVE designations
- Enhanced `BrokerConnection` class with role support
- Updated `MultiBrokerManager` with master/slave validation and tracking
- `CopyTradeEngine` class for real-time trade monitoring and replication
- Configuration support for role definitions
- Copy trading validation and status reporting

**Key Components:**

- **Role Management**: Strict validation ensuring exactly one master and at least one slave
- **Trade Monitoring**: Real-time monitoring of master account for new deals
- **Thread Safety**: All operations are thread-safe with proper locking
- **Status Tracking**: Comprehensive status reporting for copy trading setup
- **Configuration**: Role-based account configuration with copy trading settings

**Configuration Example:**

```ini
[CopyTrade]
enabled = true
check_interval = 1.0

[Account1]
account = 12345678
password = password123
role = master

[Account2]
account = 87654321
password = password456
role = slave
```

**Usage:**

```bash
# Start copy trading
python main.py --config config.ini

# Interactive copy trading demo
python src/copy_trade_example.py

# Connect without copy trading
python main.py --config config.ini --no-copy
```

### Next Steps

4. Implement actual trade execution logic (currently logs trades to be copied)
5. Add proportional scaling based on account balance ratios
6. Implement risk management rules and trade filters
7. Add monitoring dashboard and notification features
8. Create enhanced trade management (SL/TP modifications, partial closes)
