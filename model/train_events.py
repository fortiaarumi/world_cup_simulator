"""
train_events.py
===============
Entrena els models XGBoost per predir córners i targetes per partit.

FONT DE DADES: data/datos_historicos.csv (dades reals de partits)
Les columnes usades son mitjanes mòbils de les últimes 2 jornades:
  - avg_Córneres_2_Local / Visitante   → target proxy per córners
  - avg_Tarjetas_amarillas_2_Local / Visitante → target proxy per targetes

Nota: El CSV no conté valors per jornada concreta sinó mitjanes acumulades.
Per tant usem les mitjanes com a target de Poisson (lambda real) i
augmentem les dades amb soroll Poisson per generar mostres entrenables.
"""

import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
MODEL_DIR = Path(__file__).parent


def load_real_data():
    """
    Carrega datos_historicos.csv i construeix el dataset d'entrenament
    per córners i targetes basant-se en les columnes de mitjanes reals.
    """
    csv_path = DATA_DIR / "datos_historicos.csv"
    df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")

    # Columnes rellevants (amb noms originals en espanyol/català)
    col_corners_local     = "avg_Córneres_2_Local"
    col_corners_visitante = "avg_Córneres_2_Visitante"
    col_cards_local       = "avg_Tarjetas_amarillas_2_Local"
    col_cards_visitante   = "avg_Tarjetas_amarillas_2_Visitante"

    # Fallback si l'encoding provoca noms lleugerament diferents
    for col in df.columns:
        if "rneres" in col and "Local" in col:
            col_corners_local = col
        if "rneres" in col and "Visitante" in col:
            col_corners_visitante = col
        if "Tarjeta" in col and "Local" in col:
            col_cards_local = col
        if "Tarjeta" in col and "Visitante" in col:
            col_cards_visitante = col

    # Filtra files amb dades completes de córners i targetes
    needed = [col_corners_local, col_corners_visitante,
              col_cards_local, col_cards_visitante]
    df_clean = df.dropna(subset=needed).copy()

    print(f"  Files amb dades reals de córners+targetes: {len(df_clean)} / {len(df)}")

    # Aproximació del rank FIFA: usen 'diff_Puntos' (diferència de punts ELO)
    # i 'Prob_Implicita_ELO'. Usem un rank sintètic basat en Prob_ELO si existeix.
    if "Prob_Implicita_ELO" in df_clean.columns:
        # P(victòria local) alta → rank local millor (nombre baix)
        df_clean["team_rank"]    = (1 - df_clean["Prob_Implicita_ELO"]) * 100 + 1
        df_clean["opp_rank"]     = df_clean["Prob_Implicita_ELO"] * 100 + 1
    else:
        df_clean["team_rank"]    = 50.0
        df_clean["opp_rank"]     = 50.0

    df_clean["rank_diff"] = df_clean["opp_rank"] - df_clean["team_rank"]

    # Clipa les mitjanes a rangs físicament raonables
    df_clean["avg_corners_for_local"]  = df_clean[col_corners_local].clip(0, 15)
    df_clean["avg_corners_for_away"]   = df_clean[col_corners_visitante].clip(0, 15)
    df_clean["avg_cards_for_local"]    = df_clean[col_cards_local].clip(0, 10)
    df_clean["avg_cards_for_away"]     = df_clean[col_cards_visitante].clip(0, 10)

    return df_clean


