# -*- coding: utf-8 -*-
"""
predict_direct.py
=================
Predicció analítica directa de partits del Mundial 2026.

Usa el model de regressió de Poisson entrenat (model/expanded_model.pkl) i la
matriu bivariant de Dixon-Coles per calcular probabilitats exactes de marcador,
victòria/empat/derrota per a partits concrets — sense Monte Carlo.

Ús:
    .env\\Scripts\\python predict_direct.py

======================================================================
 SECCIÓ DE PARÀMETRES EDITABLES PER L'USUARI
 Modifica aquests valors per reflectir la forma real post-fase de grups.
 Els valors per defecte provenen de data/wc_2026_teams.json.
 
 Estructura de cada equip:
   - name         : nom exacte de l'equip
   - confederation: confederació (UEFA, CONMEBOL, AFC, CONCACAF, CAF, OFC)
   - fifa_rank    : ranking FIFA oficial (base)
   - host         : True si és país amfitrió (avantatge de camp)
   
   # Ranks dinàmics (a ajustar manualment per l'estat de forma real):
   - current_rank : rank dinàmic actual (per defecte = fifa_rank)
                    BAIXAR el número = millor forma, PUJAR = pitjor forma
   - current_off_rank: rank ofensiu (defecte = fifa_rank)
                    BAIXAR = millor atac (marcant més del previst)
   - current_def_rank: rank defensiu (defecte = fifa_rank)
                    BAIXAR = millor defensa (encaixant menys del previst)
======================================================================
"""

# ─────────────────────────────────────────────────────────────────────────────
#  PARTITS A ANALITZAR  →  edita la llista per afegir-ne més
# ─────────────────────────────────────────────────────────────────────────────
MATCHES_TO_PREDICT = [
    ("Brazil", "Japan", "Partit 1: Vuitens de Final"),
    ("Germany", "Paraguay", "Partit 2: Vuitens de Final"),
]

import json
from pathlib import Path

_live_ranks_cache = None
def get_live_team(name):
    global _live_ranks_cache
    if _live_ranks_cache is None:
        live_ranks_path = Path(__file__).parent / "data" / "live_ranks.json"
        if live_ranks_path.exists():
            with open(live_ranks_path, encoding='utf-8') as f:
                _live_ranks_cache = json.load(f)
        else:
            _live_ranks_cache = {}

    if name in _live_ranks_cache:
        return _live_ranks_cache[name]
    
    return {
        "name": name,
        "confederation": "UNKNOWN",
        "fifa_rank": 50,
        "host": False,
        "current_rank": 50.0,
        "current_off_rank": 50.0,
        "current_def_rank": 50.0,
    }

MATCHES = [
    {
        "label": label,
        "home": get_live_team(t1),
        "away": get_live_team(t2),
        "stage_weight": 1,
        "is_knockout": True,
    } for t1, t2, label in MATCHES_TO_PREDICT
]

# ─────────────────────────────────────────────────────────────────────────────
#  PARÀMETRES DEL MODEL  (no cal editar llevat que vulguis experimentar)
# ─────────────────────────────────────────────────────────────────────────────
RHO         = -0.1   # Paràmetre Dixon-Coles (negatiu → infla les probabilitats d'empat)
MAX_GOALS   = 7      # Rang màxim de gols per equip en la matriu bivariant
TOP_N_SCORES = 5     # Quants marcadors exactes mostrar per partit

# ─────────────────────────────────────────────────────────────────────────────
#  IMPORTS I LÒGICA PRINCIPAL  (no cal editar)
# ─────────────────────────────────────────────────────────────────────────────
import io
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.stats import poisson

# Afegim el directori arrel i model al path perquè els transformers siguin
# importables tal com fa el propi engine del projecte.
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "model"))

# Força la sortida en UTF-8 per suportar caràcters especials a Windows
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

STRONG_CONFEDS = {"UEFA", "CONMEBOL"}


def load_model():
    """Carrega el model Poisson entrenat (expanded_model.pkl)."""
    model_path = PROJECT_ROOT / "model" / "expanded_model.pkl"
    with open(model_path, "rb") as f:
        artifact = pickle.load(f)
    return artifact


