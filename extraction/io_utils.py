from __future__ import annotations
import json
from pathlib import Path
import pandas as pd


def resolve_project_root(current_file: str) -> Path:
    """
    Resolve the root of the project from the location of the current file.
    """
    # Use the location of this script to find the top-level project folder.
    # I did this so the paths work automatically whether you run it from 
    # the root folder or the scripts folder.
    return Path(current_file).resolve().parent.parent


def save_json(data, output_path: Path) -> None:
    """
    Save Python object as JSON with pretty formatting.
    """
    # Create the directory if it doesn't exist yet.
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Open the file and dump the data.
    with open(output_path, "w", encoding="utf-8") as f:
        # I added indent=2 so the JSON is human-readable on GitHub.
        # I also used default=str so it doesn't crash on non-serializable objects.
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def load_email_dataframe(input_path: Path) -> pd.DataFrame:
    """
    Load the Enron dataset and determine which column contains email text.
    This version loads the full dataset and leaves batch selection to the pipeline.
    """

    # Load the CSV file into a pandas DataFrame.
    df = pd.read_csv(input_path)

    # Possible columns containing email text.
    # I noticed that different versions of the Enron dataset use different column names,
    # so I'm checking for the most common ones here.
    candidate_columns = ["body_only", "message", "text", "content"]

    text_column = None
    for col in candidate_columns:
        if col in df.columns:
            text_column = col
            break

    # You'll get an error here if the CSV doesn't match our expected format.
    if text_column is None:
        raise ValueError(
            f"No valid email text column found. Available columns: {list(df.columns)}"
        )

    if "file" not in df.columns:
        raise ValueError(
            f"Dataset must contain a 'file' column. Found columns: {list(df.columns)}"
        )

    # Clean the data by removing rows where the file ID or message is missing.
    df = df.dropna(subset=["file", text_column]).copy()

    # Store the chosen text column name in the metadata so the pipeline can find it.
    df.attrs["text_column"] = text_column

    return df