import re
import os 
import time
import calendar
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from functools import wraps
from selenium.common.exceptions import StaleElementReferenceException


def retries(max_retries=3, delay=2, exceptions=(Exception,)):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    print(f"Function '{func.__name__}' crashed on attempt {attempts}/{max_retries}: {e}")
                    if attempts < max_retries:
                        print(f"Retrying function '{func.__name__}'...")
                        time.sleep(delay)
                    else:
                        print(f"Function '{func.__name__}' failed after {max_retries} retries.")
                        raise
        return wrapper
    return decorator

@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def extract_and_convert_ordinal(text):
        number_to_words = {
            "1": "First", "2": "Second", "3": "Third", "4": "Fourth", "5": "Fifth", 
            "6": "Sixth", "7": "Seventh", "8": "Eighth", "9": "Ninth", "10": "Tenth",
            "11": "Eleventh", "12": "Twelfth", "13": "Thirteenth", "14": "Fourteenth", 
            "15": "Fifteenth", "16": "Sixteenth", "17": "Seventeenth", "18": "Eighteenth", 
            "19": "Nineteenth", "20": "Twentieth", "21": "Twenty First", "22": "Twenty Second",
            "23": "Twenty Third", "24": "Twenty Fourth", "25": "Twenty Fifth", "26": "Twenty Sixth",
            "27": "Twenty Seventh", "28": "Twenty Eighth", "29": "Twenty Ninth", "30": "Thirtieth"
        }

        words = text.split()
        for word in words:
            if word.isdigit() or (word[:-2].isdigit() and word[-2:] in ["ST", "ND", "RD", "TH"]):
                key = word[:-2] if word[:-2].isdigit() else word
                return number_to_words.get(key, word)
        return text


def parse_address(address):
    # Split the address
    address_parts = address.split(",")
    
    street = address_parts[0].strip().split(" ")
    state_info = address_parts[-1].strip().split(" ") if len(address_parts) > 1 else ""

    # Split the street values
    if len(street) < 2:
         return {
        'street_no': '',
        'street_name': '',
        'city': '',
        'state': '',
        'zip': '',
    }
    street_no = street[0] if len(street) > 0 else ''
    print('street ' , street)
    street_name = None
    if len(street[1]) > 1:
        street_name = extract_and_convert_ordinal(street[1])
    elif len(street) > 2 :
        street_name = extract_and_convert_ordinal(street[2])

    # Split the state information
    city = state_info[0] if len(state_info) > 0 else ''
    state = state_info[1] if len(state_info) > 1 else ''
    zip_code = state_info[2] if len(state_info) > 2 else ''  # Assuming zip is at index 2

    return {
        'street_no': street_no,
        'street_name': street_name,
        'city': city,
        'state': state,
        'zip': zip_code,
    }

