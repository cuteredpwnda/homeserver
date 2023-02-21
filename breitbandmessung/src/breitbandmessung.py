import os
import glob
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from dotenv import load_dotenv

load_dotenv()
FIREFOX_EXE = os.getenv('FIREFOX_EXE')

def get_data():
    # selectors
    stupid_location_selector = '.modal-body'
    decline_cookies_selector = '#allow-necessary'
    start_test_selector = 'button.btn:nth-child(4)'
    accept_policy_selector = 'button.btn:nth-child(2)'
    download_results_selector = 'button.px-0:nth-child(1)'

    # check if export folder exists, if not create it
    if not os.path.exists('../export'):
        os.makedirs('../export')
    download_path = os.path.abspath('../export')

    BASE_URL = 'https://breitbandmessung.de'
    url = BASE_URL + '/test'

    try:
        binary = FirefoxBinary(FIREFOX_EXE)

        options = Options()
        #options.headless = True
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.download.dir", download_path)

        driver = webdriver.Firefox(firefox_binary=binary, options=options)
        _set_viewport_size(driver, 1920, 1080)
    except Exception as e:
        print(f"[error: get data]\t{e}")

    driver.get(url)
    # wait until the modalbody disappears
    try:
        WebDriverWait(driver, 20).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, stupid_location_selector)))
    except TimeoutException as e:
        print(f"[error: get data]\t{e}")
        return

    # decline cookies
    try:
        decline_cookies = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, decline_cookies_selector)))
    except TimeoutException as e:
        print(f"[error: get data]\t{e}")
        return
    decline_cookies.click()

    # wait until the start test button is clickable
    try:
        wait = WebDriverWait(driver, 10)
        start_test = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, start_test_selector)))
    except TimeoutException as e:
        print(f"[error: get data]\t{e}")
        return
    start_test.click()

    # scroll down to the bottom of the page
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    # wait until the accept policy button is clickable
    accept_policy = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, accept_policy_selector)))
    accept_policy.click()

    print(f"[info: get data]\tTest started")

    # wait until the download results button is clickable and download the results
    download_results = WebDriverWait(driver, 60).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, download_results_selector)))
    print(f"[info: get data]\tTest finished")
    download_results.click()
    print(f"[info: get data]\tdownloaded result to {download_path}")
    driver.close()

def handle_data():
    # check if data.csv exists
    try:
        df = pd.read_csv('../export/data.csv')
    except FileNotFoundError:
        print("[error: handle data]\tNo data.csv found, creating it...")
        cols = ["Messzeitpunkt", "Download (Mbit/s)", "Upload (Mbit/s)", "Laufzeit (ms)",
                "Test-ID", "Version", "Betriebssystem", "Internet-Browser"]
        df = pd.DataFrame(columns=cols)
        df.to_csv('../export/data.csv', index=False)
    # get files in ../export
    files = glob.glob('../export/Breitbandmessung_*.csv')
    if not files:
        return
    # read all files
    dfs = [pd.read_csv(f, delimiter=";") for f in files]
    # fix dtypes, format date and Mbit/s to be float
    for df in dfs:
        df['Messzeitpunkt_formatted'] = df['Messzeitpunkt'].astype(str) + ' ' + df['Uhrzeit'].astype(str)
        df['Messzeitpunkt'] = pd.to_datetime(df['Messzeitpunkt_formatted'], format='%d.%m.%Y %H:%M:%S')
        df['Download (Mbit/s)'] = df['Download (Mbit/s)'].str.replace(',', '.').astype(float)
        df['Upload (Mbit/s)'] = df['Upload (Mbit/s)'].str.replace(',', '.').astype(float)
        df.drop(columns=['Uhrzeit', 'Messzeitpunkt_formatted'], inplace=True)
    # concat all files to the existing file
    try:
        existing = pd.read_csv('../export/data.csv')
    except FileNotFoundError:
        cols = ["Messzeitpunkt", "Download (Mbit/s)", "Upload (Mbit/s)", "Laufzeit (ms)",
                "Test-ID", "Version", "Betriebssystem", "Internet-Browser"]
        existing = pd.DataFrame(columns=cols)
    df = pd.concat([existing, *dfs])
    df.drop_duplicates(subset=['Test-ID'], inplace=True)
    df.to_csv('../export/data.csv', index=False)
    print(f"[info: handle data]\tRead {len(dfs)} files, wrote {len(df)} rows to output.")
    # remove all files in ./export that have been read
    for f in files:
        os.remove(f)

def _set_viewport_size(driver, width, height):
    window_size = driver.execute_script("""
        return [window.outerWidth - window.innerWidth + arguments[0],
          window.outerHeight - window.innerHeight + arguments[1]];
        """, width, height)
    driver.set_window_size(*window_size)

if __name__ == '__main__':
    get_data()
    handle_data()
