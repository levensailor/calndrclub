# Enhanced Logging Guide

This guide explains how to use the enhanced logging system for better troubleshooting and debugging.

## Overview

The backend now has comprehensive logging with the following features:

- **Separate log files**: `backend.log` for application logs, `requests.log` for HTTP requests
- **File rotation**: 1MB max per file, keeps 3 backup copies
- **EST timestamps**: All logs use Eastern Time with AM/PM format
- **Function names**: Logs include the function name where the log was generated
- **Line numbers**: Logs include filename and line number
- **Health endpoint exclusion**: `/health`, `/db-info`, and `/cache-status` are not logged to reduce noise

## Log Files

### backend.log
Contains all application logs including:
- Startup/shutdown events
- Database operations
- Error messages with full stack traces
- Service operations

### requests.log
Contains HTTP request logs including:
- Request method and path
- Client IP and user agent
- Response status codes
- Request duration
- Errors during request processing

## Using Logging in Your Code

### Basic Logging

```python
from core.logging import get_logger

logger = get_logger(__name__)

def my_function():
    logger.info("This is an info message")
    logger.warning("This is a warning")
    logger.error("This is an error")
    logger.debug("This is debug info (only shown in DEBUG mode)")
```

### Function Logging Decorator

For automatic entry/exit logging:

```python
from core.logging import log_function_call

@log_function_call
def my_function(param1, param2):
    # Function logic here
    return result
```

For async functions:

```python
from core.logging import log_async_function_call

@log_async_function_call
async def my_async_function(param1, param2):
    # Async function logic here
    return result
```

### Exception Logging

Use the context manager for automatic exception logging:

```python
from core.logging import log_exception

with log_exception():
    # Code that might raise an exception
    risky_operation()
```

## Log Format

Application logs use this format:
```
2024-01-15 02:30:45 PM EST - INFO - [filename.py:123] - function_name() - Log message
```

Request logs use this format:
```
2024-01-15 02:30:45 PM EST - INFO - ➤ POST /api/v1/users from 192.168.1.1 [Mozilla/5.0...]
2024-01-15 02:30:45 PM EST - INFO - ✓ POST /api/v1/users → 201 (0.234s)
```

## Health Endpoints

The following endpoints are excluded from request logging to reduce noise:
- `/health`
- `/db-info`
- `/cache-status`

## Troubleshooting Tips

1. **Check both log files**: Application errors in `backend.log`, request issues in `requests.log`
2. **Look for stack traces**: Full Python tracebacks are logged for unhandled exceptions
3. **Check request timing**: Slow requests are logged with duration
4. **Monitor startup logs**: Database and Redis connection issues are logged during startup
5. **Use log rotation**: Old logs are automatically archived (backend.log.1, backend.log.2, etc.)

## Log Levels

- **DEBUG**: Detailed information for debugging (function entry/exit)
- **INFO**: General information about application flow
- **WARNING**: Something unexpected happened but the app can continue
- **ERROR**: A serious problem occurred
- **CRITICAL**: A very serious error occurred

## Environment Variables

You can control logging behavior with:
- `LOG_LEVEL`: Set to DEBUG, INFO, WARNING, ERROR, or CRITICAL
- `APP_ENV`: Set to development for more verbose logging

## Best Practices

1. Use appropriate log levels
2. Include context in log messages (user ID, operation being performed)
3. Don't log sensitive information (passwords, tokens)
4. Use the decorators for automatic function logging
5. Check logs regularly for patterns and issues 