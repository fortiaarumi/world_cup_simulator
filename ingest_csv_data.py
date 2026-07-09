import pandas as pd
import json
from pathlib import Path

def ingest_csv():
    print("Iniciant la ingestió del fitxer Mundial_FIFA_2026.csv...")
    csv_path = "Mundial_FIFA_2026.csv"
    
    if not Path(csv_path).exists():
        print(f"Error: No s'ha trobat el fitxer {csv_path}")
        return
        
    df = pd.read_csv(csv_path)
    
    matches = []
    
    # Agrupem per 'Partit' que és un identificador únic del tipus "TeamA vs TeamB"
    for partit, group in df.groupby("Partit"):
        if len(group) != 2:
            print(f"Advertència: El partit '{partit}' no té exactament 2 files.")
            continue
            
        row1 = group.iloc[0]
        row2 = group.iloc[1]
        
        # Ignorem explícitament els NAs de les altres columnes
        # Neteja de la dada xG:
        xg1 = row1["xG"]
        xg2 = row2["xG"]
        
        if pd.isna(xg1): xg1 = None
        else: xg1 = float(xg1)
            
        if pd.isna(xg2): xg2 = None
        else: xg2 = float(xg2)
            
        team1_name, team2_name = partit.split(" vs ")
        
        # Mapejar els xG als equips correctes segons la fila
        if row1["Equip"] == team1_name:
            xg_team1, xg_team2 = xg1, xg2
        else:
            xg_team1, xg_team2 = xg2, xg1
            
        matches.append({
            "date": row1["Data"],
            "team1": team1_name,
            "team2": team2_name,
            "xg1": xg_team1,
            "xg2": xg_team2
        })
        
    # Guardem l'output al fitxer live_xg_2026.json
    output_path = Path("data/live_xg_2026.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"matches": matches}, f, indent=2, ensure_ascii=False)
        
    print(f"S'han processat i exportat {len(matches)} partits a {output_path}.")
    
if __name__ == "__main__":
    ingest_csv()
