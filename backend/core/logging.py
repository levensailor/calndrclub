import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import pytz

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
    
    # Create EST formatter
    est_formatter = ESTFormatter(
        '%(asctime)s EST - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove default handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create file handler with rotation
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=1*1024*1024,  # 1 MB
        backupCount=3
    )
    file_handler.setFormatter(est_formatter)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(est_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Prevent duplicate logs
    logger.propagate = False
    
    return logger

# Initialize logger
logger = setup_logging()
