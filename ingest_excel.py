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
    "Follow-up Prompts",  # exact match from your Excel
    "followup", "follow_ups", "follow-ups", "follow-up", "followups",
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
        
        # Key columns from your template
        response_col = "Response (Short, Natural)"
        intent_col = "Intent Name"
        training_col = "Training Phrases (Examples)"
        followup_col = "Follow-up Prompts"
        category_col = "Service Category"
        
        for idx, row in df.iterrows():
            # Primary response text (most important)
            response_text = str(row.get(response_col, "")).strip()
            if not response_text:
                continue  # Skip if no response text
                
            # Build rich context
            context_parts = []
            
            # Add intent and category if available
            intent = str(row.get(intent_col, "")).strip()
            category = str(row.get(category_col, "")).strip()
            if intent:
                context_parts.append(f"Intent: {intent}")
            if category:
                context_parts.append(f"Category: {category}")
                
            # Add training phrases if available
            training = str(row.get(training_col, "")).strip()
            if training:
                phrases = split_followups_cell(training)  # reuse splitter for pipe-separated phrases
                if phrases:
                    context_parts.append(f"Example Questions: {', '.join(phrases)}")
            
            # Combine context with response
            text = f"{' | '.join(context_parts)}\n\nResponse: {response_text}"
            
            # Extract followups
            followups = []
            if followup_col in df.columns:
                raw = str(row[followup_col]).strip()
                if raw:
                    followups = split_followups_cell(raw)
                    
            all_passages.append({
                "doc": doc_name,
                "sheet": sheet,
                "row": int(idx),
                "col": ", ".join([response_col, intent_col, category_col, training_col, followup_col]),
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
