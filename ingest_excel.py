# ingest_excel.py
import os
import sys
from typing import List, Dict
import pandas as pd

from app.ingest_to_postgres import ingest_passages_to_db

# Path to your Excel (adjust if needed)
EXCEL_PATH = os.path.join("data", "Dialogflow_Chatbot_Training_Template_with_Video_Subservices.xlsx")

# common names to check for follow-up fields (case-insensitive)
FOLLOWUP_COL_CANDIDATES = {
    "followup", "follow_ups", "follow_ups", "follow-up", "followups",
    "clarifyingquestion", "clarifying_question", "clarifying question",
    "follow_up", "FollowUp", "Follow_Up", "Follow Ups", "Followups",
    "next question", "next_question", "clarify", "clarification"
}

def find_followup_column(columns):
    # Return the first matching column name from the DataFrame columns (case-insensitive)
    cols_lower = {c.lower(): c for c in columns}
    for candidate in FOLLOWUP_COL_CANDIDATES:
        if candidate.lower() in cols_lower:
            return cols_lower[candidate.lower()]
    return None

def split_followups_cell(cell_value: str):
    """
    Normalize a cell's follow-up content into a list of strings.
    Supports newline-separated, semicolon-separated, or '||' separators.
    """
    if not cell_value:
        return []
    # ensure string
    s = str(cell_value).strip()
    # common separators
    parts = []
    # try double-pipe first (used sometimes)
    if "||" in s:
        parts = [p.strip() for p in s.split("||") if p.strip()]
    elif "\n" in s:
        parts = [p.strip() for p in s.splitlines() if p.strip()]
    elif ";" in s:
        parts = [p.strip() for p in s.split(";") if p.strip()]
    else:
        parts = [s]
    return parts

def extract_passages_from_excel(path: str) -> List[Dict]:
    if not os.path.exists(path):
        print(f"Excel file not found at {path}")
        sys.exit(1)

    xls = pd.ExcelFile(path)
    all_passages = []
    doc_name = os.path.basename(path)

    for sheet in xls.sheet_names:
        df = xls.parse(sheet_name=sheet, dtype=str).fillna("")
        followup_col = find_followup_column(df.columns)
        for idx, row in df.iterrows():
            # Build text from columns: you can customize which column(s) to use.
            # If your sheet has a particular 'Description' or 'Response' column, prefer that.
            # Otherwise join all non-empty columns into a single passage.
            pairs = []
            for col in df.columns:
                v = str(row[col]).strip()
                if v and (followup_col is None or col != followup_col):
                    pairs.append(f"{col}: {v}")
            if not pairs:
                continue
            text = "  |  ".join(pairs)

            followups = []
            if followup_col:
                raw = str(row[followup_col]).strip()
                followups = split_followups_cell(raw)

            all_passages.append({
                "doc": doc_name,
                "sheet": sheet,
                "row": int(idx),
                "col": ", ".join([c for c in df.columns if str(row[c]).strip()]),
                "text": text,
                "followups": followups
            })
    return all_passages

def main():
    passages = extract_passages_from_excel(EXCEL_PATH)
    print(f"[ingest_excel] extracted {len(passages)} passages")
    ingest_passages_to_db(passages, chunk_size=500, chunk_overlap=50)

if __name__ == "__main__":
    main()
