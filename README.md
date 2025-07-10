# BrowserStack-demo


### ✅ **Task Achievement Table**

| Task                                                                   | Status     | Notes                                                                                   |
| ---------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------- |
| ✅ Visit the website El País ([https://elpais.com](https://elpais.com)) | ✅ Done     | Accessed directly via Selenium driver.                                                  |
| ✅ Ensure website is in Spanish                                         | ✅ Done     | The site is by default in Spanish.                                                      |
| ✅ Navigate to the Opinion section                                      | ✅ Done     | `driver.get("https://elpais.com/opinion/")`                                             |
| ✅ Fetch first five articles                                            | ✅ Done     | Selects top 5 `<article>` tags on the page.                                             |
| ✅ Print title and content of each article (Spanish)                    | ✅ Done     | Title and content fetched via Selenium, stored in logs and output files.                |
| ✅ Download and save cover image if available                           | ✅ Done     | Images saved using `requests.get()` and `img_tag.get_attribute("src")`.                 |
| ✅ Translate article titles using Google Translate API                  | ✅ Done     | Uses `googletrans` library to translate titles from Spanish to English.                 |
| ✅ Print translated headers                                             | ✅ Done     | Translated headers are saved to `articles_output.txt` and printed in output.            |
| ✅ Analyze translated headers for repeated words                        | ✅ Done     | Uses `collections.Counter` to find words with count > 2. Logged in scraper log.         |
| ✅ Run locally and verify functionality                                 | ✅ Done     | Code runs locally using `webdriver.Chrome()` or remote driver setup.                    |
| ✅ Run on BrowserStack across 5 parallel threads                        | ⚠️ Partial | Code runs on BrowserStack via `Remote()` but needs threading added for 5 parallel tests |
| ✅ Use free trial BrowserStack account                                  | ✅ Done     | Uses credentials stored via `os.getenv()`                                               |

