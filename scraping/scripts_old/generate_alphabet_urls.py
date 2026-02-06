# EDGAR Rate Limits : Current max request rate: 10 requests/second.
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd

# Retrieve JSON for Alphabet
cik = "0001652044"
company_json_url = rf"https://data.sec.gov/submissions/CIK{cik}.json"
driver = webdriver.Chrome()
driver.get(company_json_url)
company_large_json_string = driver.find_element(By.TAG_NAME, "pre").get_attribute("innerHTML")
driver.quit()
company_json = json.loads(company_large_json_string)

# Load JSON into a dataframe
recent_filings = company_json["filings"]["recent"]
features = ["accessionNumber", "filingDate", "reportDate", "primaryDocument", "form"]
form_access_data = {feat: recent_filings[feat] for feat in features}
form_access_data.update({
    "fiscalYearEnd": company_json["fiscalYearEnd"],
})
num_tickers = len(company_json["tickers"])
form_access_data.update({
    f"ticker{i+1}": ticker for i, ticker in enumerate(company_json["tickers"])
})

df = pd.DataFrame(form_access_data)
cik = company_json["cik"]

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

    tickers = [f"ticker{i+1}" for i in range(num_tickers)]
    return df[["url", "filingDate", "reportDate", "form", "fiscalYearEnd"] + tickers]

ten_k_forms = df.query(f"form.str.contains('10-K') or form.str.contains('10-Q')").reset_index(drop=True)
urls = create_filing_urls(ten_k_forms)

# make ticker common access
tickers = urls.loc[0,"ticker1":]

from pathlib import Path

for ticker in tickers:
    path = Path(f"data/{ticker}")
    path.mkdir(parents=True, exist_ok=True)

for ticker in tickers:
    urls.to_csv(f"data/{ticker}/urls.csv", index=True, header=True)