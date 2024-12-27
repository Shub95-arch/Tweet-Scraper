from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import threading
from datetime import datetime, timedelta
import re
import os
from urllib.parse import unquote
import ast
import logging
log_file_path = 'tweets_log.txt'
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,  # Set the logging level to INFO
    format='%(asctime)s - %(message)s',  # Simple format with timestamp
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Adjust Cookies
def set_cookies_with_js(driver, cookies):
    for cookie in cookies:
        cookie_string = f"{cookie['name']}={cookie['value']}; domain={cookie['domain']}; path={cookie['path']};"
        if 'expiry' in cookie:
            cookie_string += f" expires={cookie['expiry']};"
        driver.execute_script(f"document.cookie = '{cookie_string}'")
        print(f"Cookie set: {cookie_string}")

# Csv Append
def append_to_csv(json_file_path, data):

    if os.path.exists(json_file_path) and os.path.getsize(json_file_path) > 0:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            try:
                existing_data = json.load(file)
            except json.JSONDecodeError:
                # print("Error: JSON file is corrupted. It will be overwritten.")
                logging.info('Error: JSON file is corrupted. It will be overwritten.')
                existing_data = []
    else:
        existing_data = []
        logging.info('ELSE Hit: JSON file is corrupted. It will be overwritten.')
    existing_data.extend(data)
    with open(json_file_path, 'w', encoding='utf-8') as file:
        json.dump(existing_data, file, ensure_ascii=False, indent=4)

    
    
# Scraping
def scrape_with_chrome_profile(url, cookies, scroll_selector=None, data_selector=None, max_scrolls=float('inf')):
    try:
        # chrome_profile_path = "C:/Users/shubh/AppData/Local/Google/Chrome/User Data/"
        # profile_directory = "Profile 4"
        
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')
        # options.add_argument(f"--user-data-dir={chrome_profile_path}")
        # options.add_argument(f"--profile-directory={profile_directory}")
        
        driver_path = "E:/chromium/t/chromedriver-win64/chromedriver.exe"
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)

        driver.get(url)
        time.sleep(5)  

        # Set cookies
        set_cookies_with_js(driver, cookies)
        
        # apply cookies
        driver.get(url)
        time.sleep(5)
        
        if not data_selector:
            raise ValueError("A valid data_selector (CSS or XPath) is required.")
        
        
        scrolls = 0
        scraped_data = []
        last_height = driver.execute_script("return document.body.scrollHeight")
        idx = 1
        start_time=time.time()
        # retry_button = driver.find_element(By.XPATH, "//button//span[text()='Retry']")
        while scrolls < max_scrolls:
            tweets = driver.find_elements(By.XPATH, data_selector)
            
            for tweet in tweets:
                try:
                    tweet_text_element = tweet.find_element(By.XPATH, './/div[@data-testid="tweetText"]')
                    tweet_text = tweet_text_element.text.strip()
                    
                    username_element = tweet.find_element(By.XPATH, '..//div[@data-testid="User-Name"]//span[1]')
                    username = username_element.text.strip()
                    
                    profile_url_element = tweet.find_element(By.XPATH, './/div[@data-testid="User-Name"]//a[@href]')
                    profile_url = profile_url_element.get_attribute('href')

                    comment_element = tweet.find_element(By.XPATH, ".//button[@data-testid='reply']//span[@data-testid='app-text-transition-container']//span")
                    comments = comment_element.text.strip() if comment_element else "0"

                    like_element = tweet.find_element(By.XPATH, ".//button[@data-testid='like']//span[@data-testid='app-text-transition-container']//span")
                    likes = like_element.text.strip() if like_element else "0"

                    repost_element = tweet.find_element(By.XPATH, ".//button[@data-testid='retweet']//span[@data-testid='app-text-transition-container']//span")
                    reposts = repost_element.text.strip() if repost_element else "0"

                    tweet_url_element = tweet.find_element(By.XPATH, './/a[@href and contains(@href, "/status/")]')
                    tweet_url = tweet_url_element.get_attribute('href')

                    time_element = tweet.find_element(By.XPATH, './/time')
                    time_frame = time_element.text.strip()
                    
                    now = datetime.now()
                    tweet_time = None

                    # 24hr stop
                    if "h" in time_frame:
                        hours_ago = int(time_frame.split('h')[0])
                        tweet_time = now - timedelta(hours=hours_ago)
                    elif "m" in time_frame:
                        minutes_ago = int(time_frame.split('m')[0])
                        tweet_time = now - timedelta(minutes=minutes_ago)
                    elif "s" in time_frame:
                        seconds_ago = int(time_frame.split('s')[0])
                        tweet_time = now - timedelta(seconds=seconds_ago)
                    elif "d" in time_frame:
                        days_ago = int(time_frame.split('d')[0])
                        tweet_time = now - timedelta(days=days_ago)
                    else:
                        try:
                            tweet_time = datetime.strptime(time_frame, "%b %d")
                            tweet_time = tweet_time.replace(year=now.year)
                        except ValueError:
                            pass

                    if tweet_time and now - tweet_time >= timedelta(hours=24):
                        print(f"Reached tweet older than 24 HRS")
                        driver.quit()
                        return scraped_data
                    decoded_url = unquote(url)
                    match = re.search(r'q=([a-zA-Z0-9_#]+)', decoded_url)
                    search_key = match.group(1)

                    # Store data
                    scraped_data.append({
                        'tweet_text': tweet_text,
                        'username': username,
                        'profile_url': profile_url,
                        'search_key': search_key,
                        'comments': 0 if comments=='' else comments,
                        'likes': 0 if likes=='' else likes,
                        'reposts': 0 if reposts=='' else reposts,
                        'tweet_url':tweet_url,
                        'time_frame': tweet_time.strftime('%Y-%m-%d %H:%M:%S') if tweet_time else "unknown"
                    })
                    log_message = (f"{idx} Tweet: {tweet_text}\n"
               f"Username: {username}\n"
               f"Profile URL: {profile_url}\n"
               f"Time: {tweet_time}\n"
               f"Search Key: {search_key}\n"
               f"Likes: {0 if likes == '' else likes}\n"
               f"Comments: {0 if comments == '' else comments}\n"
               f"Reposts: {0 if reposts == '' else reposts}\n"
               f"Tweet URL: {tweet_url}\n")
                    logging.info(log_message)

