import os
import re
import time
import traceback
from io import TextIOWrapper

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from parser import lichess_download, scrap_livechess

download_directory = os.path.expanduser("~/Pobrane")
os.makedirs(download_directory, exist_ok=True)

options = Options()
options.page_load_strategy = "eager"  # type: ignore[attr-defined]
options.add_argument(
    "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36"
)
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
# options.add_argument("--disable-javascript")
browser = uc.Chrome(version_main=156, options=options)

countries = [
    "POL",
]


def process_tournament(tournament: str, output: TextIOWrapper) -> None:
    browser.get(tournament)
    time.sleep(3)
    try:
        links = browser.find_elements(By.TAG_NAME, "a")
        lichess_links = [
            link.get_attribute("href")
            for link in links
            if link.get_attribute("href") is not None
            and "lichess.org/broadcast/" in link.get_attribute("href")
        ]
        livechess_links = [
            link.get_attribute("href")
            for link in links
            if link.get_attribute("href") is not None
            and "view.livechesscloud.com" in link.get_attribute("href")
        ]
        for lichess_link in lichess_links:
            print("lichess: " + lichess_link)
            try:
                output.write(lichess_download(lichess_link))
            except Exception:
                print("Error downloading: " + lichess_link)

        for livechess_link in livechess_links:
            print("livechess: " + livechess_link)
            try:
                output.write(scrap_livechess(livechess_link))
            except Exception:
                print("Error downloading: " + livechess_link)

    except TypeError as e:
        print(e)
        traceback.print_exc()


def try_agree(browser: uc.Chrome) -> None:
    try:
        btn_download = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "body > div.fc-consent-root > div.fc-dialog-container > div.fc-dialog.fc-choice-dialog > "
                    "div.fc-footer-buttons-container > div.fc-footer-buttons > button.fc-button.fc-cta-consent.fc-primary-button "
                    "> p",
                )
            )
        )
        time.sleep(0.5)
        btn_download.click()
    except Exception:
        pass


def process_pseudo_human(output: TextIOWrapper) -> None:
    for country in countries:
        try:
            browser.get(
                f"https://www.chessmanager.com/pl/tournaments/finished?country={country}"
            )
            try_agree(browser)

            last_elem = browser.find_element(
                By.CSS_SELECTOR,
                "body > div.pusher > main > div > div.twelve.wide.column > "
                "div.ui.centered.pagination.menu > a:nth-child(8)",
            )
            try:
                last_elem_value = int(last_elem.text)
            except ValueError:
                last_elem_value = 1

            for i in range(last_elem_value + 1):
                browser.get(
                    f"https://www.chessmanager.com/pl/tournaments/finished?country={country}&city=&city_radius=0&offset={i * 50}"
                )
                try_agree(browser)
                tournaments = [
                    link.get_attribute("href")
                    for link in browser.find_elements(By.TAG_NAME, "a")
                    if re.match(
                        r"https://www\.chessmanager\.com/[\w-]*/tournaments/\d+",
                        link.get_attribute("href"),
                    )
                ]
                for tournament in tournaments:
                    process_tournament(tournament, output)

                time.sleep(6)

        except Exception as e:
            print(e)
            traceback.print_exc()


def process_bot(output: TextIOWrapper) -> None:
    browser.get("https://www.chessmanager.com/en-us/tournaments/sitemap.xml")

    locs = browser.find_elements(By.XPATH, "//*[local-name()='loc']")
    urls = [node.get_attribute("textContent") for node in locs]

    for url in urls:
        process_tournament(url, output)


def main() -> None:
    with open("chessmanager.pgn", "a") as output:
        process_bot(output)

        while check_for_crdownload_files(download_directory):
            print("Waiting for downloads to complete...")
            time.sleep(10)  # Dodatkowe zabezpieczenie

        try:
            input("chessmanager czeka na kliknięcie klawisza")
        except Exception as e:
            print(e)
            traceback.print_exc()
    browser.quit()


def check_for_crdownload_files(folder_path: str) -> bool:
    crdownload_files = [f for f in os.listdir(folder_path) if f.endswith(".crdownload")]
    return len(crdownload_files) > 0


if __name__ == "__main__":
    main()
