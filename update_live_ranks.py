# -*- coding: utf-8 -*-
"""
update_live_ranks.py
====================
Ingereix els resultats reals de la fase de grups del Mundial 2026
(de data/wc2026_real_results.json, font: openfootball.github.io)
i recalcula els rankigns dinamics de cada equip aplicant la logica
Elo de model/preprocessing.py: rank general, ofensiu i defensiu.

Guarda el resultat a data/live_ranks.json per ser llegit per predict_direct.py.

Us:
    .env\\Scripts\\python update_live_ranks.py
"""

import io
import json
import sys
from pathlib import Path

# Sortida UTF-8 per a Windows
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "model"))

from model.preprocessing import (
    calculate_rank_shift,
    calculate_off_rank_shift,
    calculate_def_rank_shift,
    STRONG_CONFEDS,
)

# =============================================================================
# MAPATGE DE NOMS: openfootball -> wc_2026_teams.json
# Afegeix aqui si trobes discrepancies addicionals
# =============================================================================
NAME_MAP = {
    "Bosnia & Herzegovina":     "Bosnia and Herzegovina",
    "Bosnia y Herzegovina":     "Bosnia and Herzegovina",
    "Bosnia-Herzegovina":       "Bosnia and Herzegovina",
    "Cura\u00e7ao":             "Cura\u00e7ao",
    "Curacao":                  "Cura\u00e7ao",
    "Curazao":                  "Cura\u00e7ao",
    "USA":                      "USA",
    "United States":            "USA",
    "Estados Unidos":           "USA",
    "EE. UU.":                  "USA",
    "Ivory Coast":              "Ivory Coast",
    "Cote d'Ivoire":            "Ivory Coast",
    "Costa de Marfil":          "Ivory Coast",
    "DR Congo":                 "DR Congo",
    "RD Congo":                 "DR Congo",
    "Iran":                     "Iran",
    "Ir\u00e1n":                 "Iran",
    "Irán":                     "Iran",
    "Cape Verde":               "Cape Verde",
    "Cabo Verde":               "Cape Verde",
    "Saudi Arabia":             "Saudi Arabia",
    "Arabia Saudí":             "Saudi Arabia",
    "Arabia Saudi":             "Saudi Arabia",
    "South Korea":              "South Korea",
    "Corea del Sur":            "South Korea",
    "Bosnia and Herzegovina":   "Bosnia and Herzegovina",
    "Inglaterra":               "England",
    "Brasil":                   "Brazil",
    "España":                   "Spain",
    "Espana":                   "Spain",
    "Francia":                  "France",
    "Alemania":                  "Germany",
    "Paises Bajos":             "Netherlands",
    "Países Bajos":             "Netherlands",
    "Croacia":                   "Croatia",
    "Marruecos":                 "Morocco",
    "Egipto":                    "Egypt",
    "Japon":                     "Japan",
    "Japón":                     "Japan",
    "Camerun":                   "Cameroon",
    "Camerún":                   "Cameroon",
    "Suiza":                     "Switzerland",
    "Republica Checa":           "Czech Republic",
    "República Checa":           "Czech Republic",
    "Sudafrica":                 "South Africa",
    "Sudáfrica":                 "South Africa",
    "Argelia":                   "Algeria",
    "Tunez":                     "Tunisia",
    "Túnez":                     "Tunisia",
    "Turquia":                   "Turkey",
    "Turquía":                   "Turkey",
    "Bélgica":                   "Belgium",
    "Belgica":                   "Belgium",
    "Suecia":                    "Sweden",
    "Noruega":                   "Norway",
    "Dinamarca":                 "Denmark",
    "Mali":                      "Mali",
    "Malí":                      "Mali",
    "Gales":                     "Wales",
    "Escocia":                   "Scotland",
    "Nueva Zelanda":             "New Zealand",
    "Irak":                      "Iraq",
    "Canadá":                    "Canada",
    "Haití":                     "Haiti",
    "Jordania":                  "Jordan",
    "México":                    "Mexico",
    "Panamá":                    "Panama",
    "Catar":                     "Qatar",
    "Uzbekistán":                "Uzbekistan"
}

def normalize_name(name: str) -> str:
    """Normalitza el nom d'un equip al format de wc_2026_teams.json."""
    return NAME_MAP.get(name, name)


