# Columbus Permit and Property Data Scraper

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Selenium](https://img.shields.io/badge/Selenium-4.0%2B-orange)
![Pandas](https://img.shields.io/badge/Pandas-1.3%2B-brightgreen)

Automated tool for extracting permit records and detailed property information from Columbus government portals. Designed for real estate professionals, tax assessors, and data analysts.

---

## Table of Contents
- [Key Features](#key-features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output Files](#output-files)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Key Features

### 🕒 **Date Range Automation**
- Splits large date ranges into monthly intervals (avoids portal timeout limits)
- Automatic retry mechanism for failed intervals
- Handles date formatting conversions automatically

### 🔄 **Robust Error Handling**
- 5 retries for failed operations with incremental delays
- Handles stale elements, timeouts, and intercepted clicks
- Smart detection of "No Records Found" scenarios

### 🏠 **Advanced Address Parsing**
- Converts ordinal numbers (e.g., "5TH" → "Fifth")
- Splits addresses into components:
  - Street number
  - Street name
  - City
  - State
  - ZIP code

### 📊 **Comprehensive Data Extraction**
- Property Characteristics:
  - Parcel ID
  - Square footage
  - Year built
  - Bedroom/bathroom count
- Ownership Details:
  - Current owner names
  - Mailing addresses
  - Contact information
- Transaction History:
  - Transfer dates
  - Sale prices
  - Permit descriptions

---

## Requirements
- Python 3.8+
- Chrome Browser (latest version)
- ChromeDriver ([download](https://chromedriver.chromium.org/))
- 2GB+ free disk space for data storage

---

## Installation

1. **Clone Repository**
git clone https://github.com/yourusername/columbus-property-scraper.git
cd columbus-property-scraper
Install Dependencies

pip install -r requirements.txt
ChromeDriver Setup

Download ChromeDriver matching your Chrome version
Place chromedriver executable in project root or system PATH

Configuration Files

touch record_types.csv  # Add your permit type filters
Configuration
record_types.csv

record type
Building Permit
Electrical Permit
Plumbing Permit
Code Parameters (Optional)
Parameter	Location	Description
max_retries	@retries decorator	Number of retry attempts (default:5)
headless	get_chromedriver()	Run browser visibly (False)
timeout	wait_for_download()	Download wait time (default:10000s)

Usage
Run Main Script

python scraper.py

Input Date Ranges
When prompted:

Enter a starting date(MM/DD/YYYY): 01/01/2023
Enter a Ending date(MM/DD/YYYY): 06/30/2023
Automated Process Flow

Browser launches in headless mode

Processes 3-month intervals sequentially

Merges results automatically

Generates final Excel report

Output Files
DataFile.csv

Raw consolidated data from all successful scrapes:
Record Number,Address,Record Type,Description,Status,...
Output.xlsx
Structured report with normalized fields:

Column	Example
rental_zipcode	43215
Tot Fin Area	1850 sq ft
Transfer Price	$325,000
owner_business	ABC Properties LLC
ProcessedRecords.csv
Archive of successfully processed records (prevents duplicates)

Troubleshooting
Common Issues
ChromeDriver Mismatch
Verify Chrome version: chrome://version/
Download matching ChromeDriver version
Missing Records
Check record_types.csv filters
Verify portal accessibility: Columbus Permit Portal
Timeout Errors
# Increase timeouts in code:
WebDriverWait(driver, 120)  # Change from 60 to 120 seconds

Debug Mode
Run with visible browser:
# In get_chromedriver():
driver, pid = get_chromedriver(headless=False)  # Set to False

License
MIT License - See LICENSE for details


This comprehensive README:
1. Provides clear installation/configuration steps
2. Explains technical implementation details
3. Includes troubleshooting guidelines
4. Documents all output formats
5. Uses badges for quick tech stack recognition
6. Maintains consistent formatting for readability
7. Links to external resources where appropriate
