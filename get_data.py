# Plan for this project
# 1. Create webscrapper to gather team data
#   - using playwright (alternative to selenium) which allows us to grab html elements from the page
#   - was originally trying to use playwrights async functionality but windows is giving me an error, so we're
#   - going to use the synchronous version now
#   - sync also doesn't work in jupyter notebooks, so we have to use a regular .py file in pycharm
# 2. Use this data to predict games in the upcoming season
# 3. Create a new dataset with the predicted data
# 4. Predict which team will be the NBA Champions in 2025

import os
import time

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

# seasons that we will be pulling from
SEASONS = list(range(2016, 2025))

# created pointers to the path for each data category
DATA_DIR = "data"
STANDINGS_DIR = os.path.join(DATA_DIR, "standings")
SCORES_DIR = os.path.join(DATA_DIR, "scores")


# playwright works asynchronously, so we have to deal with that
# playwright opens up a web browser on a different thread
# since windows wasn't allowing us to use async properly with playwright,
# we're going to use sync now
def get_html(url, selector, sleep=5, retries=3):
    html = ""
    for i in range(1, retries + 1):
        # pauses our program for a few seconds
        # so the webscapper doesn't get blacklisted from the website
        time.sleep(sleep * i)
        try:
            # initializes our playwright instance for us
            with sync_playwright() as p:
                # launches chromium which is the open source version of chrome
                browser = p.chromium.launch()
                # waits for browsers page to load up
                page = browser.new_page()
                # awaits url response
                page.goto(url)
                # for checking progress
                print(page.title())
                # html that we were looking for from the page
                html = page.inner_html(selector)
        # this error is given by playwright if the page timed out or server banned us
        except PlaywrightTimeout:
            print(f"Timeout error on {url}")
            continue
            # gets executed when the try succeeds and breaks us out with the html info we need
        else:
            break
    return html


# scrapes all the seasons
def scrape_season(season):
    url = f"https://www.basketball-reference.com/leagues/NBA_{season}_games.html"
    html = get_html(url, "#content .filter")

    soup = BeautifulSoup(html, features="html.parser")
    links = soup.find_all("a")
    href = [l["href"] for l in links]
    standing_pages = [f"https://www.basketball-reference.com{l}" for l in href]

    for url in standing_pages:
        save_path = os.path.join(STANDINGS_DIR, url.split("/")[-1])
        if os.path.exists(save_path):
            continue

        html = get_html(url, "#all_schedule")
        with open(save_path, "w+") as f:
            f.write(html)


for season in SEASONS:
    scrape_season(season)

standings_files = os.listdir(STANDINGS_DIR)


def scrape_game(standings_file):
    with open(standings_file, "r") as f:
        html = f.read()

    soup = BeautifulSoup(html, features="html.parser")
    links = soup.find_all("a")
    hrefs = [l.get("href") for l in links]
    box_scores = [l for l in hrefs if l and "boxscore" in l and ".html" in l]
    box_scores = [f"https://www.basketball-reference.com{l}" for l in box_scores]

    for url in box_scores:
        save_path = os.path.join(SCORES_DIR, url.split("/")[-1])
        if os.path.exists(save_path):
            continue
        html = get_html(url, "#content")
        if not html:
            continue
        with open(save_path, "w+", encoding="utf-8") as f:
            f.write(html)


standings_files = [f for f in standings_files if ".html" in f]

for f in standings_files:
    file_path = os.path.join(STANDINGS_DIR, f)

    scrape_game(file_path)

for season in SEASONS:
    files = [s for s in standings_files if str(season) in s]

    for f in files:
        filepath = os.path.join(STANDINGS_DIR, f)

        scrape_game(filepath)
