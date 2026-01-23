# Expects "scripts/generate_alphabet_urls.py" to be run first
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from pathlib import Path

# make ticker common access (import reference)
tickers = ["GOOG", "GOOGL"]
ticker = "GOOG"
urls = pd.read_csv(f"data/{ticker}/urls.csv", index_col=0)["url"].to_list()

driver = webdriver.Chrome()

def get_diluted_eps(url):
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ixvFrame")))
    print("Going to sleep")
    time.sleep(5) # give time for iframe to fully load
    print("Waking up")

    html_page = driver.find_element(By.CSS_SELECTOR, "body").get_attribute("innerHTML")
    soup = BeautifulSoup(html_page, features="html.parser")

    diluted_eps_container = soup.select("span:-soup-contains('Diluted EPS')")[0].parent.parent.parent
    container_vals = diluted_eps_container.select("td:-soup-contains('.')") # Diluted EPS in the form "XX.XX"

    prev_year_eps = container_vals[0].span.text.strip()
    current_year_eps = container_vals[1].span.text.strip()

    return (float(prev_year_eps), float(current_year_eps))

prev_year_eps, current_year_eps = list(), list()
for i, url in enumerate(urls):
    print("URL #", i)
    print("Looking at ", url)
    prev_eps, current_eps = get_diluted_eps(url)
    prev_year_eps.append(prev_eps)
    current_year_eps.append(current_eps)

historical_eps = pd.DataFrame({
    "prev_year_eps": prev_year_eps,
    "current_year_eps": current_year_eps,
})

for ticker in tickers:
    historical_eps.to_csv(f"data/{ticker}/historical_eps.csv")