@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def search_and_get_case_data(driver,record_number, address, description):
    try:
        # Initialize case data dictionary
        case_data = {}
        # Parse the address
        parsed_address = parse_address(address)

        if parsed_address['street_no'] == '' and parsed_address['street_name'] == '':
            return {}
        print('parse_address ' , parsed_address)
        print("Opened the browser")

        # Fill out search form
        def fill_input(xpath, value, field_name):
            try:
                input_field = WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                input_field.send_keys(value)
                print(f"{field_name} input sent: {value}")
            except TimeoutException:
                print(f"{field_name} input field not found.")

        fill_input('//input[@id="inpNumber"]', parsed_address['street_no'], "Street Number")
        fill_input('//input[@id="inpStreet"]', parsed_address['street_name'], "Street Name")

        # Click the search button
        try:
            search_btn = WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, '//button[@id="btSearch"]'))
            )
            search_btn.click()
            print("Clicked the Search Button")
        except TimeoutException:
            print("Search button not found.")
            return

        time.sleep(3)

        # Check for "No Records Found" error
        try:
            WebDriverWait(driver, 11).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//large[contains(text(), "Your search did not find any records")]')
                )
            )
            print("No records found for the search.")
            case_data.update({
                'Record Number': record_number,
                'property_city': parsed_address['city'],
                'property_state': parsed_address['state'],
                'property_zip_code': parsed_address['zip'],
                'description': description
            })
            return case_data
        except TimeoutException:
            print("Records found. Continuing...")

        
        try:
            record_table_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '(//table[@id="searchResults"]/tbody/tr)[1]'))
            )
            record_table_btn.click()
            print("Clicked the First Row")
        except TimeoutException:
            print("Search Results timed out")


        # Helper function to extract data with XPath
        def extract_data(xpath, key, description=None):
            try:
                element = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath)))
                if key == 'parcel_id':
                    case_data[key] = element.text.split(':')[1].strip()
                else:
                    case_data[key] = element.text.strip()
                if description:
                    print(f"{description}: {element.text.strip()}")
            except TimeoutException:
                case_data[key] = ""
                if description:
                    print(f"{description} not found.")

        # Extract main case data
        extract_data('//td[@class="DataletHeaderTopLeft"]', 'parcel_id', "Parcel ID")
        extract_data('//tr[td[contains(text(), "Site (Property) Address")]]/td[@class="DataletData"]',
                     'property_address', "Property Address")
        
        # extracting the property class
        extract_data('//tr[td[contains(text(), "Property Class")]]/td[@class="DataletData"]',
                     'Property Class', "Property Class")
        
        try:
            # Locate all `<a>` elements containing owner names
            owner_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, '//tr[td[contains(text(), "Owner")]]/td[@class="DataletData"]/a'))
            )

            # Handle cases where there are multiple owners
            if len(owner_elements) == 0:
                case_data['owner_names'] = []
                case_data['owner_names_string'] = ''

            # Extract the text content from each `<a>` element
            owner_names = [owner.text.strip() for owner in owner_elements if owner.text.strip()]

            # Store the owner names as a list and a comma-separated string
            case_data['owner_names'] = owner_names
            case_data['owner_names_string'] = ', '.join(owner_names)

            print(f"Owner Names: {owner_names}")

        except TimeoutException:
            # Handle missing owners by initializing an empty list and string
            case_data['owner_names'] = []
            case_data['owner_names_string'] = ''
            print("Owner Names not found.")


        # Append address info
        case_data.update({
            'Record Number': record_number,
            'property_city': parsed_address['city'],
            'property_state': parsed_address['state'],
            'property_zip_code': parsed_address['zip'],
            'description': description
        })

        # Extract additional fields
        extract_data('//tr[td[contains(text(), "Owner Mailing /")]]/td[@class="DataletData"]',
                     'mailing_address', "Mailing Address")
        extract_data('//tr[td[contains(text(), "Contact Address")]]/td[@class="DataletData"]',
                     'contact_address', "Contact Address")

        # Dwelling data
        dwelling_data = {
            '(//table[@id="Dwelling Data"]//td)[10]': 'bedrooms',
            '(//table[@id="Dwelling Data"]//td)[11]': 'bathrooms',
            '(//table[@id="Dwelling Data"]//td)[8]': 'Tot Fin Area',
            '(//table[@id="Dwelling Data"]//td)[7]': 'Year built'
        }
        for xpath, key in dwelling_data.items():
            extract_data(xpath, key, key)

        # Transfer details
        extract_data('//tr[td[contains(text(), "Transfer Date")]]/td[@class="DataletData"]',
                     'Transfer Date', "Transfer Date")
        extract_data('//tr[td[contains(text(), "Transfer Price")]]/td[@class="DataletData"]',
                     'Transfer Price', "Transfer Price")
        

        # Click "Rental Contact" button
        try:
            rental_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[span[contains(text(), "Rental Contact")]]'))
            )
            rental_btn.click()
            print("Navigating to Rental Contact page...")
            time.sleep(3)
        except TimeoutException:
            print("Rental Contact button not found.")

        # Extract rental contact details
        rental_headers = [
            "Owner Name:", "Owner Business:", "Title:", "Address1:", "Address2:",
            "City:", "State:", "Zip Code:", "Phone Number:", "E-Mail Address:"
        ]
        for header in rental_headers:
            header_key = header.replace(":", "").replace(" ", "_").lower()
            if header in ["City:", "State:"]:
                header_key = f"rental_{header_key}"
            extract_data(f'//tr[td[contains(text(), "{header}")]]/td[@class="DataletData"]',
                         header_key, header)

        return case_data

    except Exception as e:
        print(f"An error occurred while searching for the address: {e}")
        return {}

