import re
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio

from core.logging import logger

# School Events Caching
SCHOOL_EVENTS_CACHE: Optional[List[Dict[str, Any]]] = None
SCHOOL_EVENTS_CACHE_TIME: Optional[datetime] = None
SCHOOL_EVENTS_CACHE_TTL_HOURS = 24

# Calendar URL discovery patterns
CALENDAR_URL_PATTERNS = [
    r'calendar',
    r'events',
    r'schedule',
    r'closures',
    r'holidays',
    r'important.dates',
    r'school.calendar',
    r'academic.calendar',
    r'news',
    r'announcements'
]

# Common calendar/events page indicators
CALENDAR_KEYWORDS = [
    'calendar', 'events', 'schedule', 'closure', 'holiday', 'vacation',
    'break', 'closed', 'open', 'hours', 'dates', 'announcements', 'news',
    'academic', 'school'
]

# Event parsing patterns
EVENT_DATE_PATTERNS = [
    r'(\w+\s+\d{1,2},?\s+\d{4})',  # January 15, 2024
    r'(\d{1,2}/\d{1,2}/\d{4})',    # 1/15/2024
    r'(\d{1,2}-\d{1,2}-\d{4})',    # 1-15-2024
    r'(\w+\s+\d{1,2})',            # January 15
]

def _is_valid_event_title(title: str) -> bool:
    """
    Check if an event title is valid and should be included.
    Filters out day-only events, empty content, and other invalid titles.
    """
    if not title or len(title.strip()) < 3:
        return False
    
    title_lower = title.lower().strip()
    
    # Filter out day-only events
    day_only_patterns = [
        r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\.?,?\s*$',
        r'^(mon|tue|wed|thu|fri|sat|sun)\.?,?\s*$',
        r'^(mo|tu|we|th|fr|sa|su)\.?,?\s*$'
    ]
    
    for pattern in day_only_patterns:
        if re.match(pattern, title_lower):
            return False
    
    # Filter out generic invalid content
    invalid_patterns = [
        r'^[\d\s\-\.,]+$',  # Only numbers, spaces, dashes, periods, commas
        r'^[^\w]+$',        # Only special characters
        r'^(all day|view|more|details?|info|click|link|here)\.?\s*$',  # Generic words
        r'^(monthweekday|weekday|day)\s*\d*\s*$',  # Calendar navigation elements
        r'^\s*(previous|next|back|forward)\s*$',  # Navigation words
    ]
    
    for pattern in invalid_patterns:
        if re.match(pattern, title_lower):
            return False
    
    # Filter out very short or meaningless content
    meaningful_words = re.findall(r'\b[a-zA-Z]{3,}\b', title)
    if len(meaningful_words) == 0:
        return False
    
    return True

async def discover_calendar_url(school_name: str, base_url: str) -> Optional[str]:
    """
    Crawl a school website to discover potential calendar/events URLs.
    Returns the most promising calendar URL found.
    """
    if not base_url:
        return None
        
    logger.info(f"Discovering calendar URL for school: {school_name}, URL: {base_url}")
    
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
                        logger.info(f"Found direct calendar URL for {school_name}: {candidate}")
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
                    if 'academic' in text or 'academic' in url.lower():
                        score += 9
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
                    logger.info(f"Discovered calendar URL for {school_name}: {best_url} (score: {scored_links[0][0]})")
                    return best_url
                
            except Exception as e:
                logger.error(f"Error crawling main page {base_url}: {e}")
        
        logger.warning(f"No calendar URL discovered for {school_name} at {base_url}")
        return None
        
    except Exception as e:
        logger.error(f"Error discovering calendar URL for {school_name}: {e}")
        return None

