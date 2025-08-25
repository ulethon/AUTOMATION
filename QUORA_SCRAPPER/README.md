# QUORA_SCRAPPER
Quora Scraper  Overview  This Python script is designed to scrape question logs and answers from Quora using Selenium and the Brave browser. The script automates login, searches for specific keywords, extracts relevant links, and outputs the results in JSON format.

Requirements:
* Python 3.x
* Selenium
* Brave Browser
* Webdriver Manager
* argparse
* json
* re
* random
* configparser
* logging

Setup and Installation:
1. Install Python Packages:
    pip install selenium webdriver-manager
2. Install Brave Browser:
    Download and install Brave from here.
    Link - https://brave.com/download/
3. Webdriver Setup:
    Webdriver Manager will handle the installation of the Chrome WebDriver compatible with Brave.
4. Configure Credentials:
    Create a config.ini file in the root directory with the following format:
    [creds]
    username = your_quora_email
    password = your_quora_password

Usage
Run the script with the following command:
python script_name.py -k keywords.txt -o output.json -t day

Arguments:
-k, --keywords : Path to the file containing keywords (one keyword per line).
-o, --output : Path to the output JSON file.
-t, --bytime : Time filter (e.g., hour, day, week, month, year).

How It Works:
* Initialization:Initializes the Brave browser in incognito mode.
* Login:Automates login to Quora using provided credentials.
* Keyword Search:Searches for each keyword in Quora and scrapes relevant question links.
* Data Extraction:For each question, the script extracts the answer links and content.
* Output:Results are stored in JSON format containing source URLs and potential fake posting links.

Output Example:
{
  "Cust_ID": "12345",
  "Run_ID": "000011",
  "component_type": "scrapper",
  "Job_ID": "987644batch01",
  "Source": "Quora",
  "Source_url": "https://www.quora.com/Example",
  "fake_posting_url": "https://example.com",
  "keyword_matched": "Python",
  "original_msg": "This is an example answer from Quora."
}

Error Handling:
Errors during login, scraping, or extraction are logged in Quora_SMS.log.
A browser alert is triggered if login fails.

Notes:
Ensure that Brave browser is installed and its path is correctly set in the script (/usr/bin/brave-browser).
Adjust sleep intervals if encountering rate-limiting issues on Quora.

Disclaimer:
This script is for educational purposes only. Scraping content from Quora may violate their terms of service. Use responsibly.

Credit:
Developed by Pushpraj Thakre (ulethon)
