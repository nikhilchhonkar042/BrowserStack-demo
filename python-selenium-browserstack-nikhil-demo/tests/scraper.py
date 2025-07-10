import logging
import os
import re
import time
import json
import requests
from collections import Counter
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from googletrans import Translator
from browserstack.local import Local

# ------------------ Setup Logging ------------------
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/scraper.log",
    filemode="w",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ------------------ Start BrowserStack Local Tunnel ------------------
bs_local = None
def start_local():
    global bs_local
    bs_local = Local()
    bs_local_args = { "key": os.getenv("BROWSERSTACK_ACCESS_KEY") }
    bs_local.start(**bs_local_args)
    logging.info("BrowserStack Local started.")

def stop_local():
    if bs_local and bs_local.isRunning():
        bs_local.stop()
        logging.info("BrowserStack Local stopped.")

# ------------------ WebDriver Setup ------------------
def setup_driver():
    options = Options()
    options.set_capability("browserName", "Chrome")
    options.set_capability("browserVersion", "latest")
    options.set_capability("bstack:options", {
        "os": "Windows",
        "osVersion": "10",
        "sessionName": "ElPais Scraper Test",
        "userName": os.getenv("BROWSERSTACK_USERNAME"),
        "accessKey": os.getenv("BROWSERSTACK_ACCESS_KEY"),
        "local": "true",
        "projectName": "BrowserStack Sample",
        "buildName": "browserstack-build-1"
    })

    url = "http://hub-cloud.browserstack.com/wd/hub"
    return webdriver.Remote(command_executor=url, options=options)

# ------------------ Image Downloader ------------------
def download_image(img_url, title, save_dir="screenshots"):
    os.makedirs(save_dir, exist_ok=True)
    try:
        response = requests.get(img_url, timeout=10)
        if response.status_code == 200:
            filename = title[:30].replace(" ", "_").replace("/", "_") + ".jpg"
            filepath = os.path.join(save_dir, filename)
            with open(filepath, "wb") as f:
                f.write(response.content)
            logging.info(f"Image saved: {filepath}")
        else:
            logging.warning(f"Image request failed: {response.status_code}")
    except Exception as e:
        logging.error(f"Image download failed: {e}")

# ------------------ Article Scraper ------------------
def scrape_articles():
    driver = setup_driver()
    wait = WebDriverWait(driver, 10)
    logging.info("Opening El País - Opinión section...")
    driver.get("https://elpais.com/opinion/")
    time.sleep(3)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article")))
        articles = driver.find_elements(By.CSS_SELECTOR, "article")[:5]
        article_links = [a.find_element(By.TAG_NAME, "a").get_attribute("href") for a in articles]
    except Exception as e:
        logging.error("Failed to fetch article links")
        driver.quit()
        return []

    article_data = []
    for i, link in enumerate(article_links, start=1):
        try:
            driver.get(link)
            time.sleep(3)
            title = driver.find_element(By.TAG_NAME, "h1").text.strip()
            content = wait.until(EC.presence_of_element_located((By.TAG_NAME, "article"))).text.strip()
            try:
                img_tag = driver.find_element(By.TAG_NAME, "img")
                img_url = img_tag.get_attribute("src")
                download_image(img_url, title)
            except NoSuchElementException:
                logging.info("No image found in this article.")
            article_data.append({"title": title, "link": link, "content": content})
        except Exception as e:
            logging.error(f"Error scraping article {i}: {e}")
            continue

    driver.quit()
    return article_data

# ------------------ Cleanup & Translation ------------------
def clean_content(text):
    patterns = [
        r'Share on \w+', r'Copy link', r'COMMENTS.*', r'Standards ›', r'More information',
        r'If you are interested.*', r'Subscribe to continue.*', r'Read without limits',
        r'Continue reading', r'I am already a subscriber', r'Filed in.*', r'Sponsored content.*',
        r'Latest news.*', r'The most seen.*', r'\| Learn More', r'\.\.\.', r'^\d{2}:\d{2}'
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return text.strip()

def translate_text_list(texts):
    translator = Translator()
    translated = []
    for text in texts:
        try:
            result = translator.translate(text, src='es', dest='en')
            translated.append(result.text)
        except Exception as e:
            logging.error(f"Translation failed: {e}")
            translated.append(text)
    return translated

# ------------------ Save Output ------------------
def save_articles_to_file(articles, filename="articles_output.txt"):
    os.makedirs("output", exist_ok=True)
    filepath = os.path.join("output", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("==== Translated Articles from El País - Opinión ====\n\n")
        for idx, article in enumerate(articles, 1):
            f.write(f"📰 Article {idx}: {article['title']}\n")
            f.write(f"🔗 Link: {article['link']}\n\n")
            f.write(f"{article['content']}\n")
            f.write("\n" + "-" * 100 + "\n\n")
        f.write("==== Summary Table ====\n\n")
        f.write("{:<8} {:<60} {}\n".format("No.", "Title", "Link"))
        f.write("-" * 120 + "\n")
        for idx, article in enumerate(articles, 1):
            short_title = (article['title'][:57] + "...") if len(article['title']) > 60 else article['title']
            f.write("{:<8} {:<60} {}\n".format(idx, short_title, article['link']))
    logging.info(f"Readable output saved to: {filepath}")

def save_articles_to_json(articles, filename="articles_output.json"):
    os.makedirs("output", exist_ok=True)
    filepath = os.path.join("output", filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=4)
        logging.info(f"JSON output saved to: {filepath}")
    except Exception as e:
        logging.error(f"Failed to save JSON: {e}")

# ------------------ Word Analyzer ------------------
def analyze_repeated_words(titles):
    all_words = []
    for title in titles:
        words = re.findall(r'\b\w+\b', title.lower())
        all_words.extend(words)
    counter = Counter(all_words)
    for word, count in counter.items():
        if count > 2:
            logging.info(f"{word}: {count}")

# ------------------ Main ------------------
if __name__ == "__main__":
    try:
        start_local()
        logging.info("Starting BrowserStack test run for El País scraper")
        articles = scrape_articles()
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
        stop_local()
