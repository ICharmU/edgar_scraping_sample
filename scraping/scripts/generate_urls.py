# EDGAR Rate Limits : Current max request rate: 10 requests/second.
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import sys

# Retrieve JSON
cik = sys.argv[1]
ticker = sys.argv[2]
json_url = rf"https://data.sec.gov/submissions/CIK{cik}.json"
driver = webdriver.Chrome()
driver.get(json_url)
large_json_string = driver.find_element(By.TAG_NAME, "pre").get_attribute("innerHTML")
driver.quit()
company_json = json.loads(large_json_string)

# Load JSON into a dataframe
recent_filings = company_json["filings"]["recent"]
features = ["accessionNumber", "filingDate", "reportDate", "primaryDocument", "form"]
form_access_data = {feat: recent_filings[feat] for feat in features}
form_access_data.update({
    "fiscalYearEnd": company_json["fiscalYearEnd"],
    "ticker": ticker,
})

df = pd.DataFrame(form_access_data)

def create_filing_urls(df):
    """
    Returns a list of valid SEC urls
    """
    df = df.copy()
    df["accessionNumber"] = df["accessionNumber"].str.split("-")
    df["cik"] = cik + "/"
    df["dir2"] = df["accessionNumber"].apply("".join) + "/"

    df["url"] = (
        "https://www.sec.gov/ix?doc=/Archives/edgar/data/" +
        df["cik"] +
        df["dir2"] +
        df["primaryDocument"]
    )

    return df[["url", "filingDate", "reportDate", "form", "fiscalYearEnd", "ticker"]]

ten_k_forms = df.query(f"form.str.contains('10-K') or form.str.contains('10-Q')").reset_index(drop=True)
urls = create_filing_urls(ten_k_forms)

from pathlib import Path

path = Path(f"data/{ticker}")
path.mkdir(parents=True, exist_ok=True)

urls.to_csv(f"data/{ticker}/urls.csv", index=True, header=True)