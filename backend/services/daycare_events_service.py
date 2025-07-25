import re
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio

from core.logging import logger

# Calendar URL discovery patterns
CALENDAR_URL_PATTERNS = [
    r'calendar',
    r'events',
    r'schedule',
    r'closures',
    r'holidays',
    r'important.dates',
    r'school.calendar',
    r'daycare.calendar',
    r'news',
    r'announcements'
]

# Common calendar/events page indicators
CALENDAR_KEYWORDS = [
    'calendar', 'events', 'schedule', 'closure', 'holiday', 'vacation',
    'break', 'closed', 'open', 'hours', 'dates', 'announcements', 'news'
]

# Event parsing patterns
EVENT_DATE_PATTERNS = [
    r'(\w+\s+\d{1,2},?\s+\d{4})',  # January 15, 2024
    r'(\d{1,2}/\d{1,2}/\d{4})',    # 1/15/2024
    r'(\d{1,2}-\d{1,2}-\d{4})',    # 1-15-2024
    r'(\w+\s+\d{1,2})',            # January 15
]

async def discover_calendar_url(base_url: str) -> Optional[str]:
    """
    Crawl a daycare website to discover potential calendar/events URLs.
    Returns the most promising calendar URL found.
    """
    if not base_url:
        return None
        
    logger.info(f"Discovering calendar URL for: {base_url}")
    
    try:
        # Ensure URL has proper scheme
        if not base_url.startswith(('http://', 'https://')):
            base_url = f"https://{base_url}"
        
        parsed_base = urlparse(base_url)
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            # First, try common calendar URL patterns
            calendar_candidates = []
            
            # Direct calendar URL attempts
            for pattern in CALENDAR_URL_PATTERNS:
                for path in [f"/{pattern}", f"/{pattern}/", f"/{pattern}.html", f"/{pattern}.php"]:
                    candidate_url = urljoin(base_url, path)
                    calendar_candidates.append(candidate_url)
            
            # Test each candidate URL
            for candidate in calendar_candidates:
                try:
                    response = await client.head(candidate)
                    if response.status_code == 200:
                        logger.info(f"Found direct calendar URL: {candidate}")
                        return candidate
                except:
                    continue
            
            # If no direct calendar URL found, crawl the main page for links
            try:
                response = await client.get(base_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for links containing calendar keywords
                calendar_links = []
                
                for link in soup.find_all('a', href=True):
                    href = link.get('href')
                    text = link.get_text(strip=True).lower()
                    
                    # Check if link text or href contains calendar keywords
                    for keyword in CALENDAR_KEYWORDS:
                        if keyword in text or keyword in href.lower():
                            full_url = urljoin(base_url, href)
                            calendar_links.append((full_url, text, keyword))
                            break
                
                # Score and sort calendar links by relevance
                scored_links = []
                for url, text, keyword in calendar_links:
                    score = 0
                    if 'calendar' in text or 'calendar' in url.lower():
                        score += 10
                    if 'events' in text or 'events' in url.lower():
                        score += 8
                    if 'schedule' in text or 'schedule' in url.lower():
                        score += 6
                    if 'closure' in text or 'closure' in url.lower():
                        score += 5
                    if 'holiday' in text or 'holiday' in url.lower():
                        score += 4
                    
                    scored_links.append((score, url, text))
                
                # Return highest scoring link
                if scored_links:
                    scored_links.sort(reverse=True, key=lambda x: x[0])
                    best_url = scored_links[0][1]
                    logger.info(f"Discovered calendar URL: {best_url} (score: {scored_links[0][0]})")
                    return best_url
                
            except Exception as e:
                logger.error(f"Error crawling main page {base_url}: {e}")
        
        logger.warning(f"No calendar URL discovered for {base_url}")
        return None
        
    except Exception as e:
        logger.error(f"Error discovering calendar URL for {base_url}: {e}")
        return None

async def parse_events_from_url(calendar_url: str) -> List[Dict[str, str]]:
    """
    Parse events from a calendar URL using similar logic to school_events_service.
    Returns a list of events with date and title.
    """
    if not calendar_url:
        return []
    
    logger.info(f"Parsing events from: {calendar_url}")
    
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            response = await client.get(calendar_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            events = {}
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get all text content
            text_content = soup.get_text()
            lines = text_content.split('\n')
            
            current_year = datetime.now().year
            
            for line in lines:
                line = line.strip()
                if not line or len(line) < 5:
                    continue
                
                # Look for date patterns in the line
                for pattern in EVENT_DATE_PATTERNS:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    
                    for match in matches:
                        date_str = match.group(1)
                        
                        try:
                            # Parse different date formats
                            parsed_date = None
                            
                            # Try full date with year
                            for fmt in ['%B %d, %Y', '%b %d, %Y', '%m/%d/%Y', '%m-%d-%Y']:
                                try:
                                    parsed_date = datetime.strptime(date_str, fmt)
                                    break
                                except ValueError:
                                    continue
                            
                            # Try date without year (assume current year)
                            if not parsed_date:
                                for fmt in ['%B %d', '%b %d']:
                                    try:
                                        parsed_date = datetime.strptime(f"{date_str}, {current_year}", f"{fmt}, %Y")
                                        break
                                    except ValueError:
                                        continue
                            
                            if parsed_date:
                                iso_date = parsed_date.strftime('%Y-%m-%d')
                                
                                # Extract event title (text before or after the date)
                                event_title = line.replace(date_str, '').strip()
                                event_title = re.sub(r'[^\w\s\-\'\".,!?()]', ' ', event_title)
                                event_title = ' '.join(event_title.split())
                                
                                # Clean up common prefixes/suffixes
                                event_title = re.sub(r'^[-:\s]+', '', event_title)
                                event_title = re.sub(r'[-:\s]+$', '', event_title)
                                
                                if event_title and len(event_title) > 2:
                                    events[iso_date] = event_title[:100]  # Limit title length
                        
                        except ValueError:
                            continue
            
            # Look for structured calendar data (tables, lists, etc.)
            calendar_tables = soup.find_all(['table', 'ul', 'ol', 'div'], 
                                          class_=re.compile(r'calendar|event|schedule', re.I))
            
            for table in calendar_tables:
                rows = table.find_all(['tr', 'li', 'div'])
                for row in rows:
                    row_text = row.get_text(strip=True)
                    if not row_text:
                        continue
                    
                    # Apply same date parsing logic to structured content
                    for pattern in EVENT_DATE_PATTERNS:
                        matches = re.finditer(pattern, row_text, re.IGNORECASE)
                        for match in matches:
                            date_str = match.group(1)
                            try:
                                parsed_date = None
                                for fmt in ['%B %d, %Y', '%b %d, %Y', '%m/%d/%Y', '%m-%d-%Y']:
                                    try:
                                        parsed_date = datetime.strptime(date_str, fmt)
                                        break
                                    except ValueError:
                                        continue
                                
                                if not parsed_date:
                                    for fmt in ['%B %d', '%b %d']:
                                        try:
                                            parsed_date = datetime.strptime(f"{date_str}, {current_year}", f"{fmt}, %Y")
                                            break
                                        except ValueError:
                                            continue
                                
                                if parsed_date:
                                    iso_date = parsed_date.strftime('%Y-%m-%d')
                                    event_title = row_text.replace(date_str, '').strip()
                                    event_title = re.sub(r'[^\w\s\-\'\".,!?()]', ' ', event_title)
                                    event_title = ' '.join(event_title.split())
                                    event_title = re.sub(r'^[-:\s]+', '', event_title)
                                    event_title = re.sub(r'[-:\s]+$', '', event_title)
                                    
                                    if event_title and len(event_title) > 2:
                                        events[iso_date] = event_title[:100]
                            
                            except ValueError:
                                continue
            
            logger.info(f"Successfully parsed {len(events)} events from {calendar_url}")
            return [{"date": date, "title": title} for date, title in events.items()]
            
    except Exception as e:
        logger.error(f"Error parsing events from {calendar_url}: {e}")
        return []

async def get_all_daycare_events(base_url: str) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """
    Complete workflow: discover calendar URL and parse events.
    Returns (calendar_url, events_list).
    """
    calendar_url = await discover_calendar_url(base_url)
    if not calendar_url:
        return None, []
    
    events = await parse_events_from_url(calendar_url)
    return calendar_url, events

async def store_daycare_events(daycare_provider_id: int, events_list: List[Dict[str, Any]], daycare_name: str = "Daycare"):
    """
    Store discovered daycare events in the new daycare_events table.
    
    Args:
        daycare_provider_id: The daycare provider ID to associate events with
        events_list: List of events with 'date' and 'title' keys
        daycare_name: Name of the daycare for logging
    """
    from core.database import database
    from db.models import daycare_events
    from datetime import datetime
    
    if not events_list:
        logger.info("No daycare events to store")
        return
    
    try:
        logger.info(f"Storing {len(events_list)} daycare events for daycare provider {daycare_provider_id} ({daycare_name})")
        
        # Delete existing events for this daycare provider first to avoid duplicates
        delete_query = daycare_events.delete().where(
            daycare_events.c.daycare_provider_id == daycare_provider_id
        )
        deleted_count = await database.execute(delete_query)
        logger.info(f"Deleted {deleted_count} existing daycare events")
        
        # Insert new daycare events
        inserted_count = 0
        for event in events_list:
            try:
                # Parse the date
                event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
                
                # Determine event type based on title
                event_type = 'event'  # default
                title_lower = event['title'].lower()
                if any(word in title_lower for word in ['closed', 'closure', 'holiday']):
                    event_type = 'closure'
                elif any(word in title_lower for word in ['early', 'dismissal', 'half day']):
                    event_type = 'early_dismissal'
                
                # Insert the event
                insert_query = daycare_events.insert().values(
                    daycare_provider_id=daycare_provider_id,
                    event_date=event_date,
                    title=event['title'],
                    description=event.get('description'),
                    event_type=event_type,
                    all_day=True  # Default to all day for now
                )
                
                await database.execute(insert_query)
                inserted_count += 1
                
            except ValueError as e:
                logger.error(f"Error parsing date for daycare event: {event['date']} - {e}")
                continue
            except Exception as e:
                logger.error(f"Error inserting daycare event: {e}")
                continue
        
        logger.info(f"Successfully stored {inserted_count} daycare events for {daycare_name}")
        
    except Exception as e:
        logger.error(f"Error storing daycare events: {e}")
        raise 