def split_full_name(full_name):
    # Check if the name is likely an organization or business
    if any(keyword in full_name.upper() for keyword in ["LLC", "INC", "CORP", "COMPANY", "INVESTMENTS", "ENTERPRISES"]):
        # Treat the entire name as the last name (organization name)
        return {"first_name": "", "last_name": full_name.strip()}
    
    # Common name prefixes and suffixes to exclude from splitting
    prefixes = ["Dr.", "Mr.", "Ms.", "Mrs.", "Miss", "Prof."]
    suffixes = ["Jr.", "Sr.", "II", "III", "IV", "Ph.D.", "M.D.", "Esq."]

    # Clean and normalize the name
    full_name = full_name.strip()

    # Remove prefixes and suffixes using regex
    for prefix in prefixes:
        if full_name.startswith(prefix):
            full_name = full_name[len(prefix):].strip()

    for suffix in suffixes:
        if full_name.endswith(suffix):
            full_name = full_name[: -len(suffix)].strip()

    # Split name into parts
    name_parts = full_name.split()

    # Handle single-word names
    if len(name_parts) == 1:
        return {"first_name": name_parts[0], "last_name": ""}

    # Handle multi-word names (assign everything but the first part to last name)
    first_name = name_parts[0]
    last_name = " ".join(name_parts[1:])

    return {"first_name": first_name, "last_name": last_name}

@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def get_chromedriver(headless=False):
    current_dir = os.getcwd()  # Get current working directory for downloads
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": current_dir,  # Set the download folder
        "download.prompt_for_download": False,  # Don't prompt for download
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--start-maximized")
    if headless:
        chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)
    pid = driver.service.process.pid
    print(f"Chrome WebDriver Process ID: {pid}")
    return driver, pid

@retries(max_retries=5, delay=2, exceptions=(ElementClickInterceptedException, StaleElementReferenceException))
def click_elem(elem):
    try:
        if elem is None:
            print("Element not found. Skipping click.")
            return
        elem.click()
        print("Element clicked successfully!")
    except StaleElementReferenceException as e:
        print(f"Stale element detected. Retrying: {e}")
        raise  # Allow the `retries` decorator to retry


@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def set_date_with_js(driver, input_xpath, date_value):
    input_field = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH, input_xpath))
    )
    driver.execute_script("arguments[0].value = arguments[1];", input_field, date_value)
    driver.execute_script("arguments[0].dispatchEvent(new Event('blur'));", input_field)

def merge_into_datafile(file_path, datafile="DataFile.csv", filter_file="record_types.csv"):
    if not os.path.exists(datafile):
        print(f"Creating new data file: {datafile}")
        os.rename(file_path, datafile)
    else:
        print(f"Merging {file_path} into {datafile}")
        existing_data = pd.read_csv(datafile)
        new_data = pd.read_csv(file_path)

        # Merge the data
        combined_data = pd.concat([existing_data, new_data], ignore_index=True)
        
        # Apply the filter
        if os.path.exists(filter_file):
            print(f"Applying filter using {filter_file}")
            filters = pd.read_csv(filter_file)
            combined_data = combined_data[combined_data['Record Type'].isin(filters['record type'].tolist())]
        else:
            print(f"Filter file {filter_file} not found. Skipping filtering.")

        # Save the filtered data
        combined_data.to_csv(datafile, index=False)
        os.remove(file_path)

