import shutil, glob, os

src = r"C:\Fortia\Personal\tmp_worldcup\data-csv"
dst = r"C:\Fortia\Personal\provamundial\data\db"

os.makedirs(dst, exist_ok=True)
csvs = glob.glob(os.path.join(src, "*.csv"))
for f in csvs:
    shutil.copy(f, dst)

copied = glob.glob(os.path.join(dst, "*.csv"))
print(f"Fitxers copiats: {len(copied)}")
for f in sorted(copied):
    print(f"  - {os.path.basename(f)}")