def build_feature_row(team: dict, opponent: dict, stage_weight: int) -> np.ndarray:
    """
    Construeix el vector de 15 features per a una perspectiva (team vs opponent).

    Ordre exacte de FEATURE_COLUMNS de model/train.py:
        rank, opp_rank,
        cur_rank, opp_cur_rank,
        rank_shift, opp_rank_shift,
        off_rank, opp_off_rank,
        def_rank, opp_def_rank,
        host, opp_host,
        is_strong_confed, opp_is_strong_confed,
        stage_weight
    """
    rank           = float(team["fifa_rank"])
    opp_rank       = float(opponent["fifa_rank"])
    cur_rank       = float(team["current_rank"])
    opp_cur_rank   = float(opponent["current_rank"])
    rank_shift     = cur_rank - rank
    opp_rank_shift = opp_cur_rank - opp_rank
    off_rank       = float(team["current_off_rank"])
    opp_off_rank   = float(opponent["current_off_rank"])
    def_rank       = float(team["current_def_rank"])
    opp_def_rank   = float(opponent["current_def_rank"])
    host           = 1.0 if team["host"] else 0.0
    opp_host       = 1.0 if opponent["host"] else 0.0
    is_strong      = 1.0 if team["confederation"] in STRONG_CONFEDS else 0.0
    opp_is_strong  = 1.0 if opponent["confederation"] in STRONG_CONFEDS else 0.0

    return np.array([[
        rank, opp_rank,
        cur_rank, opp_cur_rank,
        rank_shift, opp_rank_shift,
        off_rank, opp_off_rank,
        def_rank, opp_def_rank,
        host, opp_host,
        is_strong, opp_is_strong,
        float(stage_weight),
    ]])


def build_prob_matrix(lambda_home: float, lambda_away: float,
                      rho: float = -0.1, max_goals: int = 7) -> np.ndarray:
    """
    Matriu de probabilitats bivariant Dixon-Coles normalitzada.
    
    Aplica la correcció Dixon-Coles als 4 marcadors de baix golejat
    (0-0, 0-1, 1-0, 1-1) per compensar la infra-predicció d'empats dels
    models de Poisson independents.
    
    Returns:
        Array (max_goals × max_goals) normalitzat a suma = 1.0
    """
    goals = np.arange(max_goals)
    home_pmf = poisson.pmf(goals, lambda_home)
    away_pmf = poisson.pmf(goals, lambda_away)
    matrix = np.outer(home_pmf, away_pmf)

    # Correcció Dixon-Coles per als marcadors de 0 i 1 gols
    matrix[0, 0] *= max(0.0001, 1 - lambda_home * lambda_away * rho)
    matrix[0, 1] *= max(0.0001, 1 + lambda_home * rho)
    matrix[1, 0] *= max(0.0001, 1 + lambda_away * rho)
    matrix[1, 1] *= max(0.0001, 1 - rho)

    # Renormalitzar
    matrix /= matrix.sum()
    return matrix


def predict_match(home: dict, away: dict, pipeline,
                  stage_weight: int = 1, is_knockout: bool = True,
                  rho: float = -0.1, max_goals: int = 7, top_n: int = 5):
    """
    Executa el model Poisson per a un enfrontament i retorna:
        - lambda_home, lambda_away: gols esperats
        - prob_matrix: matriu de probabilitats bivariant
        - p_home_win, p_draw, p_away_win: probabilitats finals
        - top_scores: llista de (h, a, prob) dels N marcadors més probables
    """
    # Predicció de gols esperats via pipeline
    feat_home = build_feature_row(home, away, stage_weight)
    feat_away = build_feature_row(away, home, stage_weight)
    lambda_home = float(pipeline.predict(feat_home)[0])
    lambda_away = float(pipeline.predict(feat_away)[0])

    # Matriu bivariant Dixon-Coles
    matrix = build_prob_matrix(lambda_home, lambda_away, rho, max_goals)

    # En partits d'eliminatòries: anul·lem la diagonal (empats → temps extra)
    # i renormalitzem per calcular la probabilitat de guanyar en 90 min.
    if is_knockout:
        matrix_90 = matrix.copy()
        np.fill_diagonal(matrix_90, 0.0)
        matrix_90 /= matrix_90.sum()
    else:
        matrix_90 = matrix

    # Probabilitats: victòria local (triu), empat (diag), victòria visitant (tril)
    p_home = float(np.tril(matrix_90, k=-1).sum())   # home > away (fila > col)
    p_draw = float(np.trace(matrix_90))               # home == away (diagonal)
    p_away = float(np.triu(matrix_90, k=1).sum())     # away > home

    # Top N marcadors exactes (usant la matriu ORIGINAL amb empats)
    flat_probs = matrix.flatten()
    top_indices = np.argsort(flat_probs)[::-1][:top_n]
    top_scores = []
    for idx in top_indices:
        h_goals = idx // max_goals
        a_goals = idx % max_goals
        prob = flat_probs[idx]
        top_scores.append((h_goals, a_goals, prob))

    return lambda_home, lambda_away, p_home, p_draw, p_away, top_scores