def build_training_data(df_clean):
    """
    Construeix X/y per córners i targetes en perspectiva simètrica
    (cada fila apareix dues vegades: com a local i com a visitant).
    El target és la lambda real (la mitjana mòbil de les últimes 2 jornades),
    simulant la distribució Poisson real dels comptes.
    """
    np.random.seed(42)

    # --- CÓRNERS ---
    X_home = pd.DataFrame({
        "team_rank":               df_clean["team_rank"].values,
        "opp_rank":                df_clean["opp_rank"].values,
        "rank_diff":               df_clean["rank_diff"].values,
        "avg_corners_for":         df_clean["avg_corners_for_local"].values,
        "opp_avg_corners_against": df_clean["avg_corners_for_away"].values,
    })
    X_away = pd.DataFrame({
        "team_rank":               df_clean["opp_rank"].values,
        "opp_rank":                df_clean["team_rank"].values,
        "rank_diff":               (-df_clean["rank_diff"]).values,
        "avg_corners_for":         df_clean["avg_corners_for_away"].values,
        "opp_avg_corners_against": df_clean["avg_corners_for_local"].values,
    })
    X_corners = pd.concat([X_home, X_away], ignore_index=True)
    # Target: comptes Poisson mostrejats de la lambda real (mitjana mòbil)
    lam_corners = pd.concat([
        df_clean["avg_corners_for_local"],
        df_clean["avg_corners_for_away"]
    ], ignore_index=True).clip(1, 15)
    y_corners = np.random.poisson(lam_corners.values).astype(float)

    # --- TARGETES ---
    X_cards_home = pd.DataFrame({
        "team_rank":    df_clean["team_rank"].values,
        "opp_rank":     df_clean["opp_rank"].values,
        "rank_diff":    df_clean["rank_diff"].values,
        "avg_cards_for": df_clean["avg_cards_for_local"].values,
    })
    X_cards_away = pd.DataFrame({
        "team_rank":    df_clean["opp_rank"].values,
        "opp_rank":     df_clean["team_rank"].values,
        "rank_diff":    (-df_clean["rank_diff"]).values,
        "avg_cards_for": df_clean["avg_cards_for_away"].values,
    })
    X_cards = pd.concat([X_cards_home, X_cards_away], ignore_index=True)
    lam_cards = pd.concat([
        df_clean["avg_cards_for_local"],
        df_clean["avg_cards_for_away"]
    ], ignore_index=True).clip(0, 8)
    y_cards = np.random.poisson(lam_cards.values).astype(float)

    return X_corners, y_corners, X_cards, y_cards


def train_models():
    print("=" * 55)
    print("  ENTRENAMENT XGBoost — Córners i Targetes")
    print("  Font: data/datos_historicos.csv (dades reals)")
    print("=" * 55)

    df_clean = load_real_data()
    X_corners, y_corners, X_cards, y_cards = build_training_data(df_clean)

    print(f"\n  Mostres d'entrenament córners : {len(X_corners)}")
    print(f"  Mostres d'entrenament targetes: {len(X_cards)}")
    print(f"  Mitjana reals córners (target) : {y_corners.mean():.2f}")
    print(f"  Mitjana reals targetes (target): {y_cards.mean():.2f}")

    # --- Model Córners ---
    print("\n  Entrenant XGBoost Córners (count:poisson)...")
    xgb_corners = xgb.XGBRegressor(
        objective="count:poisson",
        n_estimators=200,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    xgb_corners.fit(X_corners, y_corners)

    # --- Model Targetes ---
    print("  Entrenant XGBoost Targetes (count:poisson)...")
    xgb_cards = xgb.XGBRegressor(
        objective="count:poisson",
        n_estimators=200,
        learning_rate=0.05,
        max_depth=3,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    xgb_cards.fit(X_cards, y_cards)

    # --- Desa models ---
    with open(MODEL_DIR / "xgb_corners.pkl", "wb") as f:
        pickle.dump(xgb_corners, f)
    with open(MODEL_DIR / "xgb_cards.pkl", "wb") as f:
        pickle.dump(xgb_cards, f)

    print(f"\n  OK Models desats a: {MODEL_DIR}")

    # Validació ràpida
    from sklearn.metrics import mean_absolute_error
    pred_corners = xgb_corners.predict(X_corners)
    pred_cards   = xgb_cards.predict(X_cards)
    print(f"  MAE Córners (train) : {mean_absolute_error(y_corners, pred_corners):.3f}")
    print(f"  MAE Targetes (train): {mean_absolute_error(y_cards, pred_cards):.3f}")
    print("=" * 55)


if __name__ == "__main__":
    train_models()
