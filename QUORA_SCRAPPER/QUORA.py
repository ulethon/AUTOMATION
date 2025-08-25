# *****************************

# Credit Goes TO : ulethon

# *****************************

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

# Configure logging settings
logging.basicConfig(filename='Quora_SMS.log', level=logging.WARNING, format='%(asctime)s:%(levelname)s:%(message)s')

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

# INPUT Functionality
def parse():
    parser = argparse.ArgumentParser(description="parsing script.")
    parser.add_argument("-k", "--keywords", type=str, help="Path to keywords file.", required=True)
    parser.add_argument("-o", "--output", type=str, help="Output file path", required=True)
    parser.add_argument("-t", "--bytime", type=str, help="Input time according to you want \n hour, day, week, month, year", required=True)
    args = parser.parse_args()
    return args

# LOGIN Functionality
def login(user, passwd):
    browser = _init()
    browser.maximize_window()
    browser.get("https://www.quora.com")
    try:
        assert "Quora" in browser.title
        sleep(random.randint(1, 5))
        elem = browser.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/div/div/div[2]/div[2]/div[2]/div[2]/input')
        elem.send_keys(user)
        sleep(random.randint(1, 5))        

        elem = browser.find_element(By.XPATH, '/html/body/div[2]/div/div[2]/div/div/div/div/div/div[2]/div[2]/div[3]/div[2]/input')
        elem.send_keys(passwd + Keys.RETURN)
    except Exception as e:
        logging.error('Login error occurred'+'\n'+str(e))
        # Display an alert in the browser indicating the error
        browser.execute_script("""
            alert("Error occurred during login, please check terminal for details.")
        """)
        browser.close()
        exit()
    return browser

# Function to grep all anwser link inside the question
def search(k,browser,bytime):
    links = {}
    url = 'https://www.quora.com/search?q='+k+'&time='+bytime
    sleep(random.randint(1, 5))
    browser.execute_script('window.open("{}","_self");'.format(url.strip()))
    sleep(random.randint(1, 5))
    if "We couldn't find any results for" in browser.page_source:
            return 0

    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(random.randint(1,3))
        if "We couldn't find any more results" in browser.page_source:
            break
    try:
        regex = re.compile("https:\/\/www.quora.com\/[\w+-]+[\w]+")
        regex_res = re.findall(regex,browser.page_source)
    except Exception as e:
        logging.error('Error occured while getting Question Links'+'\n'+str(e))
        pass

    if regex_res:
        for r in regex_res:
            if "-" in r:
                links[r] = k.strip()
        return links

# for extracting all data from the page
def logs(question, browser, key):
    url = question+"/log"
    print(url)
    sleep(random.randint(1,3))
    answers = []
    browser.execute_script('window.open("{}","_self");'.format(url.strip()))
    while True:
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(random.randint(1,4))
        if browser.find_element(By.LINK_TEXT, "Question"):
            break
        if browser.page_source("Add comment"):
            pass
    try:
        ans_elements = browser.find_elements(By.LINK_TEXT, "Answer")   
    except Exception as e:
        logging.error('Error occured while getting answers'+'\n'+str(e))
        pass
    for i in ans_elements:
        answers.append([
            i.get_attribute("href"),key
        ])
    return answers

# for get the message of this answer inside the logs
def get_msg(link,browser):
    browser.execute_script('window.open("{}","_self");'.format(link.strip()))
    element = browser.find_element(By.XPATH,"/html/body/div[2]/div/div[2]/div/div[3]/div/div/div/div[1]/div[1]/div[3]")
    return element.text

# for fake_posting_url inside he message body
def url_finder(msg_body):
    res = re.findall(r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})",str(msg_body))
    if res == 0:
        return "NULL"
    else:
        return res

# OUTPUT Functionality
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

    # OUTPUT File Generating
    with open(output, "w") as jsonfile:
        json.dump(out_data, jsonfile)
        jsonfile.write('\n')

# Main Function
if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        browser = login(config['creds']['username'].strip(),config['creds']['password'].strip())
    except Exception as e:
        print(e)
        logging.error('Error Occured while parsing credencials'+'\n'+str(e))
    args = parse()
    questions = []
    try:
        with open(args.keywords) as keys:
            keywords = keys.readlines()
            for k in keywords:
                questions = search(k.strip(),browser,args.bytime)
    except Exception as e:
        logging.error("Error occured while fetching questions."+'\n'+str(e))

    answers = []
    try:
        for q in questions:
            answers.append(logs(q,browser,questions[q]))
    except Exception as e:
            logging.error('Error Occured while fetching data'+'\n'+str(e))
            # pass
            print(e)

    # args.cust_id,args.run_id,args.scrapper_id,args.job_id, args.batch_id
    json_output(args.output,answers)
