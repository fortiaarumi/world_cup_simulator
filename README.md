# FIFA World Cup 2026 — Live Prediction & Simulation Model

An end-to-end simulation and live prediction system for the 2026 FIFA World Cup. This project combines a **Poisson regression goal model** (trained on 7 World Cups of historical data) with a **live web scraper** that ingests real match statistics as the tournament progresses. By updating team strengths dynamically, it generates highly accurate predictions for each knockout round and presents them in professional PDF reports.

## System Architecture

The project consists of three main pillars:
1. **The Machine Learning Engine**: A Poisson regression model that evaluates offensive and defensive strengths.
2. **The Data Pipeline (Web Scraper)**: A Selenium-based scraper that updates match results, expected goals (xG), corners, and cards from live tournament data.
3. **The Report Generator**: A PDF generator that runs Monte Carlo simulations and outputs predictions for upcoming matches.

---

## 1. Match Prediction Model

Each match is simulated by predicting the expected goals for both teams using a **Poisson regression model**, then sampling a scoreline from a bivariate Poisson distribution with a Dixon-Coles correction for low-scoring outcomes.

### Dynamic Ranks (Elo-style updating)
Three dynamic ranks are tracked per team throughout the tournament, all starting at the team's pre-tournament FIFA ranking:

- **General rank**: Updated after each match based on the result vs opponent quality.
- **Offensive rank**: Updated based on goals scored relative to the opponent's general quality. 
- **Defensive rank**: Updated based on goals conceded. Used as the opponent's defensive component in the prediction feature.

Update magnitude scales with `log(1 + |rank_diff|)` — meaning unexpected upsets produce larger adjustments to a team's rating.

### Mean Reversion
After each rank update, the dynamic rank is pulled partway back toward the team's base FIFA ranking. Without reversion, a single fluky result in a short tournament can swing the rank far enough to distort all subsequent predictions. Mean reversion anchors each dynamic rank to our best prior.

---

## 2. Live Data Pipeline (The Scraper)

To keep the model completely up to date with the reality of the 2026 World Cup, the system uses a live web scraper (`data_scraper.py`). 

As matches conclude, the scraper visits Flashscore match URLs to extract:
- **Full-Time Scorelines**
- **Expected Goals (xG)**
- **Corners & Cards**

This data is saved locally into `data/live_stats_2026.json`. The script `update_live_ranks.py` then ingests this file to automatically recalculate the Dynamic Ranks (Elo) of every team based on their actual performance in the tournament.

---

## 3. Knockout Round Predictions & PDF Reports

For each stage of the knockout phase, the system generates a comprehensive PDF report using Python's `fpdf2` library.

The report includes:
- **Exact Match Predictions**: Win probabilities, Expected Goals (xG), and top 5 most likely exact scores.
- **Advanced Betting Markets**: Both Teams to Score (BTTS), Over/Under goals, corners, and cards projections.
- **Monte Carlo Simulations**: A 100,000-iteration Monte Carlo simulation of the remaining tournament bracket to calculate the percentage chance of each team winning the entire World Cup.

---

## Setup & Usage

### 1. Install dependencies

```bash
python -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

### 2. Update Live Data

During the tournament, add the Flashscore URLs of the completed matches to a text file (e.g., `data/ro16_urls.txt`). Then run:

```bash
# 1. Scrape the latest match data
python data_scraper.py data/ro16_urls.txt

# 2. Recalculate team Elo rankings based on the new results
python update_live_ranks.py
```

### 3. Generate Predictions

Generate the PDF reports for the upcoming round. The script automatically pairs the advancing teams and runs the Monte Carlo simulations.

```bash
# For Round of 16
python generate_ro16_report.py

# For Quarter-finals
python generate_ro8_report.py
```

The output will be saved as a highly detailed PDF (e.g., `Prediccions_Quarts_CAT_WC2026.pdf`) in the project root.