def load_teams(teams_path: Path) -> dict:
    """
    Llegeix wc_2026_teams.json i retorna un dict:
        { nom_equip: { ...dades base + ranks dynamics inicialitzats... } }
    """
    with open(teams_path, encoding='utf-8') as f:
        raw = json.load(f)

    teams = {}
    for group_name, group_teams in raw["groups"].items():
        for t in group_teams:
            name = t["name"]
            r = float(t["fifa_rank"])
            teams[name] = {
                "name":             name,
                "confederation":    t["confederation"],
                "fifa_rank":        r,
                "host":             t["host"],
                "group":            group_name,
                # Ranks dynamics (inicialitzats al rank FIFA base)
                "current_rank":     r,
                "current_off_rank": r,
                "current_def_rank": r,
                # Per auditoria
                "matches_played":   0,
                "goals_for":        0,
                "goals_against":    0,
                "corners_for":      0,
                "corners_against":  0,
                "cards_for":        0,
                "cards_against":    0,
                "wins":             0,
                "draws":            0,
                "losses":           0,
            }
    return teams


def load_xg_data(xg_path: Path) -> dict:
    if not xg_path.exists():
        return {}
    with open(xg_path, encoding='utf-8') as f:
        raw = json.load(f)
    xg_map = {}
    for m in raw.get("matches", []):
        t1 = normalize_name(m["team1"])
        t2 = normalize_name(m["team2"])
        
        xg1, xg2 = m.get("xg1"), m.get("xg2")
        # Fallback a Elo clàssic si l'xG és NA, None o 0
        if xg1 is None or str(xg1).lower() == "nan" or float(xg1) == 0.0:
            xg1 = None
        if xg2 is None or str(xg2).lower() == "nan" or float(xg2) == 0.0:
            xg2 = None
            
        c1, c2 = m.get("corners1", 0), m.get("corners2", 0)
        card1, card2 = m.get("cards1", 0), m.get("cards2", 0)
        
        # Normalize date from DD.MM.YYYY to YYYY-MM-DD
        raw_date = m.get("date", "")
        if "." in raw_date:
            parts = raw_date.split(".")
            if len(parts) == 3:
                date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                date_str = raw_date
        else:
            date_str = raw_date
            
        xg_map[(date_str, t1, t2)] = (xg1, xg2, c1, c2, card1, card2)
        xg_map[(date_str, t2, t1)] = (xg2, xg1, c2, c1, card2, card1)
    return xg_map


def load_results(results_path: Path, xg_map: dict = None) -> list:
    """
    Llegeix el JSON d'openfootball i retorna una llista de partits
    de la fase de grups amb score disponible, ordenats cronologicament.
    """
    with open(results_path, encoding='utf-8') as f:
        raw = json.load(f)

    matches = []
    for m in raw["matches"]:
        # Filtrem: nomes grups (no eliminatories) i amb resultat
        if not m.get("group") or "score" not in m:
            continue
        score = m["score"].get("ft")
        if score is None or len(score) != 2:
            continue

        t1_norm = normalize_name(m["team1"])
        t2_norm = normalize_name(m["team2"])
        xg1, xg2 = None, None
        if xg_map:
            # Cercar coincidencia fuzzy de data (fins a 2 dies de diferencia)
            from datetime import datetime, timedelta
            m_date = datetime.strptime(m["date"], "%Y-%m-%d")
            best_match = None
            best_diff = timedelta(days=999)
            
            for (s_date_str, st1, st2), val in xg_map.items():
                if st1 == t1_norm and st2 == t2_norm:
                    try:
                        s_date = datetime.strptime(s_date_str, "%Y-%m-%d")
                        diff = abs(s_date - m_date)
                        if diff < best_diff:
                            best_diff = diff
                            best_match = val
                    except:
                        pass
            
            if best_match and best_diff <= timedelta(days=2):
                xg1, xg2 = best_match[0], best_match[1]

        matches.append({
            "date":   m["date"],
            "group":  m["group"],
            "team1":  t1_norm,
            "team2":  t2_norm,
            "g1":     int(score[0]),
            "g2":     int(score[1]),
            "xg1":    xg1,
            "xg2":    xg2,
        })

    # Ordre cronologic (les dates son ISO, l'ordre lexicografic funciona)
    matches.sort(key=lambda x: x["date"])
    return matches


