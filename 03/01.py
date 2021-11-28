import argparse
import re
from typing import List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


def find_emails_in_links(driver: WebDriver) -> List[str]:
    return [x.get_attribute("href").replace("mailto:", "")
            for x in driver.find_elements(By.XPATH, "//a[contains(@href,'mailto:')]")]


def find_emails_in_page_content(driver: WebDriver) -> List[str]:
    return re.findall(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9]+(?:\.[a-zA-Z0-9-]+)*", driver.page_source)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs=1, metavar='URL', help='initial URL to parse')
    args = parser.parse_args()

    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    driver = None
    try:
        driver = webdriver.Firefox(options=options)
        driver.get(args.url[0])

        emails_links = find_emails_in_links(driver)
        emails_content = find_emails_in_page_content(driver)
        emails = set(emails_links).union(set(emails_content))
        [print(e) for e in emails]

    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    main()
