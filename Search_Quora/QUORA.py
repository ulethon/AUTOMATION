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

# Configure logging settings (all warnings and errors will be saved in Quora_SMS.log)
logging.basicConfig(filename='Quora_SMS.log', level=logging.WARNING, format='%(asctime)s:%(levelname)s:%(message)s')


# Initialize browser with Brave in incognito mode
def _init():
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


# Parse CLI arguments for keywords, output file, and time filter
def parse():
    parser = argparse.ArgumentParser(description="parsing script.")
    parser.add_argument("-k", "--keywords", type=str, help="Path to keywords file.", required=True)
    parser.add_argument("-o", "--output", type=str, help="Output file path", required=True)
    parser.add_argument("-t", "--bytime", type=str, help="Input time filter (hour, day, week, month, year)", required=True)
    args = parser.parse_args()
    return args


# Login function using credentials stored in config.ini
def login(user, passwd):
    browser = _init()
    browser.maximize_window()
    browser.get("https://www.quora.com")
    try:
        assert "Quora" in browser.title  # Check if page loaded successfully
        sleep(random.randint(1, 5))

        # Input username
        elem = browser.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/div/div/div[2]/div[2]/div[2]/div[2]/input')
        elem.send_keys(user)
        sleep(random.randint(1, 5))        

        # Input password and press ENTER
        elem = browser.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/div/div/div[2]/div[2]/div[3]/div[2]/input')
        elem.send_keys(passwd + Keys.RETURN)

    except Exception as e:
        # Log error and show alert in browser
        logging.error('Login error occurred'+'\n'+str(e))
        browser.execute_script("""alert("Error occurred during login, please check terminal for details.")""")
        browser.close()
        exit()
    return browser


# Search Quora for questions related to given keyword and time filter
def search(k, browser, bytime):
    links = {}
    url = 'https://www.quora.com/search?q='+k+'&time='+bytime
    sleep(random.randint(1, 5))
    browser.execute_script('window.open("{}","_self");'.format(url.strip()))
    sleep(random.randint(1, 5))

    # If no results found
    if "We couldn't find any results for" in browser.page_source:
        return 0

    # Scroll until all results are loaded
    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(random.randint(1,3))
        if "We couldn't find any more results" in browser.page_source:
            break

    try:
        # Regex to capture question links
        regex = re.compile("https:\/\/www.quora.com\/[\w+-]+[\w]+")
        regex_res = re.findall(regex,browser.page_source)
    except Exception as e:
        logging.error('Error occured while getting Question Links'+'\n'+str(e))
        pass

    # Store links with keyword reference
    if regex_res:
        for r in regex_res:
            if "-" in r:   # ensure it's a valid question link
                links[r] = k.strip()
        return links


# Extract answer links from Quora question logs
def logs(question, browser, key):
    url = question+"/log"
    print(url)
    sleep(random.randint(1,3))
    answers = []
    browser.execute_script('window.open("{}","_self");'.format(url.strip()))

    # Scroll until answers are loaded
    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(random.randint(1,4))
        if browser.find_element(By.LINK_TEXT, "Question"):
            break

    try:
        ans_elements = browser.find_elements(By.LINK_TEXT, "Answer")   
    except Exception as e:
        logging.error('Error occured while getting answers'+'\n'+str(e))
        pass

    # Collect all answer links with their matched keyword
    for i in ans_elements:
        answers.append([i.get_attribute("href"), key])
    return answers


# Fetch the message text of a specific answer
def get_msg(link,browser):
    browser.execute_script('window.open("{}","_self");'.format(link.strip()))
    element = browser.find_element(By.XPATH,"/html/body/div[2]/div/div[2]/div/div[3]/div/div/div/div[1]/div[1]/div[3]")
    return element.text


# Extract any URLs present in the answer text
def url_finder(msg_body):
    res = re.findall(r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})",str(msg_body))
    if res == 0:
        return "NULL"
    else:
        return res


# Generate final JSON output file
def json_output(output, answers):
    for i in answers:
        for a in i:
            msg_body = get_msg(a[0],browser)
            urls = url_finder(msg_body)
            for u in urls:
                out_data = {   
                        "Cust_ID": "12345",
                        "Run_ID": "000011",
                        "component_type":"scrapper",
                        "Job_ID": "987644batch01",
                        "Source":"Quora",
                        "Source_url":a[0],
                        "fake_posting_url":u,
                        "keyword_matched":a[2],
                        "original_msg":str(msg_body).replace("\n"," ")
                        }
                print(out_data)

    # Save output to JSON file
    with open(output, "w") as jsonfile:
        json.dump(out_data, jsonfile)
        jsonfile.write('\n')


# ===============================
# Main Execution Flow Starts Here
# ===============================
if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Step 1: Login using credentials
    try:
        browser = login(config['creds']['username'].strip(),config['creds']['password'].strip())
    except Exception as e:
        print(e)
        logging.error('Error Occured while parsing credencials'+'\n'+str(e))

    # Step 2: Parse arguments (keywords file, output, time filter)
    args = parse()
    questions = []

    # Step 3: Search Quora with each keyword
    try:
        with open(args.keywords) as keys:
            keywords = keys.readlines()
            for k in keywords:
                questions = search(k.strip(),browser,args.bytime)
    except Exception as e:
        logging.error("Error occured while fetching questions."+'\n'+str(e))

    # Step 4: Get logs/answers for each question
    answers = []
    try:
        for q in questions:
            answers.append(logs(q,browser,questions[q]))
    except Exception as e:
            logging.error('Error Occured while fetching data'+'\n'+str(e))
            print(e)

    # Step 5: Save final JSON output
    json_output(args.output,answers)