def apply_match_to_ranks(teams: dict, match: dict, pp: dict) -> tuple:
    """
    Aplica un resultat real als rankigns dynamics de dos equips.

    Usa exactament les mateixes funcions que ModeledMatch._update_ranks
    de engine/match.py, amb els parametres del model entrenat.

    Retorna (nom_equip1, nom_equip2) per a log.
    """
    n1, n2 = match["team1"], match["team2"]
    g1, g2 = match["g1"], match["g2"]
    xg1, xg2 = match.get("xg1"), match.get("xg2")
    c1, c2 = match.get("corners1", 0), match.get("corners2", 0)
    card1, card2 = match.get("cards1", 0), match.get("cards2", 0)

    t1 = teams.get(n1)
    t2 = teams.get(n2)

    if t1 is None or t2 is None:
        missing = [n for n, t in [(n1, t1), (n2, t2)] if t is None]
        return None, missing  # equip no trobat

    # Snapshots de ranks al moment del xut inicial (com fa el codi real)
    r1_snap = t1["current_rank"]
    r2_snap = t2["current_rank"]

    # Resultat des de la perspectiva de cada equip
    if g1 > g2:
        res1, res2 = 1.0, 0.0
    elif g1 < g2:
        res1, res2 = 0.0, 1.0
    else:
        res1, res2 = 0.5, 0.5

    reversion_rate = pp.get("reversion_rate", 0.0)
    shape   = pp["shape"]
    
    is_friendly = (match.get("group") == "Amistós")
    weight_factor = 0.5 if is_friendly else 1.0
    
    k_mul   = pp["k_mul"] * weight_factor
    k_off   = pp["k_off_mul"] * weight_factor
    k_def   = pp["k_def_mul"] * weight_factor
    goal_cap = pp["goal_cap"]

    def apply_reversion(val, base_val):
        return (1.0 - reversion_rate) * val + reversion_rate * base_val

    def update_team(team, opp_cur_rank_snap, goals_scored, goals_conceded, result, team_xg=None, opp_xg=None, corners_scored=0, corners_conceded=0, cards_received=0, cards_opp=0):
        base = team["fifa_rank"]

        # General rank
        gen_shift = calculate_rank_shift(
            team["current_rank"], opp_cur_rank_snap,
            result, shape=shape, k_mul=k_mul, xg_a=team_xg, xg_b=opp_xg
        )
        new_gen = max(1.0, team["current_rank"] + gen_shift)
        team["current_rank"] = round(apply_reversion(new_gen, base), 1)

        # Offensive rank
        off_shift = calculate_off_rank_shift(
            team["current_off_rank"], opp_cur_rank_snap,
            goals_scored, shape=shape, k_off_mul=k_off, goal_cap=goal_cap
        )
        new_off = max(1.0, team["current_off_rank"] + off_shift)
        team["current_off_rank"] = round(apply_reversion(new_off, base), 1)

        # Defensive rank
        def_shift = calculate_def_rank_shift(
            team["current_def_rank"], opp_cur_rank_snap,
            goals_conceded, shape=shape, k_def_mul=k_def, goal_cap=goal_cap
        )
        new_def = max(1.0, team["current_def_rank"] + def_shift)
        team["current_def_rank"] = round(apply_reversion(new_def, base), 1)

        # Stats per auditoria i models secundaris
        team["goals_for"]       += goals_scored
        team["goals_against"]   += goals_conceded
        
        team["corners_for"]     += corners_scored
        team["corners_against"] += corners_conceded
        team["cards_for"]       += cards_received
        team["cards_against"]   += cards_opp
        
        if result == 1.0:
            team["wins"] += 1
        elif result == 0.0:
            team["losses"] += 1
        else:
            team["draws"] += 1

    update_team(t1, r2_snap, g1, g2, res1, xg1, xg2, c1, c2, card1, card2)
    update_team(t2, r1_snap, g2, g1, res2, xg2, xg1, c2, c1, card2, card1)

    return n1, n2


