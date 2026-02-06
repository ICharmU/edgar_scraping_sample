# Expects "scripts/generate_alphabet_urls.py" to be run first
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import sys
import re
from datetime import datetime
import time
from word2number import w2n


ticker = sys.argv[1]
urls = pd.read_csv(f"data/{ticker}/urls.csv", index_col=0)["url"].to_list()
form_type = pd.read_csv(f"data/{ticker}/urls.csv", index_col=0)["form"].to_list()

driver = webdriver.Chrome()

def parse_recent_date(raw_dates: str):
    for i, raw_date_text in enumerate(raw_dates):
        date = f"{raw_date_text[0]}, {raw_date_text[1]} {raw_date_text[2]}"
        dt_date_format = r"%B, %d %Y"
        date = datetime.strptime(date, dt_date_format)
        raw_dates[i] = date
    
    latest_date = max(raw_dates)
    s_date_format = r"%Y-%m-%d"
    latest_date = latest_date.strftime(s_date_format)
    return latest_date

def get_diluted_eps(url):
    driver.get(url)
    # TODO - are older urls formatted differently from new urls?
    # Old urls don't have XML support and take the bulk of scraping time
    wait = WebDriverWait(driver, 5)
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "ixvFrame")))

    diluted_eps_name = "us-gaap:EarningsPerShareDiluted"
    wait.until(EC.presence_of_element_located((By.XPATH, f"//*['ix:nonfraction'][@name='{diluted_eps_name}']")))
    time.sleep(1)   

    html_page = driver.find_element(By.CSS_SELECTOR, "body").get_attribute("innerHTML")
    soup = BeautifulSoup(html_page, "lxml")

    diluted_eps_container = soup.find_all("ix:nonfraction", attrs=dict(name=diluted_eps_name), limit=2)
    soup_html = diluted_eps_container[0].find_parent("tbody")

    prev_year_eps = diluted_eps_container[1].text.strip()
    current_year_eps = diluted_eps_container[0].text.strip()

    # Find stock splits
    stock_ratio = ("one", "one")
    stock_split_date = None
    try:
        split_regex = r" .+?-for-.+? stock split"
        split_container = soup.find("span", string=re.compile(split_regex))
        stock_ratio = split_container.text # throws exception when there is no split
        raw_dates = re.findall(r" ([a-zA-Z]{3,9}) ([1-9]|[1-2][0-9]|[3][0-1]), ([0-9]{4})", stock_ratio)
        stock_split_date = parse_recent_date(raw_dates)
        # print(f"Stock split date {stock_split_date}")
        stock_ratio = re.search(r" ([a-zA-Z]+)-for-([a-zA-Z]+) ", stock_ratio)[0].strip().split("-")
        stock_ratio = (stock_ratio[0], stock_ratio[2])
        # print("Most recent date is:", stock_split_date)
        # print(f"Full split text: {stock_ratio}")
    except Exception as e:
        # print(e)
        pass

    if len(stock_ratio) != 2:
        stock_ratio = ("one", "one")

    stock_ratio = tuple(w2n.word_to_num(s_num) for s_num in stock_ratio)
    # print(f"Stock split ratios {stock_ratio}")
    return (float(prev_year_eps), float(current_year_eps), stock_ratio, stock_split_date, soup_html)

# 10K Start
splitter_10k = "##"

def get_diluted_eps_text(soup_html):
    """
    Parses raw html into html text.
    Text in different divs are separated by '##'
    """
    text = soup_html.find_all("span")
    text = splitter_10k.join([span.text.strip() for span in text])
    
    return text

from pydantic import BaseModel, Field
import ollama
import json

class FindYears(BaseModel):
    year: list[int] = Field(ge=1990, le=2030)
    basic: list[float]
    diluted: list[float]

schema = FindYears.model_json_schema()

def get_10k_eps(raw_html):
    text = get_diluted_eps_text(raw_html)

    agent_prompt = f"""
    Only find information from 12 months ended. 
    Each X months ended includes current year and previous year.

    Find years. 
    Find basic net income (earnings) PER SHARE.
    Find diluted net income (earnings) PER SHARE. 
    The values you return are consecutive, by feature.
    The feature name is placed before consecutive values.

    Items are separated by '{splitter_10k}'
    """

    response = ollama.chat(
        model='gemma3:4b',
        format=schema,
        messages=[{
        'role': 'system',
        "content": text,
        },
        {
        'role': 'user',
        'content': agent_prompt,
        }],
        options = {
            "temperature": 0,
            "num_gpu": 20,
        }
    ).message.content

    diluted_eps = json.loads(response)
    diluted_eps = pd.DataFrame(diluted_eps).sort_values(by="year", ascending=False).reset_index(drop=True)

    recent_eps = diluted_eps["diluted"].iloc[:2].to_numpy()
    # print("recent eps was", recent_eps)
    prev_year_eps, curr_year_eps = recent_eps

    return prev_year_eps, curr_year_eps

# 10K End


prev_year_eps, current_year_eps = list(), list()
stock_ratio_given, stock_ratio_per, stock_split_date = list(), list(), list()
for i, url in enumerate(urls[:]):
    curr_form = form_type[i]
    # print("URL #", i)
    # print("Looking at ", url)
    # print(f"This is a {form_type[i]}")
    try:
        prev_eps, current_eps, curr_stock_ratio, split_date, raw_html = get_diluted_eps(url)
        if curr_form == "10-K":
            prev_eps, current_eps = get_10k_eps(raw_html)
        prev_year_eps.append(prev_eps)
        current_year_eps.append(current_eps)
        stock_ratio_given.append(curr_stock_ratio[0])
        stock_ratio_per.append(curr_stock_ratio[1])
        stock_split_date.append(split_date)

    except Exception as e:
        print(f"Looking at {url}")
        print(f"Failed to parse #URL #{i}")
        # print(e)
        prev_year_eps.append(None)
        current_year_eps.append(None)
        stock_ratio_given.append(None)
        stock_ratio_per.append(None)
        stock_split_date.append(None)
    time.sleep(0.1) # Limit of 10 requests/s

historical_eps = pd.DataFrame({
    "prev_year_eps": prev_year_eps,
    "curr_year_eps": current_year_eps,
    "stock_ratio_given": stock_ratio_given, # number of shares currently received
    "stock_ratio_taken": stock_ratio_per, # equivalent number of shares in the previous quarter
    "split_date": stock_split_date,
})

historical_eps.to_csv(f"data/{ticker}/historical_eps.csv")
print(f"Saved ticker {ticker} to csv")