@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def switch_to_iframe(driver, iframe_xpath='//iframe[@id="ACAFrame"]', retries=3, delay=2):
    attempt = 0
    while attempt < retries:
        try:
            # Wait for iframe to be visible and clickable
            driver.switch_to.default_content()
            iframe = WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, iframe_xpath))
            )
            driver.switch_to.frame(iframe)
            print("Successfully switched to iframe")
            return
        except TimeoutException:
            driver.refresh()
            time.sleep(2)
            driver.switch_to.default_content()
            print(f"Timeout while waiting for iframe on attempt {attempt + 1}/{retries}. Retrying...")
        except Exception as e:
            print(f"Error on attempt {attempt + 1}/{retries}: {e}")

        attempt += 1
        time.sleep(delay)  # Wait before retrying

    print(f"Failed to switch to iframe after {retries} attempts.")
    driver.switch_to.default_content()  # Switching back to the default content if all retries fail

def is_in_iframe(driver, iframe_xpath):
    try:
        driver.switch_to.default_content()
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, iframe_xpath))
        )
        driver.switch_to.frame(iframe)
        print("Switched to iframe successfully.")
        return True
    except Exception as e:
        print(f"Could not switch to iframe: {e}")
        return False


# @retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def get_case_file(driver, start_date, end_date):
    for retries in range(5):
        try:
            set_date_with_js(driver, '//input[@id="ctl00_PlaceHolderMain_generalSearchForm_txtGSStartDate"]', start_date)
            print(f"Set the start date: {start_date}")

            set_date_with_js(driver, '//input[@id="ctl00_PlaceHolderMain_generalSearchForm_txtGSEndDate"]', end_date)
            print(f"Set the end date: {end_date}")

            wait_until_loading_disappears(driver)

            search_btn = WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, '//a[@id="ctl00_PlaceHolderMain_btnNewSearch"]')))
            search_btn.click()
            print("Clicked the Search Button")

            wait_until_loading_disappears(driver=driver)
            time.sleep(2)

            try:
                notice = WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.XPATH, '//span[@id="ctl00_PlaceHolderMain_RecordSearchResultInfo_noDataMessageForSearchResultList_lblMessage"]')))
                
                return True
            except:
                pass
            
            download_btn = WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, '//a[@id="ctl00_PlaceHolderMain_dgvPermitList_gdvPermitList_gdvPermitListtop4btnExport"]')))
            if download_btn is None:
                print("Download button not found.")
                download_btn = WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.XPATH, '//a[@id="ctl00_PlaceHolderMain_dgvPermitList_gdvPermitList_gdvPermitListtop4btnExport"]')))
                
            download_btn.click()
            print("Clicked the Download Button")
            wait_until_loading_disappears(driver=driver)
            print("Laoding screen is disappeared!")

            if wait_for_download_to_complete(pattern="RecordList.*\\.csv"):
                print("Download Successful!")
                downloaded_file = next((f for f in os.listdir(os.getcwd()) if re.match("RecordList.*\\.csv", f)), None)
                if downloaded_file:
                    merge_into_datafile(downloaded_file)
                    return True
            else:
                print("Download failed or timed out.")
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(2)  # Wait before retrying
    return False

@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def wait_until_loading_disappears(driver, timeout=500):
    print("Inside the wait_until_loading_disappears")
    try:
        WebDriverWait(driver, timeout).until_not(
            EC.visibility_of_element_located((By.CLASS_NAME, "ACA_Global_Loading"))
        )
        print("Loading indicator disappeared.")
    except Exception as e:
        print(f"Timeout or error waiting for loading indicator to disappear: {e}")