def main():
    print("=" * 65)
    print("  UPDATE LIVE RANKS - Mundial 2026 (Fase de Grups)")
    print("  Font: openfootball/worldcup.json (github.com)")
    print("=" * 65)

    # 1. Carregar base de dades d'equips
    teams_path   = PROJECT_ROOT / "data" / "wc_2026_teams.json"
    results_path = PROJECT_ROOT / "data" / "wc2026_real_results.json"
    output_path  = PROJECT_ROOT / "data" / "live_ranks.json"

    teams = load_teams(teams_path)
    print(f"\n  Equips carregats: {len(teams)}")

    xg_path = PROJECT_ROOT / "data" / "live_stats_2026.json"
    xg_map = load_xg_data(xg_path)
    if xg_map:
        print(f"  Dades xG carregades per a {len(xg_map)//2} partits.")
    else:
        print("  Sense dades d'xG addicionals.")

    # 2. Carregar parametres del model entrenat
    import pickle
    model_path = PROJECT_ROOT / "model" / "expanded_model.pkl"
    with open(model_path, "rb") as f:
        artifact = pickle.load(f)
    pp = artifact["preprocess_params"]
    print(f"  Parametres model: shape={pp['shape']:.3f}, "
          f"k_mul={pp['k_mul']:.3f}, k_off={pp['k_off_mul']:.3f}, "
          f"k_def={pp['k_def_mul']:.3f}, goal_cap={pp['goal_cap']:.3f}, "
          f"reversion={pp['reversion_rate']:.3f}")
          
    # 2.5 Carregar estadístiques pures de córners i targetes de Flashscore
    # Filtrem NOMES els partits de la fase de grups real del Mundial
    # (usem el conjunt de dates i equips de wc2026_real_results.json com a referència)
    if xg_path.exists():
        with open(xg_path, encoding='utf-8') as f:
            raw_xg = json.load(f)

        for m in raw_xg.get("matches", []):
            t1_raw = normalize_name(m["team1"])
            t2_raw = normalize_name(m["team2"])

            # Només processem si els dos equips existeixen (són del Mundial)
            if t1_raw not in teams or t2_raw not in teams:
                continue

            c1, c2 = m.get("corners1", 0), m.get("corners2", 0)
            card1, card2 = m.get("cards1", 0), m.get("cards2", 0)
            g1, g2 = m.get("g1", 0), m.get("g2", 0)

            # Només sumar estadístiques si hi ha hagut joc real
            if (c1 + c2 > 0) or (card1 + card2 > 0) or (g1 + g2 > 0):
                if t1_raw in teams:
                    teams[t1_raw]["corners_for"] += c1
                    teams[t1_raw]["corners_against"] += c2
                    teams[t1_raw]["cards_for"] += card1
                    teams[t1_raw]["cards_against"] += card2
                    teams[t1_raw]["matches_played"] += 1

                if t2_raw in teams:
                    teams[t2_raw]["corners_for"] += c2
                    teams[t2_raw]["corners_against"] += c1
                    teams[t2_raw]["cards_for"] += card2
                    teams[t2_raw]["cards_against"] += card1
                    teams[t2_raw]["matches_played"] += 1
        print("  Estadístiques de córners i targetes agregades (nomes partits WC reals).")

    # 3. Carregar resultats reals i afegir els nous partits de eliminatòries (Setzens, etc.)
    matches = load_results(results_path, xg_map)
    
    # Creem un set per saber quins partits ja estan carregats per la fase de grups
    loaded_match_keys = {(m["team1"], m["team2"]) for m in matches}
    loaded_match_keys.update({(m["team2"], m["team1"]) for m in matches})
    
    # Data de tall: les eliminatòries comencen el 28 de juny
    KNOCKOUT_START = "2026-06-28"
    
    def norm_date_str(raw):
        if "." in raw:
            p = raw.split(".")
            if len(p) == 3:
                return f"{p[2]}-{p[1]}-{p[0]}"
        return raw
    
    # Recollim tots els partits de knockout del JSON, ORDENATS per data (els més recents primer)
    # Així el partit real (juliol) guanya sobre l'amistós (juny).
    knockout_candidates = []
    for m in raw_xg.get("matches", []):
        t1_norm = normalize_name(m["team1"])
        t2_norm = normalize_name(m["team2"])
        if t1_norm not in teams or t2_norm not in teams:
            continue
        date_norm = norm_date_str(m.get("date", ""))
        
        if date_norm < "2026-06-11":
            if m.get("g1") is not None and m.get("g2") is not None:
                knockout_candidates.append({
                    "date": date_norm,
                    "group": "Amistós",
                    "team1": t1_norm,
                    "team2": t2_norm,
                    "g1": int(m["g1"]),
                    "g2": int(m["g2"]),
                    "xg1": m.get("xg1"),
                    "xg2": m.get("xg2"),
                })
            continue

        if date_norm < KNOCKOUT_START:
            continue  # Ignorar amistosos anteriors a les eliminatòries
        if m.get("g1") is None or m.get("g2") is None:
            continue
        knockout_candidates.append({
            "date": date_norm,
            "group": "Knockout",
            "team1": t1_norm,
            "team2": t2_norm,
            "g1": int(m["g1"]),
            "g2": int(m["g2"]),
            "xg1": m.get("xg1"),
            "xg2": m.get("xg2"),
        })
    
    # Ordenem per data DESCENDENT per assegurar que el partit real (el més recent) s'afegeix primer
    knockout_candidates.sort(key=lambda x: x["date"], reverse=True)
    
    added_knockout_keys = set()
    for km in knockout_candidates:
        t1, t2 = km["team1"], km["team2"]
        key = (t1, t2)
        rkey = (t2, t1)
        # Afegim el partit si la parella no ha aparegut ja en la fase de grups NI en un altre knockout
        if key not in loaded_match_keys and key not in added_knockout_keys:
            matches.append(km)
            added_knockout_keys.add(key)
            added_knockout_keys.add(rkey)
    
    matches.sort(key=lambda x: x["date"])
    print(f"\n  Partits totals (Fase grups + Eliminatòries) carregats: {len(matches)}")
    print(f"  (Fase de grups: {len(matches) - len(added_knockout_keys)//2}, Eliminatòries: {len(added_knockout_keys)//2})")


    # 4. Processar cada partit cronologicament
    print("\n" + "-" * 65)
    print(f"  {'Data':<12} {'Grup':<10} {'Resultat':<35} {'Estat'}")
    print("-" * 65)

    ok_count = 0
    skip_count = 0
    skipped = []
    
    xg_count = 0
    classic_count = 0

    for m in matches:
        if m.get("xg1") is not None and m.get("xg2") is not None:
            xg_count += 1
        else:
            classic_count += 1
            
        result_str = f"{m['team1']} {m['g1']}-{m['g2']} {m['team2']}"
        n1, n2 = apply_match_to_ranks(teams, m, pp)
        if n1 is None:
            status = f"SKIP (desconegut: {n2})"
            skip_count += 1
            skipped.append(result_str)
        else:
            status = "OK"
            ok_count += 1
        print(f"  {m['date']:<12} {m['group']:<10} {result_str:<35} {status}")

    print("-" * 65)
    print(f"\n  Partits ingerits: {ok_count}  |  Omesos: {skip_count}")
    
    print(f"\n=======================================================")
    print(f" RESUM D'ACTUALITZACIÓ DE RÀNQUINGS")
    print(f"=======================================================")
    print(f" Partits processats amb Dades xG  : {xg_count}")
    print(f" Partits processats amb Elo clàssic: {classic_count} (per falta de dades)")
    print(f"=======================================================\n")

    if skipped:
        print(f"  Partits omesos: {skipped}")

    # 5. Mostrar taula de ranks actualitzats (equips rellevants primer)
    highlight = {"Brazil", "Japan", "Germany", "Paraguay"}
    all_teams = sorted(teams.values(), key=lambda t: t["current_rank"])

    print("\n" + "=" * 75)
    print(f"  {'Equip':<22} {'Base':>6} {'General':>9} {'Atac':>9} "
          f"{'Defensa':>9} {'MP':>4} {'GF':>4} {'GA':>4} {'W-D-L'}")
    print("=" * 75)

    for t in all_teams:
        marker = " ***" if t["name"] in highlight else ""
        delta = t["current_rank"] - t["fifa_rank"]
        d_str = f"({delta:+.1f})" if delta != 0.0 else "      "
        print(f"  {t['name']:<22} {t['fifa_rank']:>6.0f}  "
              f"{t['current_rank']:>6.1f}{d_str:<8}  "
              f"{t['current_off_rank']:>6.1f}  {t['current_def_rank']:>6.1f}  "
              f"{t['matches_played']:>3}  {t['goals_for']:>3}  "
              f"{t['goals_against']:>3}  "
              f"{t['wins']}-{t['draws']}-{t['losses']}{marker}")

    # 6. Guardar live_ranks.json
    output = {}
    for name, t in teams.items():
        output[name] = {
            "name":             t["name"],
            "confederation":    t["confederation"],
            "fifa_rank":        t["fifa_rank"],
            "host":             t["host"],
            "current_rank":     t["current_rank"],
            "current_off_rank": t["current_off_rank"],
            "current_def_rank": t["current_def_rank"],
            "matches_played":   t["matches_played"],
            "goals_for":        t["goals_for"],
            "goals_against":    t["goals_against"],
            "corners_for":      t["corners_for"],
            "corners_against":  t["corners_against"],
            "cards_for":        t["cards_for"],
            "cards_against":    t["cards_against"],
            "wins":             t["wins"],
            "draws":            t["draws"],
            "losses":           t["losses"],
        }

    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n  Ranks guardats a: {output_path}")
    print("  Obre predict_direct.py per veure les prediccions actualitzades.\n")


if __name__ == "__main__":
    main()
