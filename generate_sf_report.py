# -*- coding: utf-8 -*-
import json
import pickle
import sys
from pathlib import Path
import numpy as np
from scipy.stats import poisson
from fpdf import FPDF
from fpdf.enums import XPos, YPos

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "model"))



STRONG_CONFEDS = {"UEFA", "CONMEBOL"}

def load_live_ranks():
    live_ranks_path = PROJECT_ROOT / "data" / "live_ranks.json"
    if live_ranks_path.exists():
        with open(live_ranks_path, encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_live_team(ranks, name):
    if name in ranks:
        return ranks[name]
    return {
        "name": name,
        "confederation": "UNKNOWN",
        "fifa_rank": 50.0,
        "host": False,
        "current_rank": 50.0,
        "current_off_rank": 50.0,
        "current_def_rank": 50.0,
    }

SF_MATCHUPS = [
    # Semifinals - Mundial 2026 (14-15 juliol 2026)
    ("Argentina", "England"),
    ("Spain", "France"),
]


def load_model():
    model_path = PROJECT_ROOT / "model" / "expanded_model.pkl"
    with open(model_path, "rb") as f:
        artifact = pickle.load(f)
    return artifact

def build_feature_row(team: dict, opponent: dict, stage_weight: int) -> np.ndarray:
    rank           = float(team.get("fifa_rank", 50))
    opp_rank       = float(opponent.get("fifa_rank", 50))
    cur_rank       = float(team.get("current_rank", 50))
    opp_cur_rank   = float(opponent.get("current_rank", 50))
    rank_shift     = cur_rank - rank
    opp_rank_shift = opp_cur_rank - opp_rank
    off_rank       = float(team.get("current_off_rank", 50))
    opp_off_rank   = float(opponent.get("current_off_rank", 50))
    def_rank       = float(team.get("current_def_rank", 50))
    opp_def_rank   = float(opponent.get("current_def_rank", 50))
    host           = 1.0 if team.get("host") else 0.0
    opp_host       = 1.0 if opponent.get("host") else 0.0
    is_strong      = 1.0 if team.get("confederation") in STRONG_CONFEDS else 0.0
    opp_is_strong  = 1.0 if opponent.get("confederation") in STRONG_CONFEDS else 0.0

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

def build_prob_matrix(lambda_home: float, lambda_away: float, rho: float = -0.1, max_goals: int = 7) -> np.ndarray:
    goals = np.arange(max_goals)
    home_pmf = poisson.pmf(goals, lambda_home)
    away_pmf = poisson.pmf(goals, lambda_away)
    matrix = np.outer(home_pmf, away_pmf)
    matrix[0, 0] *= max(0.0001, 1 - lambda_home * lambda_away * rho)
    matrix[0, 1] *= max(0.0001, 1 + lambda_home * rho)
    matrix[1, 0] *= max(0.0001, 1 + lambda_away * rho)
    matrix[1, 1] *= max(0.0001, 1 - rho)
    matrix /= matrix.sum()
    return matrix

def predict_match(home: dict, away: dict, pipeline, stage_weight: int = 1, rho: float = -0.1, max_goals: int = 7, top_n: int = 5):
    feat_home = build_feature_row(home, away, stage_weight)
    feat_away = build_feature_row(away, home, stage_weight)
    lambda_home = float(pipeline.predict(feat_home)[0])
    lambda_away = float(pipeline.predict(feat_away)[0])
    matrix = build_prob_matrix(lambda_home, lambda_away, rho, max_goals)
    
    p_home = float(np.tril(matrix, k=-1).sum())
    p_draw = float(np.trace(matrix))
    p_away = float(np.triu(matrix, k=1).sum())

    flat_probs = matrix.flatten()
    top_indices = np.argsort(flat_probs)[::-1][:top_n]
    top_scores = []
    for idx in top_indices:
        h_goals = idx // max_goals
        a_goals = idx % max_goals
        prob = flat_probs[idx]
        top_scores.append((h_goals, a_goals, prob))
        
    p_btts_yes = float(np.sum(matrix[1:, 1:]))
    i, j = np.indices(matrix.shape)
    p_over_15 = float(np.sum(matrix[(i + j) > 1]))
    p_over_25 = float(np.sum(matrix[(i + j) > 2]))
    p_teamA_over_15 = float(np.sum(matrix[2:, :]))
    p_teamB_over_15 = float(np.sum(matrix[:, 2:]))
    
    p_cs_teamA = float(np.sum(matrix[:, 0]))
    p_cs_teamB = float(np.sum(matrix[0, :]))
    
    derived = {
        "btts": p_btts_yes,
        "over_15": p_over_15,
        "over_25": p_over_25,
        "teamA_over_15": p_teamA_over_15,
        "teamB_over_15": p_teamB_over_15,
        "cs_teamA": p_cs_teamA,
        "cs_teamB": p_cs_teamB,
    }
        
    return lambda_home, lambda_away, p_home, p_draw, p_away, top_scores, derived

class PremiumPDF(FPDF):
    def header(self):
        self.set_fill_color(30, 41, 59)
        self.rect(0, 0, 210, 25, style='F')
        self.set_y(8)
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        # Using a utf-8 string directly (fpdf2 supports this natively for core fonts with standard cp1252 mapped chars if available)
        self.cell(0, 10, 'WC 2026: PREDICCIONS AVANÇADES I MERCATS', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(10)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pàgina {self.page_no()}', align='C')

def main():
    print("Generant Premium PDF de Semifinals en català...")
    live_ranks = load_live_ranks()
    artifact = load_model()
    pipeline = artifact["pipeline"]
    

    pdf = PremiumPDF()
    pdf.add_page()
    
    pdf.set_y(30)
    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(71, 85, 105)
    pdf.set_fill_color(241, 245, 249)
    note = ("Nota Tecnica: Aquest model avalua el rendiment col·lectiu i la forca de bloc. "
            "No es possible predir golejadors individuals, ja que el sistema no rastreja "
            "l'estadistica individual dels jugadors, sino l'eficiencia agregada de l'equip.")
    # Fix for fpdf2 standard fonts avoiding some utf-8 chars error if not using a unicode font: 
    # fpdf2 helvetica natively handles latin-1 including a, e, i, o, u, l·l, c
    pdf.multi_cell(0, 5, note, fill=True, border=1)
    pdf.ln(8)
    
    for match_idx, (t1_name, t2_name) in enumerate(SF_MATCHUPS, 1):
        team1 = get_live_team(live_ranks, t1_name)
        team2 = get_live_team(live_ranks, t2_name)
        
        # Predict Goals
        l_h, l_a, p_h, p_d, p_a, top_scores, derived = predict_match(team1, team2, pipeline, stage_weight=1)
        adv_h = p_h + p_d * 0.5
        adv_a = p_a + p_d * 0.5
        
        # Predict Events amb XGBoost
        from engine.match import _load_xgb_corners, _load_xgb_cards
        import pandas as pd
        xgb_corners = _load_xgb_corners()
        xgb_cards = _load_xgb_cards()
        
        h_mp = max(1, team1.get("matches_played", 1))
        a_mp = max(1, team2.get("matches_played", 1))
        
        h_avg_c_for = team1.get("corners_for", 0) / h_mp
        h_avg_c_ag = team1.get("corners_against", 0) / h_mp
        a_avg_c_for = team2.get("corners_for", 0) / a_mp
        a_avg_c_ag = team2.get("corners_against", 0) / a_mp
        
        h_avg_card_for = team1.get("cards_for", 0) / h_mp
        a_avg_card_for = team2.get("cards_for", 0) / a_mp
        
        rank_diff = team2.get("fifa_rank", 50) - team1.get("fifa_rank", 50)
        
        if xgb_corners is not None and xgb_cards is not None:
            X_corners_home = pd.DataFrame([[team1.get("fifa_rank", 50), team2.get("fifa_rank", 50), rank_diff, h_avg_c_for, a_avg_c_ag]], columns=['team_rank', 'opp_rank', 'rank_diff', 'avg_corners_for', 'opp_avg_corners_against'])
            X_corners_away = pd.DataFrame([[team2.get("fifa_rank", 50), team1.get("fifa_rank", 50), -rank_diff, a_avg_c_for, h_avg_c_ag]], columns=['team_rank', 'opp_rank', 'rank_diff', 'avg_corners_for', 'opp_avg_corners_against'])
            c_h = max(0.1, xgb_corners.predict(X_corners_home)[0])
            c_a = max(0.1, xgb_corners.predict(X_corners_away)[0])
            
            X_cards_home = pd.DataFrame([[team1.get("fifa_rank", 50), team2.get("fifa_rank", 50), rank_diff, h_avg_card_for]], columns=['team_rank', 'opp_rank', 'rank_diff', 'avg_cards_for'])
            X_cards_away = pd.DataFrame([[team2.get("fifa_rank", 50), team1.get("fifa_rank", 50), -rank_diff, a_avg_card_for]], columns=['team_rank', 'opp_rank', 'rank_diff', 'avg_cards_for'])
            crd_h = max(0.1, xgb_cards.predict(X_cards_home)[0])
            crd_a = max(0.1, xgb_cards.predict(X_cards_away)[0])
        else:
            c_h, crd_h = 5.0, 2.0
            c_a, crd_a = 5.0, 2.0
            
        total_corners_lam = float(c_h + c_a)
        total_cards_lam = float(crd_h + crd_a)
        
        def get_prob_over(lam, over_val):
            return 1.0 - sum(poisson.pmf(k, lam) for k in range(int(over_val) + 1))
            
        p_cor_over_85 = get_prob_over(total_corners_lam, 8)
        p_cor_over_95 = get_prob_over(total_corners_lam, 9)
        p_crd_over_15 = get_prob_over(total_cards_lam, 1)
        p_crd_over_25 = get_prob_over(total_cards_lam, 2)
        
        # Match Header
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(15, 23, 42)
        pdf.set_fill_color(200, 230, 255)  # Blau més viu per quarts de final
        pdf.cell(0, 8, f"SEMIFINAL {match_idx}: {t1_name} vs {t2_name}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        
        # Basic Stats & Advancement
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.cell(0, 6, f"Elo: {t1_name} ({team1['current_rank']:.1f})  |  {t2_name} ({team2['current_rank']:.1f})", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        
        # Probabilities block
        pdf.set_fill_color(248, 250, 252)
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(65, 6, f"Passa de ronda: {adv_h*100:.1f}%", border=1, fill=True, align="C")
        pdf.cell(60, 6, f"Gols Esperats: {l_h:.2f} - {l_a:.2f}", border=1, fill=True, align="C")
        pdf.cell(65, 6, f"Passa de ronda: {adv_a*100:.1f}%", border=1, fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font("helvetica", "", 10)
        pdf.cell(65, 6, f"Victòria (90'): {p_h*100:.1f}%", border=1)
        pdf.cell(60, 6, f"Empat (90'): {p_d*100:.1f}%", border=1, align="C")
        pdf.cell(65, 6, f"Victòria (90'): {p_a*100:.1f}%", border=1, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        
        # Exact Scores
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(2, 132, 199)
        pdf.cell(0, 6, "Top 5 Marcadors Exactes:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(15, 23, 42)
        scores_txt = "   ".join([f"{h}-{a} ({prob*100:.1f}%)" for h, a, prob in top_scores])
        pdf.cell(0, 6, scores_txt, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        
        # Advanced Goal Markets
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(16, 185, 129)
        pdf.cell(0, 6, "Mercats de Gols:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(65, 5, f"Ambdós equips marquen: {derived['btts']*100:.1f}%")
        pdf.cell(60, 5, f"Més d'1.5 gols totals: {derived['over_15']*100:.1f}%", align="C")
        pdf.cell(65, 5, f"Més de 2.5 gols totals: {derived['over_25']*100:.1f}%", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.cell(65, 5, f"{t1_name} més d'1.5 gols: {derived['teamA_over_15']*100:.1f}%")
        pdf.cell(60, 5, "")
        pdf.cell(65, 5, f"{t2_name} més d'1.5 gols: {derived['teamB_over_15']*100:.1f}%", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.cell(65, 5, f"Porteria a zero {t1_name}: {derived['cs_teamA']*100:.1f}%")
        pdf.cell(60, 5, "")
        pdf.cell(65, 5, f"Porteria a zero {t2_name}: {derived['cs_teamB']*100:.1f}%", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        
        # Event Markets
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(245, 158, 11)
        pdf.cell(0, 6, "Mercats de Córners i Targetes:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(15, 23, 42)
        
        pdf.cell(95, 5, f"Més de 8.5 Córners: {p_cor_over_85*100:.1f}%")
        pdf.cell(95, 5, f"Més de 9.5 Córners: {p_cor_over_95*100:.1f}%", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.cell(95, 5, f"Més de 1.5 Targetes: {p_crd_over_15*100:.1f}%")
        pdf.cell(95, 5, f"Més de 2.5 Targetes: {p_crd_over_25*100:.1f}%", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)
        
        # Narrative Synthesis
        top_h, top_a, top_prob = top_scores[0]
        if top_h > top_a:
            result_str = f"una victòria de {t1_name} per {top_h}-{top_a}"
        elif top_h < top_a:
            result_str = f"una victòria de {t2_name} per {top_h}-{top_a}"
        else:
            result_str = f"un empat {top_h}-{top_a}"
            
        expected_corners = round(total_corners_lam)
        expected_cards = round(total_cards_lam)
        
        narrative = (f"Segons el model, l'escenari més probable als 90 minuts és {result_str}. "
                     f"A nivell d'esdeveniments, s'espera un partit amb aproximadament {expected_corners} "
                     f"córners totals i unes {expected_cards} targetes mostrades.")
        
        pdf.set_font("helvetica", "BI", 9)
        pdf.set_text_color(67, 56, 202) # Indigo-ish
        pdf.cell(0, 6, "Conclusió de l'Analista:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 5, narrative)
        
        pdf.ln(8)
        
        if pdf.get_y() > 240:
            pdf.add_page()
            
    # Add Monte Carlo Win Probabilities
    pdf.add_page()
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "PROBABILITAT DE GUANYAR EL MUNDIAL (MONTE CARLO)", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    print("Calculant probabilitats de guanyar el mundial des de Semifinals...")
    try:
        from collections import Counter
        import random
        
        print("Precalculant probabilitats de tots els possibles enfrontaments...")
        all_teams = list(live_ranks.keys())
        prob_cache = {}
        for t1 in all_teams:
            prob_cache[t1] = {}
            team1 = get_live_team(live_ranks, t1)
            for t2 in all_teams:
                if t1 == t2: continue
                team2 = get_live_team(live_ranks, t2)
                _, _, p_h, p_d, _, _, _ = predict_match(team1, team2, pipeline, stage_weight=1)
                prob_cache[t1][t2] = p_h + p_d * 0.5
                
        def simulate_bracket(matchups):
            current_round = list(matchups)
            while len(current_round) > 1:
                next_round = []
                for t1_name, t2_name in current_round:
                    adv_h = prob_cache.get(t1_name, {}).get(t2_name, 0.5)
                    
                    if random.random() < adv_h:
                        next_round.append(t1_name)
                    else:
                        next_round.append(t2_name)
                        
                # Prepare next round pairings
                current_round = []
                for i in range(0, len(next_round), 2):
                    if i + 1 < len(next_round):
                        current_round.append((next_round[i], next_round[i+1]))
                    else:
                        current_round.append((next_round[i], None))
            
            # Final
            if current_round:
                t1_name, t2_name = current_round[0]
                adv_h = prob_cache.get(t1_name, {}).get(t2_name, 0.5)
                return t1_name if random.random() < adv_h else t2_name
            return None
            
        winners = []
        # Utilitzem SF_MATCHUPS definit a l'inici del fitxer com a punt de partida
        for i in range(100000): # 100.000 iteracions d'alta precisio per la nit
            champion = simulate_bracket(SF_MATCHUPS)
            if champion:
                winners.append(champion)
                
        counts = Counter(winners)
        sorted_probs = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        
        pdf.set_font("helvetica", "", 11)
        pdf.set_text_color(51, 65, 85)
        for team, count in sorted_probs:
            prob = count / 100000.0
            pdf.cell(100, 6, team, border=1)
            pdf.cell(50, 6, f"{prob*100:.1f}%", border=1, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    except Exception as e:
        print(f"Error en Monte Carlo: {e}")
        pdf.cell(0, 10, f"Error calculant probabilitats: {str(e)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
    output_path = PROJECT_ROOT / "Prediccions_Semifinals_CAT_WC2026.pdf"
    pdf.output(str(output_path))
    print(f"PDF generat correctament a: {output_path}")

if __name__ == "__main__":
    main()