@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def wait_for_download_to_complete(download_folder=None, pattern="RecordList.*\\.csv", timeout=10000, check_interval=1):
    if download_folder is None:
        download_folder = os.getcwd()  # Default to current directory
    seconds_waited = 0

    while seconds_waited < timeout:
        # List files in the download folder
        files = os.listdir(download_folder)
        if any(file.endswith('.crdownload') for file in files):  # Check for incomplete download
            print("Download in progress...")
            time.sleep(check_interval)  # Wait for a while before checking again
            seconds_waited += check_interval
            print("Seconds waiting for download , ", seconds_waited)
        else:
            matched_files = [file for file in files if re.match(pattern, file)]
            if matched_files:
                print("Download complete.")
                return True  # Download is complete
            time.sleep(check_interval)
            seconds_waited += check_interval
    print("Timeout while waiting for download.")
    return False  # Timeout

@retries(max_retries=5, delay=1, exceptions=(ElementClickInterceptedException, TimeoutException))
def parse_date_range_into_months(start_date, end_date):
    start = datetime.strptime(start_date, "%m/%d/%Y")
    end = datetime.strptime(end_date, "%m/%d/%Y")

    intervals = []
    current = start
    while current <= end:
        next_month = (current + timedelta(days=calendar.monthrange(current.year, current.month)[1])).replace(day=1)
        interval_end = next_month - timedelta(days=1)
        if interval_end > end:
            interval_end = end
        intervals.append((current.strftime("%m/%d/%Y"), interval_end.strftime("%m/%d/%Y")))
        current = next_month

    return intervals

def extract_and_convert_ordinal(text):
        number_to_words = {
            "1": "First", "2": "Second", "3": "Third", "4": "Fourth", "5": "Fifth", 
            "6": "Sixth", "7": "Seventh", "8": "Eighth", "9": "Ninth", "10": "Tenth",
            "11": "Eleventh", "12": "Twelfth", "13": "Thirteenth", "14": "Fourteenth", 
            "15": "Fifteenth", "16": "Sixteenth", "17": "Seventeenth", "18": "Eighteenth", 
            "19": "Nineteenth", "20": "Twentieth", "21": "Twenty First", "22": "Twenty Second",
            "23": "Twenty Third", "24": "Twenty Fourth", "25": "Twenty Fifth", "26": "Twenty Sixth",
            "27": "Twenty Seventh", "28": "Twenty Eighth", "29": "Twenty Ninth", "30": "Thirtieth"
        }

        words = text.split()
        for word in words:
            if word.isdigit() or (word[:-2].isdigit() and word[-2:] in ["ST", "ND", "RD", "TH"]):
                key = word[:-2] if word[:-2].isdigit() else word
                return number_to_words.get(key, word)
        return text


def parse_address(address):
    # Split the address
    address_parts = address.split(",")
    
    street = address_parts[0].strip().split(" ")
    state_info = address_parts[-1].strip().split(" ") if len(address_parts) > 1 else ""

    # Split the street values
    if len(street) < 2:
         return {
        'street_no': '',
        'street_name': '',
        'city': '',
        'state': '',
        'zip': '',
    }
    street_no = street[0] if len(street) > 0 else ''
    print('street ' , street)
    street_name = None
    if len(street[1]) > 1:
        street_name = extract_and_convert_ordinal(street[1])
    elif len(street) > 2:
        street_name = extract_and_convert_ordinal(street[2])

    print('street no ', street_no, '\n street name ', street_name)
    # Split the state information
    city = state_info[0] if len(state_info) > 0 else ''
    state = state_info[1] if len(state_info) > 1 else ''
    zip_code = state_info[2] if len(state_info) > 2 else ''  # Assuming zip is at index 2

    return {
        'street_no': street_no,
        'street_name': street_name,
        'city': city,
        'state': state,
        'zip': zip_code,
    }

