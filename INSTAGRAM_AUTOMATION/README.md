# INSTAGRAM_AUTOMATION
Instagram Scraper  Description  This script is an automated tool designed to scrape Instagram posts based on specified keywords. It uses Selenium and Brave browser to navigate through Instagram, log in, search hashtags, and extract relevant post data. The scraped data is saved in JSON format.

Features:
* Automates Instagram login and hashtag search.
* Extracts post URLs, usernames, and post content.
* Saves data in structured JSON format.
* Utilizes Brave browser for enhanced privacy.
* Configurable scrolling duration for post extraction.

Prerequisites:
* Ensure the following software is installed:
* Python 3.6 or higher
* Brave browser
* ChromeDriver (for Brave browser)
* Selenium
* webdriver_manager

Install required Python packages with:
pip3 install selenium webdriver-manager

Setup:
1. Install Brave Browser:
    Download and install Brave from https://brave.com/.
2. ChromeDriver for Brave:
    ChromeDriver is automatically managed using webdriver-manager.
3. Configuration File:
    Create a config.ini file in the project directory with the following content:
    [creds]
    username=your_instagram_username
    password=your_instagram_password
4. Keyword File:
    Prepare a text file containing keywords (one per line) for hashtag searches.

Usage:
Run the script with the following command:
python script_name.py -k path/to/keywords.txt -o path/to/output.json -t 5
* -k : Path to the keyword file.
* -o : Path to the output JSON file.
* -t : (Optional) Time limit in minutes for scrolling. Default is 0.5 minutes.

Example:
python3 instagram_scraper.py -k keywords.txt -o results.json -t 3

How It Works:
1. Login – Logs into Instagram using credentials from config.ini.
2. Search – Searches for each keyword as a hashtag.
3. Scroll – Scrolls through posts under each hashtag for the specified duration.
4. Extract – Collects post URLs, usernames, and embedded links.
5. Save – Stores the extracted data into a JSON file.

Output:
The output JSON will have the following structure:
{
  "Cust_ID": "0001",
  "Run_ID": "12345",
  "component-type": "Scraper",
  "Job_ID": "1234568jack",
  "Source": "Instagram",
  "Source_url": "post_url",
  "original_poster_profile": "username",
  "fake_posting_url": "embedded_links",
  "keyword_matched": "searched_keyword",
  "original_msg": "post_text"
}

Logging:
Important events and errors are logged in Instagram_SMS.log.

Notes:
* Ensure compliance with Instagram's policies.
* Excessive scraping may trigger account restrictions.

Credit:
Developed by ulethon
