from fastapi import Request, HTTPException
from fastapi.responses import Response, JSONResponse
import re
import asyncio
from core.logging import logger

# Bot and scanner user agents to filter out
BOT_USER_AGENTS = [
    r'bot', r'crawler', r'spider', r'scraper', r'scanner', 
    r'censys', r'shodan', r'masscan', r'nmap', r'zmap',
    r'nuclei', r'sqlmap', r'dirb', r'gobuster', r'nikto'
]

async def request_validation_middleware(request: Request, call_next):
    """Validate and sanitize incoming HTTP requests to prevent malformed request errors."""
    try:
        # Basic request validation
        
        # 1. Check for reasonable URL length (prevent extremely long URLs)
        if len(str(request.url)) > 8192:  # 8KB limit
            logger.warning(f"Request URL too long ({len(str(request.url))} chars) from {request.client.host}")
            return JSONResponse(
                status_code=414,
                content={"error": "URI Too Long"}
            )
        
        # 2. Check for reasonable header sizes
        total_header_size = sum(len(k) + len(v) for k, v in request.headers.items())
        if total_header_size > 16384:  # 16KB limit
            logger.warning(f"Request headers too large ({total_header_size} bytes) from {request.client.host}")
            return JSONResponse(
                status_code=431,
                content={"error": "Request Header Fields Too Large"}
            )
        
        # 3. Validate HTTP method
        allowed_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"}
        if request.method not in allowed_methods:
            logger.warning(f"Invalid HTTP method '{request.method}' from {request.client.host}")
            return JSONResponse(
                status_code=405,
                content={"error": "Method Not Allowed"}
            )
        
        # 4. Check for null bytes in URL path (common in exploit attempts)
        if '\x00' in str(request.url.path):
            logger.warning(f"Null byte in URL path from {request.client.host}")
            return JSONResponse(
                status_code=400,
                content={"error": "Bad Request"}
            )
        
        # 5. Check Content-Length for POST/PUT requests
        if request.method in {"POST", "PUT", "PATCH"}:
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    length = int(content_length)
                    if length > 10 * 1024 * 1024:  # 10MB limit
                        logger.warning(f"Request body too large ({length} bytes) from {request.client.host}")
                        return JSONResponse(
                            status_code=413,
                            content={"error": "Payload Too Large"}
                        )
                except ValueError:
                    logger.warning(f"Invalid Content-Length header from {request.client.host}")
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Bad Request"}
                    )
        
        # Process the request with timeout protection
        try:
            response = await asyncio.wait_for(call_next(request), timeout=30.0)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout from {request.client.host} for {request.url.path}")
            return JSONResponse(
                status_code=504,
                content={"error": "Gateway Timeout"}
            )
            
    except Exception as e:
        # Catch any other malformed request issues
        logger.warning(f"Malformed request from {request.client.host}: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={"error": "Bad Request"}
        )

async def bot_filter_middleware(request: Request, call_next):
    """Filter out bot/scanner requests to reduce invalid HTTP warnings."""
    user_agent = request.headers.get("user-agent", "").lower()
    
    # Check if request is from a known bot/scanner
    for bot_pattern in BOT_USER_AGENTS:
        if re.search(bot_pattern, user_agent):
            logger.debug(f"Filtered bot request from {request.client.host if request.client else 'unknown'}: {user_agent}")
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden"}
            )
    
    # Check for common scanner paths
    scanner_paths = [
        "/.env", "/wp-admin", "/wp-login", "/phpmyadmin", "/admin",
        "/xmlrpc.php", "/wp-config.php", "/.git", "/config.php",
        "/phpinfo.php", "/wp-content", "/uploads", "/backup"
    ]
    
    request_path = str(request.url.path).lower()
    for scanner_path in scanner_paths:
        if scanner_path in request_path:
            logger.debug(f"Filtered scanner path request from {request.client.host if request.client else 'unknown'}: {request_path}")
            return JSONResponse(
                status_code=404,
                content={"error": "Not Found"}
            )
    
    response = await call_next(request)
    return response

async def add_no_cache_headers(request: Request, call_next):
    """Add no-cache headers to API responses."""
    response = await call_next(request)
    if str(request.url.path).startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response
