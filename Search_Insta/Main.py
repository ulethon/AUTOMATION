# ****************************************************
#  Project : Search Instagram
#  Author  : ulethon
#  Credit  : Full credit goes to ulethon
#  License : For educational use only
# ****************************************************

# Import necessary libraries
import argparse, json, re, random, configparser, logging
from datetime import date
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as BraveService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.utils import ChromeType

# Configure logging settings (logs warnings/errors to Instagram_SMS.log)
logging.basicConfig(
    filename='Instagram_SMS.log',
    level=logging.WARNING,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# -------------------------------
# INPUT Functionality
# -------------------------------
def parse():
    """
    Parse command-line arguments:
    -k : keywords file path
    -t : time limit for scrolling (in minutes)
    -o : output JSON file path
    """
    parser = argparse.ArgumentParser(description="parsing script.")
    parser.add_argument("-k", "--keywords", type=str, help="Path to keywords file.", required=True)
    parser.add_argument("-t", "--time_limit", type=float, nargs='?', const=0.5, help="Enter time_limit for scrolling",)
    parser.add_argument("-o", "--output", type=str, help="Output file name with path", required=True)
    args = parser.parse_args()
    return args

# -------------------------------
# Initialize Selenium + Brave Browser
# -------------------------------
def _init():
    """
    Initialize Brave browser in incognito mode
    using webdriver-manager for automatic driver installation.
    """
    options = webdriver.ChromeOptions()
    options.binary_location = "/usr/bin/brave-browser"
    options.add_argument("--incognito")
    browser = webdriver.Chrome(
        service=BraveService(
            ChromeDriverManager(chrome_type=ChromeType.BRAVE).install()
        ),
        options=options,
    )
    return browser

# -------------------------------
# LOGIN Functionality
# -------------------------------
def login(user, passwd):
    """
    Log in to Instagram with provided username & password.
    Handles popups like 'Save login info' and 'Turn on notifications'.
    """
    browser = _init()
    browser.maximize_window()
    browser.get("https://www.instagram.com/")
    try:
        # Ensure Instagram page loaded
        assert "Instagram" in browser.title

        # Enter username
        sleep(random.randint(1, 6))
        elem = browser.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div/div/div[1]/section/main/div/div/div[1]/div[2]/form/div/div[1]/div/label/input")
        elem.send_keys(user)

        # Enter password
        sleep(random.randint(1, 4))
        elem = browser.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div/div/div[1]/section/main/div/div/div[1]/div[2]/form/div/div[2]/div/label/input")
        elem.send_keys(passwd + Keys.RETURN)
        sleep(3)

        # Handle various states & popups
        if 'No results found.' in browser.page_source:
            return 0
        if "Sorry, this page isn\'t available." or "The link you followed may be broken, or the page may have been removed" in browser.page_source:
            pass
        sleep(random.randint(0, 2))

        # Dismiss notification popup
        if 'Turn on notifications' in browser.page_source:
            elem = browser.find_element(By.XPATH, '/html/body/div[2]/div/div/div[3]/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div[3]/button[2]')
            elem.click()

        # Handle save login popup
        if 'Save your login information?' in browser.page_source:
            elems = browser.find_element(By.XPATH,"/html/body/div[2]/div/div/div[2]/div/div/div/div[1]/div[1]/div[2]/section/main/div/div/div/div/div")
            elems.click()

    except Exception as e:
        logging.error("Login error occurred"+'\n'+str(e))
        browser.execute_script("""
            alert("Error occurred during login, pls check terminal for details.")
        """)
        browser.close()
        exit()
    return browser

# -------------------------------
# SEARCH Functionality
# -------------------------------
def search(key, browser, time_limit):
    """
    Search Instagram hashtag page, scroll for posts,
    and collect post URLs within a given time limit.
    """
    url = 'https://www.instagram.com/explore/tags/' + key
    browser.execute_script('window.open("{}","_self");'.format(url.strip()))
    sleep(random.randint(1,7))

    # Check if page not available
    if 'No results found.' in browser.page_source:
        return 0
    if "Sorry, this page isn\'t available." in browser.page_source:
        return str(0)

    # Handle popups again
    if 'Turn on notifications' in browser.page_source:
        elem = browser.find_element(By.XPATH, '/html/body/div[2]/div/div/div[3]/div/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div[3]/button[2]')
        elem.click()

    link = []
    start_time = float(datetime.datetime.now().minute)

    # Keep scrolling to collect posts
    while True:
        sleep(5)
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Collect post links
        post = browser.find_elements(By.CSS_SELECTOR, 'a[Role]')
        for p in post:
            try:
                href = p.get_attribute('href')
                if '/p/' in href:   # Only post URLs
                    link.append([href, key])
            except Exception as e:
                logging.error("Exception Occured when trying to retrive post url\'s"+'\n'+str(e))
                pass

        # Extra scroll movements to load more posts
        try:
            sleep(1)
            browser.execute_script("window.scrollTo(0,document.body.scrollHeight - 100)")
            sleep(7)
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(1)
            browser.execute_script("window.scrollTo(0,document.body.scrollHeight - 100)")
        except Exception as e:
            logging.error('Error Occured While scrolling page...'+'\n'+str(e))
            pass

        # Stop after time_limit reached
        if float(datetime.datetime.now().minute) - start_time >= time_limit:
            break

        # Stop if duplicate links detected
        found_duplicates = False
        for i in range(len(link)-1):
            if link[i] == link[i+1]:
                found_duplicates = True
                break
        if found_duplicates:
            break
    return link

# -------------------------------
# POST SEARCH Functionality
# -------------------------------
def post_search(post_url,browser,output,keyword):
    """
    Visit each post, extract message body, profile name, links,
    and save data to JSON output file.
    """
    sleep(5)
    browser.execute_script('window.open("{}","_self");'.format(post_url.strip()))
    browser.implicitly_wait(random.randint(5,10))

    # Extract post body
    message_body = []
    try:
        body = browser.find_element(By.CLASS_NAME, '_a9zr').text
        if body == "":
            message_body = 'NULL'
        message_body = body
    except Exception as e:
        logging.error('Exeption while finding Message_body...!'+'\n'+str(e))

    # Extract profile name
    profile_name = []
    try:
        profile = message_body.split()
        profile_name = profile[0]
    except Exception as e:
        logging.error('Exeption while finding Profile_name...!'+'\n'+str(e))

    # Extract links from post text
    links = []
    try:
        l_regex = re.compile('(http|ftp|https):\/\/([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])')
        link = l_regex.findall(message_body)
        if link == "":
            links = 'NULL'
        links = str(link)
    except Exception as e:
        logging.error('Exeption while finding Fake_posting_urls...!'+'\n'+str(e))

    # Prepare data dictionary for saving
    out_data = {
        "Cust_ID": '0001',
        "Run_ID": '12345',
        "component-type": "Scrapper",
        "Job_ID": '1234568jack',
        "Source": "Instagram",
        "Source_url": post_url,
        "original_poster_profile": profile_name,
        "fake_posting_url": links,
        "keyword_matched": keyword,
        "original_msg": str(message_body).replace("\n"," ")
    } 
    output_json(out_data,output)

# -------------------------------
# OUTPUT Functionality
# -------------------------------
def output_json(data, output):
    """Append scraped data to JSON output file."""
    with open(output, 'a') as jsonfile:
        json.dump(data, jsonfile)
        jsonfile.write('\n')

# -------------------------------
# MAIN Function
# -------------------------------
def Instagram_main():
    """
    Main function:
    - Read credentials from config.ini
    - Login to Instagram
    - Search for keywords
    - Extract posts
    - Save to output JSON file
    """
    config = configparser.ConfigParser(interpolation=None)
    args = parse()
    config.read('config.ini')

    # Login with config.ini credentials
    browser = login(config['creds']['username'].strip(),config['creds']['password'].strip())
    post = []

    # Read keywords from file and search each
    with open(args.keywords,'r') as k:
        key = k.readlines()
        for i in (key):
            post += search(i.strip(), browser, args.time_limit)

    # If no posts found
    if post == 0:
        print('No post url find')
        browser.close()

    # Process each post found
    for post_url in (post):
        post_search(post_url[0].strip(),browser, args.output,post_url[1])

# Entry point
if __name__ == "__main__":
    Instagram_main()
