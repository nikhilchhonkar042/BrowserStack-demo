# Import all required libraries
import logging  # For logging progress and errors
import os  # For file/directory handling and environment variables
import re  # For regular expressions (used in cleaning text)
import time  # To pause execution for loading pages
import json  # To save output in JSON format
import requests  # To download images from URLs
from collections import Counter  # For counting repeated words

# Import Selenium-related libraries
from selenium import webdriver  # Main Selenium WebDriver
from selenium.webdriver.common.by import By  # To locate elements like By.TAG_NAME
from selenium.webdriver.support.ui import WebDriverWait  # For explicit waits
from selenium.webdriver.support import expected_conditions as EC  # Expected conditions for wait
from selenium.common.exceptions import TimeoutException, NoSuchElementException  # Handling exceptions
from selenium.webdriver.chrome.options import Options  # For browser options

# For translation of content
from googletrans import Translator

# For running local tunnel with BrowserStack
from browserstack.local import Local

# Create logs directory and configure logging settings
from datetime import datetime
os.makedirs("logs", exist_ok=True)  # Create folder if it doesn't exist
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = f"logs/scraper_{timestamp}.log"
OUTPUT_TXT = f"output/articles_output_{timestamp}.txt"
OUTPUT_JSON = f"output/articles_output_{timestamp}.json"
logging.basicConfig(
    filename=LOG_FILE,  # Log file path
    filemode="w",  # Overwrite the log file each time
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
    level=logging.INFO  # Minimum level to log
)

# Initialize BrowserStack Local
bs_local = None

def start_local():
    global bs_local
    bs_local = Local()  # Create a Local tunnel instance
    bs_local_args = { "key": os.getenv("BROWSERSTACK_ACCESS_KEY") }  # Get key from system environment variables
    bs_local.start(**bs_local_args)  # Start the local tunnel with credentials
    logging.info("BrowserStack Local started.")  # Log tunnel started

def stop_local():
    if bs_local and bs_local.isRunning():
        bs_local.stop()  # Stop the local tunnel
        logging.info("BrowserStack Local stopped.")

# Set up the remote browser using BrowserStack

def setup_driver():
    options = Options()  # Create Chrome options instance
    options.set_capability("browserName", "Chrome")  # Use Chrome browser
    options.set_capability("browserVersion", "latest")  # Use latest version

    # Set additional capabilities for BrowserStack
    options.set_capability("bstack:options", {
        "os": "Windows",
        "osVersion": "10",
        "sessionName": "ElPais Scraper Test",
        "userName": os.getenv("BROWSERSTACK_USERNAME"),  # Read username from environment
        "accessKey": os.getenv("BROWSERSTACK_ACCESS_KEY"),
        "local": "true",  # Indicates we are using local testing
        "projectName": "BrowserStack Sample",
        "buildName": "browserstack-build-1"
    })

    # Connect to BrowserStack hub
    url = "http://hub-cloud.browserstack.com/wd/hub"
    return webdriver.Remote(command_executor=url, options=options)

# Function to download an image from URL and save locally
def download_image(img_url, title, save_dir="screenshots"):
    os.makedirs(save_dir, exist_ok=True)  # Ensure directory exists
    try:
        response = requests.get(img_url, timeout=10)  # Send HTTP GET request
        if response.status_code == 200:
            filename = title[:30].replace(" ", "_").replace("/", "_") + ".jpg"  # Generate file name
            filepath = os.path.join(save_dir, filename)  # Full file path
            with open(filepath, "wb") as f:
                f.write(response.content)  # Write binary content to file
            logging.info(f"Image saved: {filepath}")
        else:
            logging.warning(f"Image request failed: {response.status_code}")
    except Exception as e:
        logging.error(f"Image download failed: {e}")

# Function to open the site, collect article links, visit each article, and extract info
def scrape_articles():
    driver = setup_driver()  # Start Selenium browser
    wait = WebDriverWait(driver, 10)  # Wait max 10 seconds for elements to load
    logging.info("Opening El País - Opinión section...")
    driver.get("https://elpais.com/opinion/")  # Go to the main page
    time.sleep(3)  # Wait for JavaScript content to load

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article")))  # Wait for articles to appear
        articles = driver.find_elements(By.CSS_SELECTOR, "article")[:5]  # Find top 5 article elements
        article_links = [
            a.find_element(By.TAG_NAME, "a").get_attribute("href")  # From each article, get the link
            for a in articles
        ]
    except Exception as e:
        logging.error("Failed to fetch article links")
        driver.quit()
        return []

    article_data = []  # Store all articles in a list
    for i, link in enumerate(article_links, start=1):
        try:
            driver.get(link)  # Open article link
            time.sleep(3)  # Wait for page load
            title = driver.find_element(By.TAG_NAME, "h1").text.strip()  # Extract article title
            content = wait.until(EC.presence_of_element_located((By.TAG_NAME, "article"))).text.strip()  # Get content
            try:
                img_tag = driver.find_element(By.TAG_NAME, "img")  # Try to find image tag
                img_url = img_tag.get_attribute("src")  # Get image URL
                download_image(img_url, title)  # Download image
            except NoSuchElementException:
                logging.info("No image found in this article.")
            article_data.append({"title": title, "link": link, "content": content})  # Save article data
        except Exception as e:
            logging.error(f"Error scraping article {i}: {e}")
            continue

    driver.quit()  # Close browser session
    return article_data  # Return list of scraped articles