def print_match_prediction(match_cfg: dict, artifact: dict, rho: float,
                           max_goals: int, top_n: int):
    """Imprimeix el resultat formatat per a un partit."""
    home = match_cfg["home"]
    away = match_cfg["away"]
    label = match_cfg["label"]
    stage_weight = match_cfg["stage_weight"]
    is_knockout = match_cfg["is_knockout"]

    pipeline = artifact["pipeline"]

    lambda_h, lambda_a, p_home, p_draw, p_away, top_scores = predict_match(
        home, away, pipeline,
        stage_weight=stage_weight,
        is_knockout=is_knockout,
        rho=rho,
        max_goals=max_goals,
        top_n=top_n,
    )

    # ─── Capçalera ───────────────────────────────────────────────────────────
    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  {label}")
    print(f"  {home['name']} (FIFA #{home['fifa_rank']})  vs  "
          f"{away['name']} (FIFA #{away['fifa_rank']})")
    print(sep)

    # ─── Gols esperats ───────────────────────────────────────────────────────
    print(f"\n  Gols esperats (λ):")
    print(f"    {home['name']:>20s}  →  {lambda_h:.3f}")
    print(f"    {away['name']:>20s}  →  {lambda_a:.3f}")

    # ─── Probabilitats win/draw/loss ─────────────────────────────────────────
    print(f"\n  Probabilitats de resultat:")
    bar_width = 30
    for label_str, prob, flag in [
        (f"  Victoria {home['name']}", p_home, "[W]"),
        (f"  Empat              ", p_draw, "[D]"),
        (f"  Victoria {away['name']}", p_away, "[W]"),
    ]:
        filled = int(round(prob * bar_width))
        bar = "█" * filled + "░" * (bar_width - filled)
        print(f"    {label_str:>24s}: {prob*100:5.1f}%  [{bar}] {flag}")

    # ─── Top N marcadors ─────────────────────────────────────────────────────
    knockout_note = " (sense empat en 90')" if is_knockout else ""
    print(f"\n  Top {top_n} marcadors exactes més probables{knockout_note}:")
    for rank_i, (h, a, prob) in enumerate(top_scores, 1):
        emoji = "***" if rank_i == 1 else "   "
        print(f"    {rank_i}. {home['name'][:3].upper()} {h}-{a} "
              f"{away['name'][:3].upper()}  →  {prob*100:5.2f}%  {emoji}")

    # ─── Ranks dinàmics de context ───────────────────────────────────────────
    print(f"\n  Context de forma (ranks dinàmics usats):")
    for t in [home, away]:
        base = t['fifa_rank']
        cur  = t['current_rank']
        off  = t['current_off_rank']
        deff = t['current_def_rank']
        delta = cur - base
        arrow = "(+)" if delta < 0 else ("(-) " if delta > 0 else "(=) ")
        print(f"    {t['name']:>12s}: General={cur:.1f} {arrow}{abs(delta):.1f}"
              f"  Atac={off:.1f}  Defensa={deff:.1f}")

    # Fi del bloc
    print(f"\n{sep}\n")


def main():
    print("\n" + "=" * 62)
    print("  PREDICTOR DIRECTE DE PARTITS - FIFA WORLD CUP 2026")
    print("  Model: Regressio Poisson + Dixon-Coles (bivariant)")
    print("=" * 62)

    # Carregar model (una sola vegada)
    print("\n  Carregant model entrenat (expanded_model.pkl)...")
    artifact = load_model()
    pp = artifact["preprocess_params"]
    print(f"  Model carregat OK  |  Poisson deviance CV: {artifact['best_score']:.6f}")
    print(f"  Paràmetres de preprocessing: shape={pp['shape']:.3f}, "
          f"k_mul={pp['k_mul']:.3f}, goal_cap={pp['goal_cap']:.3f}")

    # Predicció per a cada partit
    for match_cfg in MATCHES:
        print_match_prediction(
            match_cfg=match_cfg,
            artifact=artifact,
            rho=RHO,
            max_goals=MAX_GOALS,
            top_n=TOP_N_SCORES,
        )

    print("  [Nota] Els ranks d'aquests equips han estat obtinguts i")
    print("  calculats de forma automàtica a data/live_ranks.json")
    print("  reflectint la forma real i el seu rendiment a la fase de grups.\n")


if __name__ == "__main__":
    main()
