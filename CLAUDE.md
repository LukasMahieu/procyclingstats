# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python package for scraping procyclingstats.com, a cycling statistics website. The package provides a web scraping API with different scraper classes for various types of cycling data.

## Architecture

The codebase follows a class-based scraping architecture:

### Core Components
- **Base Scraper Class** (`scraper.py`): Contains the core `Scraper` class that all other scrapers inherit from. It handles HTTP requests, HTML parsing via selectolax, URL construction, and provides a common `parse()` method that calls all parsing methods on a scraper instance.

- **Specialized Scrapers**: Each scraper class inherits from `Scraper` and implements specific parsing methods for different data types:
  - `Race` - Race information and results
  - `RaceStartlist` - Race participant lists  
  - `RaceClimbs` - Climb details for races
  - `Rider` - Individual rider profiles and stats
  - `RiderResults` - Rider's race results history
  - `Ranking` - Various rankings and standings
  - `Stage` - Individual stage information
  - `Team` - Team information and rosters
  - `Calendar` - Race calendar data
  - `StageFeatures` - Stage profile features

### Key Architectural Patterns
- All scrapers work with relative URLs that get converted to absolute procyclingstats.com URLs
- HTML parsing uses selectolax for performance 
- Dynamic URL construction with query parameters via `.php` endpoints
- Common `parse()` method automatically calls all parsing methods and returns a dictionary
- Error handling for expected parsing failures via `ExpectedParsingError`
- Fixtures-based testing approach with HTML snapshots

## Common Development Commands

### Installation & Setup
```bash
# Install for development
pip install -r requirements_dev.txt

# Install package in editable mode  
pip install -e .
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test class
python -m pytest tests/pcs_test.py::TestRider

# Add new test fixtures from URLs
python -m tests add "rider/tadej-pogacar" "race/tour-de-france/2022"

# Update existing HTML fixtures if scraping results differ
python -m tests update_htmls
```

### Usage Patterns
The scrapers follow a consistent pattern:
```python
from procyclingstats import Rider
rider = Rider("rider/tadej-pogacar")
data = rider.parse()  # Returns dict with all parsed data
birthdate = rider.birthdate()  # Call specific parsing method
```

## Development Notes

- All scrapers expect relative URLs (e.g., "rider/tadej-pogacar" not full URLs)
- The base URL is https://www.procyclingstats.com/
- HTML validation checks for "Page not found" and server error messages
- Parsing methods are auto-discovered via reflection (public methods not in `_public_nonparsing_methods`)
- Test fixtures store both HTML (.txt) and expected parsing results (.json)
- The codebase uses selectolax instead of BeautifulSoup for faster HTML parsing