# Optionally, log a separator to make the file more readable
                    logging.info("\n" + "-" * 40 + "\n")
                    print(f"{idx} Tweet: {tweet_text}\nUsername: {username}\nProfile URL: {profile_url}\nTime: {tweet_time}\nSearch Key: {search_key}\nLikes: {0 if likes=='' else likes}\nComments: {0 if comments=='' else comments}\nReposts: {0 if reposts=='' else reposts}\nTweet URL: {tweet_url}\n")
                except Exception as e:
                    print(f"Error extracting data from tweet: {e}")
                idx += 1
            
            if scraped_data:
                append_to_csv('./data.json', scraped_data)
                scraped_data.clear()
            # bottom scroll page
            if scroll_selector:
                driver.execute_script(scroll_selector)
            else:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            
            time.sleep(3)  
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            
            if new_height == last_height:
                print("Reached the bottom of the page. Please wait")
                end_time= time.time()-start_time
                rem_time=max(0,15*60-end_time)+3
                # print(start_time,end_time,rem_time)
                
                time.sleep(rem_time)#720
                try:
                    retry_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button//span[text()='Retry']"))
                    )
                    
                    driver.execute_script("arguments[0].scrollIntoView(true);", retry_button)
                    time.sleep(1) 
                    
                    # Retry Click
                    driver.execute_script("arguments[0].click();", retry_button)
                    print("Clicked the Retry button.")
                except Exception as e:
                    driver.execute_script("location.reload()") #added for EXTRA, if not work delete
                    print("Retry button not found")
                
                start_time=time.time()
                pass
                # break
            last_height = new_height
            scrolls += 1
        
        driver.quit()
        print(f"Scraped {len(scraped_data)} items from {url}.")
        # for data in scraped_data:
        #     print(data)
        # return scraped_data
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# Thread function
def scrape_thread(url, cookies, scroll_selector, data_selector):
    print(f"Starting scraping for {url}")
    scrape_with_chrome_profile(url, cookies, scroll_selector, data_selector)
    print(f"Finished scraping for {url}")

def scrape_multiple_urls(data_set, scroll_selector, data_selector):
    threads = []
    
    for data in data_set:
        with open(data['cookie_path'], 'r') as file:
            content = file.read()
        cookies=json.loads(content)
        
        thread = threading.Thread(target=scrape_thread, args=(data['url'], cookies, scroll_selector, data_selector))
        threads.append(thread)
        thread.start()
    
    
    for thread in threads:
        thread.join()
    
    print("Finished scraping all URLs.")


def scrape_multiple_twitter():
    # urls = [
    #     {
    #         'url':'https://x.com/search?q=bitcoin&src=typed_query&f=live',
    #         'cookie_path':'./cookies/twitter.txt'
    #     },
    #     {
    #         'url':'https://x.com/search?q=python&src=typed_query&f=live',
    #         'cookie_path':'./cookies/twitter1.txt'
    #     }
    # ]
    #--
    with open('./urls.txt', 'r') as file:
        content = file.read()
    content = content.replace("'", '"')
    urls = ast.literal_eval(f"[{content}]")
    #--
    data_selector = '//article[@data-testid="tweet"]'  # XPath for tweet containers
    scroll_selector = "window.scrollTo(0, document.body.scrollHeight);"
    
    
    scrape_multiple_urls(urls, scroll_selector, data_selector)

scrape_multiple_twitter()