async def parse_events_from_url(calendar_url: str) -> List[Dict[str, str]]:
    """
    Parse events from a school calendar URL.
    Returns a list of events with date and title.
    """
    if not calendar_url:
        return []
    
    logger.info(f"Parsing school events from: {calendar_url}")
    
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
                                
                                # Filter out invalid event titles
                                if event_title and len(event_title) > 2 and _is_valid_event_title(event_title):
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
                                    
                                    # Filter out invalid event titles
                                    if event_title and len(event_title) > 2 and _is_valid_event_title(event_title):
                                        events[iso_date] = event_title[:100]
                            
                            except ValueError:
                                continue
            
            logger.info(f"Successfully parsed {len(events)} school events from {calendar_url}")
            return [{"date": date, "title": title} for date, title in events.items()]
            
    except Exception as e:
        logger.error(f"Error parsing school events from {calendar_url}: {e}")
        return []

async def get_school_events(family_id: str, events: List[Dict[str, str]], school_name: str) -> Dict[str, str]:
    """
    Process and store school events for a family.
    Returns a dictionary of {date: event_title} for calendar display.
    """
    try:
        processed_events = {}
        for event in events:
            date = event.get('date')
            title = event.get('title', '')
            
            if date and title:
                # Prefix with school name if provided
                if school_name:
                    display_title = f"{school_name}: {title}"
                else:
                    display_title = title
                
                processed_events[date] = display_title[:100]  # Limit length
        
        logger.info(f"Processed {len(processed_events)} school events for family {family_id}")
        return processed_events
        
    except Exception as e:
        logger.error(f"Error processing school events for family {family_id}: {e}")
        return {}

async def fetch_school_events() -> List[Dict[str, str]]:
    """Scrape school closing events and return list of {date, title}. Uses 24-hour in-memory cache."""
    global SCHOOL_EVENTS_CACHE, SCHOOL_EVENTS_CACHE_TIME
    
    # Return cached copy if fresh
    if SCHOOL_EVENTS_CACHE and SCHOOL_EVENTS_CACHE_TIME:
        if datetime.now(timezone.utc) - SCHOOL_EVENTS_CACHE_TIME < timedelta(hours=SCHOOL_EVENTS_CACHE_TTL_HOURS):
            logger.info("Returning cached school events.")
            return SCHOOL_EVENTS_CACHE

    logger.info("Fetching fresh school events from the website...")
    url = "https://www.thelearningtreewilmington.com/calendar-of-events/"
    scraped_events = {}

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the header for the 2025 closings to anchor the search
        header = soup.find('p', string=re.compile(r'THE LEARNING TREE CLOSINGS IN 2025'))
        if header:
            for sibling in header.find_next_siblings():
                if sibling.name != 'p':
                    break
                
                text = sibling.get_text(separator=' ', strip=True)
                if not text:
                    continue

                parts = text.split('-')
                
                if len(parts) > 1:
                    event_name = parts[0].strip()
                    date_str = "-".join(parts[1:]).strip()
                else:
                    event_name = text
                    date_str = ""

                date_match = re.search(r'(\w+\s+\d+)', text)
                if date_match:
                    date_str = date_match.group(1)

                year_match = re.search(r'(\d{4})', header.text)
                year = year_match.group(1) if year_match else "2025"
                
                if "new year" in event_name.lower() and "2026" in text.lower():
                    year = "2026"

                event_name = event_name.replace(date_str, "").strip()
                event_name = re.sub(r'\s*-\s*$', '', event_name)

                try:
                    date_str_no_weekday = re.sub(r'^\w+,\s*', '', date_str)
                    full_date_str = f"{date_str_no_weekday}, {year}"
                    full_date_str = full_date_str.replace("Jan ", "January ")

                    event_date = datetime.strptime(full_date_str, '%B %d, %Y')
                    iso_date = event_date.strftime('%Y-%m-%d')
                    if event_name:
                        scraped_events[iso_date] = event_name
                except ValueError:
                    logger.warning(f"Could not parse date from: '{date_str}' in text: '{text}'")
        else:
            logger.warning("Could not find the school closings header for 2025.")

    except Exception as e:
        logger.error(f"Failed to scrape or parse school events: {e}", exc_info=True)
        # Return old cache if fetching fails to avoid returning nothing on a temporary error
        if SCHOOL_EVENTS_CACHE:
            return SCHOOL_EVENTS_CACHE
        return []

    logger.info(f"Successfully scraped {len(scraped_events)} school events.")
    SCHOOL_EVENTS_CACHE = [{"date": d, "title": name} for d, name in scraped_events.items()]
    SCHOOL_EVENTS_CACHE_TIME = datetime.now(timezone.utc)
    return SCHOOL_EVENTS_CACHE