# Clean unwanted patterns from article content using regular expressions
def clean_content(text):
    patterns = [
        r'Share on \w+',  # Matches text like 'Share on Twitter'
        r'Copy link',
        r'COMMENTS.*',
        r'Standards ›',
        r'More information',
        r'If you are interested.*',
        r'Subscribe to continue.*',
        r'Read without limits',
        r'Continue reading',
        r'I am already a subscriber',
        r'Filed in.*',
        r'Sponsored content.*',
        r'Latest news.*',
        r'The most seen.*',
        r'\| Learn More',
        r'\.\.\.',
        r'^\d{2}:\d{2}'  # Time stamps like 13:45
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return text.strip()

# Translate list of strings using Google Translate
def translate_text_list(texts):
    translator = Translator()
    translated = []
    for text in texts:
        try:
            result = translator.translate(text, src='es', dest='en')  # Spanish to English
            # If result is a coroutine, run it synchronously
            if hasattr(result, '__await__'):
                import asyncio
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(result)
            translated.append(result.text)
        except Exception as e:
            logging.error(f"Translation failed: {e}")
            translated.append(text)
    return translated

# Save readable articles in TXT format
def save_articles_to_file(articles, filename="articles_output.txt"):
    os.makedirs("output", exist_ok=True)
    filepath = OUTPUT_TXT
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("==== Translated Articles from El País - Opinión ====\n\n")
        for idx, article in enumerate(articles, 1):  # idx = 1, 2, 3...; article = each dict in articles list
            f.write(f"\U0001F4F0 Article {idx}: {article['title']}\n")  # 📰 Article title
            f.write(f"\U0001F517 Link: {article['link']}\n\n")  # 🔗 Link to article
            f.write(f"{article['content']}\n")  # Article content
            f.write("\n" + "-" * 100 + "\n\n")  # Separator line
        f.write("==== Summary Table ====\n\n")
        f.write("{:<8} {:<60} {}\n".format("No.", "Title", "Link"))  # Column headers
        f.write("-" * 120 + "\n")
        for idx, article in enumerate(articles, 1):
            short_title = (article['title'][:57] + "...") if len(article['title']) > 60 else article['title']
            f.write("{:<8} {:<60} {}\n".format(idx, short_title, article['link']))
    logging.info(f"Readable output saved to: {filepath}")

# Save articles in JSON format
def save_articles_to_json(articles, filename="articles_output.json"):
    os.makedirs("output", exist_ok=True)
    filepath = OUTPUT_JSON
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=4)
        logging.info(f"JSON output saved to: {filepath}")
    except Exception as e:
        logging.error(f"Failed to save JSON: {e}")

# Analyze title word frequency using Counter
def analyze_repeated_words(titles):
    all_words = []
    for title in titles:
        words = re.findall(r'\b\w+\b', title.lower())  # Extract words
        all_words.extend(words)
    counter = Counter(all_words)  # Count all words
    for word, count in counter.items():
        if count > 2:
            logging.info(f"{word}: {count}")

# Main driver block
if __name__ == "__main__":
    try:
        start_local()  # Start the BrowserStack tunnel
        logging.info("Starting BrowserStack test run for El País scraper")
        articles = scrape_articles()  # Get scraped articles
        if articles:
            titles = [a["title"] for a in articles]
            contents = [a["content"] for a in articles]
            translated_titles = translate_text_list(titles)
            translated_contents = translate_text_list(contents)
            final_articles = []
            for a, tt, tc in zip(articles, translated_titles, translated_contents):
                final_articles.append({
                    "title": tt,
                    "link": a["link"],
                    "content": clean_content(tc)
                })
            save_articles_to_file(final_articles)
            save_articles_to_json(final_articles)
            analyze_repeated_words(translated_titles)
        else:
            logging.warning("No articles scraped.")
    finally:
        stop_local()  # Always stop the tunnel
