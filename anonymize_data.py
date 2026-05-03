from pathlib import Path
import pandas as pd
import unicodedata

PRIVATE_DIR = Path("data_private")
PUBLIC_DIR = Path("data_public")

PUBLIC_DIR.mkdir(exist_ok=True)


def normalize_text(text):
    text = str(text).replace('"', "").strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def clean_columns(df):
    df = df.copy()
    df.columns = [str(col).replace('"', "").strip() for col in df.columns]
    return df


def read_csv_french(file_path):
    try:
        return pd.read_csv(file_path, sep=";", decimal=",", encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, sep=";", decimal=",", encoding="latin1")


def find_column(df, keywords):
    for col in df.columns:
        normalized_col = normalize_text(col)
        if all(keyword in normalized_col for keyword in keywords):
            return col
    return None


# Load all private CSV files
csv_files = list(PRIVATE_DIR.glob("*.csv"))

if not csv_files:
    raise FileNotFoundError("No CSV files found in data_private.")

all_dataframes = {}

for file in csv_files:
    df = read_csv_french(file)
    df = clean_columns(df)
    all_dataframes[file.name] = df


# Create consistent anonymization mappings across all files
all_agencies = set()
all_upws = set()

for df in all_dataframes.values():
    designation_col = find_column(df, ["designation"])
    upw_col = find_column(df, ["upw"])

    if designation_col:
        all_agencies.update(df[designation_col].dropna().astype(str).unique())

    if upw_col:
        all_upws.update(df[upw_col].dropna().astype(str).unique())


agency_mapping = {
    agency: f"Agency_{i + 1:03d}"
    for i, agency in enumerate(sorted(all_agencies))
}

upw_mapping = {
    upw: f"UPW_{i + 1:03d}"
    for i, upw in enumerate(sorted(all_upws))
}


# Save anonymized files
for file_name, df in all_dataframes.items():
    df_public = df.copy()

    designation_col = find_column(df_public, ["designation"])
    upw_col = find_column(df_public, ["upw"])

    if designation_col:
        df_public[designation_col] = (
            df_public[designation_col]
            .astype(str)
            .map(agency_mapping)
        )

    if upw_col:
        df_public[upw_col] = (
            df_public[upw_col]
            .astype(str)
            .map(upw_mapping)
        )

    output_path = PUBLIC_DIR / file_name
    df_public.to_csv(
        output_path,
        sep=";",
        decimal=",",
        index=False,
        encoding="utf-8-sig"
    )

print("Public anonymized files created successfully in data_public.")
print(f"Number of anonymized agencies: {len(agency_mapping)}")
print(f"Number of anonymized UPWs: {len(upw_mapping)}")