def process_owner_data(all_data, split_full_name, processed_data):
    for item in all_data:
        if item is None:
            continue
        
        # Get the list of owner names
        owner_names = item.get('owner_names', [])
        
        for i in range(len(owner_names)):
            # Ensure we process only valid owner names
            if owner_names[i].strip():
                full_owner_name = owner_names[i].strip()
                print(f'Processing owner: {full_owner_name}')
                
                # Split the full owner name into first and last names
                name_parts = split_full_name(owner_names[i])
                first_name = name_parts['first_name']
                last_name = name_parts['last_name']

                # Split mailing_address into mailing_city, mailing_state, and mailing_zip
                contact_address = item.get('contact_address', '')
                mailing_parts = contact_address.split(" ")
                mailing_city = mailing_parts[0] if len(mailing_parts) > 0 else ""
                mailing_state = mailing_parts[1] if len(mailing_parts) > 1 else ""
                mailing_zip = mailing_parts[2] if len(mailing_parts) > 2 else ""

                # Append processed data for this owner
                processed_data.append({
                    "record_number": item.get('Record Number', ''),
                    "parcel": item.get('parcel_id', ''),
                    "first_name": first_name,
                    "last_name": last_name,
                    "full_name": owner_names[i],
                    "property_address": item.get('property_address', ''),
                    "property_city": item.get('property_city', ''),
                    "property_state": item.get('property_state', ''),
                    "property_zip_code": item.get('property_zip_code', ''),
                    "description": item.get('description', ''),
                    "mailing_address": item.get('mailing_address', ''),
                    "mailing_city": mailing_city,
                    "mailing_state": mailing_state,
                    "mailing_zip": mailing_zip,
                    "owner_name": item.get('owner_name', ''),
                    "owner_business": item.get('owner_business', ''),
                    "title": item.get('title', ''),
                    "address_1": item.get('address1', ''),
                    "address_2": item.get('address2', ''),
                    "rental_city": item.get('rental_city', ''),
                    "rental_state": item.get('rental_state', ''),
                    "rental_zipcode": item.get('zip_code', ''),
                    "phone": item.get('phone_number', ''),
                    "email": item.get('e-mail_address', ''),
                    "bedroom": item.get('bedrooms', ''),
                    "bathroom": item.get('bathrooms', ''),
                    "Tot Fin Area": item.get('Tot Fin Area', ''),
                    "year built": item.get('Year built', ''),
                    "Property Class": item.get('Property Class', ''),  # Assuming no Property Class in data
                    "Transfer Date": item.get('Transfer Date', ''),
                    "Transfer Price": item.get('Transfer Price', '')
                })

        if owner_names == []:
            # Handle case where owner name is missing or blank
            print(f"No valid owner name found in this entry, processing other data.")
            # Append data with missing owner information
            processed_data.append({
                "record_number": item.get('Record Number', ''),
                "parcel": item.get('parcel_id', ''),
                "first_name": '',
                "last_name": '',
                "full_name": '',
                "property_address": item.get('property_address', ''),
                "property_city": item.get('property_city', ''),
                "property_state": item.get('property_state', ''),
                "property_zip_code": item.get('property_zip_code', ''),
                "description": item.get('description', ''),
                "mailing_address": item.get('mailing_address', ''),
                "mailing_city": '',
                "mailing_state": '',
                "mailing_zip": '',
                "owner_name": item.get('owner_name', ''),
                "owner_business": item.get('owner_business', ''),
                "title": item.get('title', ''),
                "address_1": item.get('address1', ''),
                "address_2": item.get('address2', ''),
                "rental_city": item.get('rental_city', ''),
                "rental_state": item.get('rental_state', ''),
                "rental_zipcode": item.get('zip_code', ''),
                "phone": item.get('phone_number', ''),
                "email": item.get('e-mail_address', ''),
                "bedroom": item.get('bedrooms', ''),
                "bathroom": item.get('bathrooms', ''),
                "Tot Fin Area": item.get('Tot Fin Area', ''),
                "year built": item.get('Year built', ''),
                "Property Class": item.get('Property Class', ''),
                "Transfer Date": item.get('Transfer Date', ''),
                "Transfer Price": item.get('Transfer Price', '')
            })



