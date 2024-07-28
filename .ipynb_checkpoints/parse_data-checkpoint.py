import os
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
import lxml

SCORE_DIR = "data/scores"
# %%
box_scores = os.listdir(SCORE_DIR)
box_scores = [os.path.join(SCORE_DIR, f) for f in box_scores if f.endswith(".html")]
# %%


def parse_html(box_score):
    with open(box_score, encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, features="lxml")
    # remove the html elements tr.over_header and tr.thead
    [s.decompose() for s in soup.select("tr.over_header")]
    [s.decompose() for s in soup.select("tr.thead")]
    return soup


# %%
def read_season_info(soup):
    # find all a tags
    nav = soup.select("#bottom_nav_container")[0]
    hrefs = [a["href"] for a in nav.find_all('a')]
    season = os.path.basename(hrefs[1]).split("_")[0]
    return season


# %%
def read_line_score(soup):
    # getting the teams that won and lost and the total points of each team
    html_str = str(soup)
    line_score = pd.read_html(StringIO(html_str), attrs={'id': 'line_score'})[0]
    cols = list(line_score.columns)
    cols[0] = "team"
    cols[-1] = "total"
    line_score.columns = cols

    line_score = line_score[["team", "total"]]

    return line_score


def read_stats(soup, team, stat):
    # read the advanced stats for the game
    html_str = str(soup)
    try:
        df = pd.read_html(StringIO(html_str), attrs={'id': f'box-{team}-game-{stat}'}, index_col=0)[0]
        df = df.apply(pd.to_numeric, errors="coerce")
    except ValueError as e:
        print(f"Error reading stats for team {team}, stat {stat}: {e}")
        print(f"HTML content: {html_str[:500]}")  # Print a portion of the HTML content for inspection
        return None
    return df



games = []
base_cols = None
for i, box_score in enumerate(box_scores):
    current_file = box_score
    try:
        print(f"Processing file {i + 1}/{len(box_scores)}: {box_score}")
        soup = parse_html(box_score)
        line_score = read_line_score(soup)
        teams = list(line_score["team"])

        summaries = []
        for team in teams:
            basic = read_stats(soup, team, "basic")
            advanced = read_stats(soup, team, "advanced")

            if basic is None or advanced is None:
                print(f"Skipping file {box_score} due to missing data for team {team}")
                continue

            totals = pd.concat([basic.iloc[-1, :], advanced.iloc[-1, :]])
            totals.index = totals.index.str.lower()

            maxes = pd.concat([basic.iloc[:-1].max(), advanced.iloc[:-1].max()])
            maxes.index = maxes.index.str.lower() + "_max"

            summary = pd.concat([totals, maxes])

            if base_cols is None:
                base_cols = list(summary.index.drop_duplicates(keep="first"))
                base_cols = [b for b in base_cols if "bpm" not in b]

            summary = summary[base_cols]

            summaries.append(summary)
        summary = pd.concat(summaries, axis=1).T

        game = pd.concat([summary, line_score], axis=1)

        game["home"] = [0, 1]

        game_opp = game.iloc[::-1].reset_index()
        game_opp.columns += "_opp"

        full_game = pd.concat([game, game_opp], axis=1)
        full_game["season"] = read_season_info(soup)

        full_game["date"] = os.path.basename(box_score)[:8]
        full_game["date"] = pd.to_datetime(full_game["date"], format="%Y%m%d")

        full_game["won"] = full_game["total"] > full_game["total_opp"]
        games.append(full_game)

        if len(games) % 100 == 0:
            print(f"{len(games)} / {len(box_scores)}")

    except Exception as e:
        print(f"Error processing {box_score}: {e}")


games_df = pd.concat(games, ignore_index=True)

games_df.to_csv("nba_games.csv")