async def get_all_school_events(base_url: str) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """
    Complete workflow: discover calendar URL and parse events for schools.
    Returns (calendar_url, events_list).
    """
    calendar_url = await discover_calendar_url("School", base_url)
    if not calendar_url:
        return None, []
    
    events = await parse_events_from_url(calendar_url)
    return calendar_url, events

async def store_school_events(school_provider_id: int, events_list: List[Dict[str, Any]], school_name: str = "School"):
    """
    Store discovered school events in the new school_events table.
    
    Args:
        school_provider_id: The school provider ID to associate events with
        events_list: List of events with 'date' and 'title' keys
        school_name: Name of the school for logging
    """
    from core.database import database
    from db.models import school_events
    from datetime import datetime
    
    if not events_list:
        logger.info("No school events to store")
        return
    
    try:
        logger.info(f"Storing {len(events_list)} school events for school provider {school_provider_id} ({school_name})")
        
        # Delete existing events for this school provider first to avoid duplicates
        delete_query = school_events.delete().where(
            school_events.c.school_provider_id == school_provider_id
        )
        deleted_count = await database.execute(delete_query)
        logger.info(f"Deleted {deleted_count} existing school events")
        
        # Insert new school events
        inserted_count = 0
        skipped_count = 0
        for event in events_list:
            try:
                # Validate event title before storing
                if not _is_valid_event_title(event['title']):
                    logger.debug(f"Skipping invalid event title: '{event['title']}'")
                    skipped_count += 1
                    continue
                
                # Parse the date
                event_date = datetime.strptime(event['date'], '%Y-%m-%d').date()
                
                # Determine event type based on title
                event_type = 'event'  # default
                title_lower = event['title'].lower()
                if any(word in title_lower for word in ['closed', 'closure', 'holiday', 'break', 'vacation']):
                    event_type = 'closure'
                elif any(word in title_lower for word in ['early', 'dismissal', 'half day', 'early release']):
                    event_type = 'early_dismissal'
                elif any(word in title_lower for word in ['pd day', 'professional development', 'teacher workday']):
                    event_type = 'pd_day'
                
                # Insert the event
                insert_query = school_events.insert().values(
                    school_provider_id=school_provider_id,
                    event_date=event_date,
                    title=event['title'],
                    description=event.get('description'),
                    event_type=event_type,
                    all_day=True  # Default to all day for now
                )
                
                await database.execute(insert_query)
                inserted_count += 1
                
            except ValueError as e:
                logger.error(f"Error parsing date for school event: {event['date']} - {e}")
                continue
            except Exception as e:
                logger.error(f"Error inserting school event: {e}")
                continue
        
        logger.info(f"Successfully stored {inserted_count} school events for {school_name} (skipped {skipped_count} invalid events)")
        
    except Exception as e:
        logger.error(f"Error storing school events: {e}")
        raise

# Keep the old function for backward compatibility but deprecate it
async def get_school_events(family_id: str, events_list: List[Dict[str, str]], school_name: str):
    """
    DEPRECATED: Use store_school_events instead.
    This function is kept for backward compatibility but should not be used for new code.
    """
    logger.warning("get_school_events is deprecated. Use store_school_events instead.")
    # This function will be removed in a future update
    pass