if __name__ == "__main__":
    starting_date = input('Enter a starting date(MM/DD/YYYY): \t')
    ending_date = input('Enter a Ending date(MM/DD/YYYY): \t')

    driver, pid = get_chromedriver(headless=True)
    driver.get("https://portal.columbus.gov/permits/Default.aspx")
    print("Opened the browser")

    failed_intervals = []
    try:
        switch_to_iframe(driver)
        next_btn = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//a[@id="ctl00_PlaceHolderMain_TabDataList_TabsDataList_ctl02_LinksDataList_ctl00_LinkItemUrl"]')))
        click_elem(next_btn)
        print("Clicked the Next Button successfully!")

        intervals = parse_date_range_into_months(starting_date, ending_date)
        for start_date, end_date in intervals:
            print(f"Processing interval: {start_date} to {end_date}")
            result = get_case_file(driver, start_date, end_date)
            if not result:
                print("Failed to get case files for the interval.")
                failed_intervals.append((start_date, end_date))

        while failed_intervals:
            print(f"Retrying for failed intervals: {failed_intervals}")
            remaining_intervals = failed_intervals[:]
            failed_intervals = []
            for interval in remaining_intervals:
                print(f"Retrying for interval: {interval[0]} to {interval[1]}")
                result = get_case_file(driver, interval[0], interval[1])
                if not result:
                    print("Unsuccessfully retried to get case files for the interval.")
                    failed_intervals.append(interval)

        driver.quit()

        # # getting the chrome driver
        driver , pid = get_chromedriver(headless=True)

        data = pd.read_csv('DataFile.csv')
        filters = pd.read_csv('record_types.csv')

        # filtering out the required records
        data = data[data['Record Type'].isin(filters['record type'].tolist())]

        # droping all the duplicates
        data.drop_duplicates(subset=['Address', 'Record Number'], inplace=True)
        data = data.iloc[1:40]
        
        all_data = []
        for index, row in data.iterrows():
            print(f"Processing record: {row['Address']}")
            driver.get("https://property.franklincountyauditor.com/_web/search/commonsearch.aspx?mode=address")
            case_data = search_and_get_case_data(driver, row['Record Number'] , row['Address'] , row['Description'] )
            print('case_data , ', case_data)
            all_data.append(case_data)
        
    finally:
        driver.quit()

    columns = [
            "record_number", "parcel", "first_name", "last_name", "full name", "property_address",
            "property_city", "property_state", "property_zip_code", "description",
            "mailing_address", "mailing_city", "mailing_state", "mailing_zip",
            "owner_name", "owner_business", "title", "address_1", "address_2",
            "rental_city", "rental_state", "rental_zipcode", "phone", "email",
            "bedroom", "bathroom", "Tot Fin Area", "year built", "Property Class",
            "Transfer Date", "Transfer Price"
    ]

    processed_data = []

    process_owner_data(all_data, split_full_name, processed_data)
    # Create a DataFrame
    df = pd.DataFrame(processed_data, columns=columns)
    output_file = "Output.xlsx"

    renamed_file = 'Previous_output.xlsx'
    # Check if the renamed file exists
    if os.path.exists(renamed_file):
        # Delete the renamed file
        os.remove(renamed_file)
        print(f"File {renamed_file} has been deleted")

    # Save to Excel
    if os.path.exists(output_file):
        # Rename the file
        os.rename(output_file, renamed_file)
        if os.path.exists('ProcessedRecords.csv'):
            os.remove('ProcessedRecords.csv')
            print(f"File ProcessedRecords.csv has been deleted")
        os.rename('DataFile.csv', 'ProcessedRecords.csv')
        print(f"File renamed to {renamed_file}")

    df.to_excel(output_file, index=False)
    print(f"Data saved to {output_file}")
