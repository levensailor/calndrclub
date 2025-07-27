import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import pytz
import functools
import traceback
from typing import Any, Callable

class ESTFormatter(logging.Formatter):
    """Custom formatter to show EST timezone with 12-hour format."""
    def converter(self, timestamp):
        dt = datetime.fromtimestamp(timestamp, tz=pytz.timezone('US/Eastern'))
        return dt.timetuple()
    
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=pytz.timezone('US/Eastern'))
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %I:%M:%S %p')

def setup_logging():
    """Setup application logging with file rotation and console output."""
    # Create logs directory
    log_directory = "logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    
    log_file_path = os.path.join(log_directory, "backend.log")
    request_log_path = os.path.join(log_directory, "requests.log")
    
    # Create EST formatter with function name
    est_formatter = ESTFormatter(
        '%(asctime)s EST - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s'
    )
    
    # Create simplified formatter for request logs
    request_formatter = ESTFormatter(
        '%(asctime)s EST - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove default handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create file handler with rotation for main log
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=1*1024*1024,  # 1 MB
        backupCount=3
    )
    file_handler.setFormatter(est_formatter)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(est_formatter)
    
    # Add handlers to root logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent duplicate logs
    logger.propagate = False
    
    # Create separate request logger
    request_logger = logging.getLogger('requests')
    request_logger.setLevel(logging.INFO)
    
    # Create file handler for request logs
    request_file_handler = RotatingFileHandler(
        request_log_path,
        maxBytes=1*1024*1024,  # 1 MB
        backupCount=3
    )
    request_file_handler.setFormatter(request_formatter)
    
    # Create console handler for requests (optional, can be removed if too verbose)
    request_console_handler = logging.StreamHandler()
    request_console_handler.setFormatter(request_formatter)
    
    # Add handlers to request logger
    request_logger.addHandler(request_file_handler)
    # Uncomment the next line if you want request logs in console too
    # request_logger.addHandler(request_console_handler)
    
    # Prevent request logs from propagating to root logger
    request_logger.propagate = False
    
    return logger

def get_request_logger():
    """Get the request logger instance."""
    return logging.getLogger('requests')

def log_function_call(func: Callable) -> Callable:
    """Decorator to log function entry and exit with parameters."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        
        # Log function entry
        args_str = ", ".join([str(arg)[:100] for arg in args])
        kwargs_str = ", ".join([f"{k}={str(v)[:100]}" for k, v in kwargs.items()])
        params = ", ".join(filter(None, [args_str, kwargs_str]))
        
        logger.debug(f"→ Entering {func.__name__}({params[:200]}{'...' if len(params) > 200 else ''})")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"← Exiting {func.__name__} successfully")
            return result
        except Exception as e:
            logger.error(f"✗ Error in {func.__name__}: {type(e).__name__}: {str(e)}")
            raise
    
    return wrapper

async def log_async_function_call(func: Callable) -> Callable:
    """Decorator to log async function entry and exit with parameters."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        
        # Log function entry
        args_str = ", ".join([str(arg)[:100] for arg in args])
        kwargs_str = ", ".join([f"{k}={str(v)[:100]}" for k, v in kwargs.items()])
        params = ", ".join(filter(None, [args_str, kwargs_str]))
        
        logger.debug(f"→ Entering {func.__name__}({params[:200]}{'...' if len(params) > 200 else ''})")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"← Exiting {func.__name__} successfully")
            return result
        except Exception as e:
            logger.error(f"✗ Error in {func.__name__}: {type(e).__name__}: {str(e)}")
            raise
    
    return wrapper

def log_exception(logger_name: str = None):
    """Context manager to log exceptions with full traceback."""
    class ExceptionLogger:
        def __init__(self, logger_name: str):
            self.logger = logging.getLogger(logger_name or __name__)
        
        def __enter__(self):
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is not None:
                self.logger.error(
                    f"Exception occurred: {exc_type.__name__}: {exc_val}\n"
                    f"Traceback:\n{traceback.format_exc()}"
                )
            return False  # Don't suppress the exception
    
    return ExceptionLogger(logger_name)

def get_logger(name: str = None) -> logging.Logger:
    """Get a logger with the specified name, defaults to calling module."""
    import inspect
    if name is None:
        frame = inspect.currentframe().f_back
        name = frame.f_globals['__name__']
    return logging.getLogger(name)

# Initialize logger
logger = setup_logging()
request_logger = get_request_logger()
