import pandas as pd

ne = pd.read_csv("data/newspapers_non_english.csv")
ne["start"] = ne.title.str.extract(r":\s*(\d{4})")[0].astype(int)
ne = ne[ne.start <= 1954]
ne = ne[~ne.language.isin(["en", "la"]) & (ne.proportion >= 0.2)]
ne["language_full"] = ne.language_full.str.replace(r" \(1453-\)", "", regex=True)
lang = (ne.groupby("language_full")
          .agg(titles=("id", "nunique"), first_year=("start", "min"))
          .reset_index().sort_values(["titles", "first_year"], ascending=[False, True]))
lang.to_csv("data/non_english_languages.csv", index=False)
print(lang)