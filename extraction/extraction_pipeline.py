from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Set

# I'm importing these from my other files to keep this script clean
from .io_utils import load_email_dataframe, resolve_project_root, save_json
from .processor import EnronProcessor

# I set these as defaults so I don't accidentally spend too much money at once!
DEFAULT_BATCH_SIZE = 5
MAX_EMAIL_CHARS = 1200


def parse_args() -> argparse.Namespace:
    # This part lets you run the script from the terminal with custom settings
    parser = argparse.ArgumentParser(description="Run the Enron extraction pipeline.")
    parser.add_argument(
        "--input",
        default=None,
        help="Path to the CSV dataset. Defaults to data/raw/sample_emails.csv",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to the JSON output. Defaults to data/processed/extracted_memories.json",
    )
    parser.add_argument(
        "--failed-output",
        default=None,
        help="Path to the failed records JSON. Defaults to data/processed/failed_emails.json",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of NEW unprocessed emails to extract in this run. Default: 5",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Groq API key. If omitted, GROQ_API_KEY environment variable is used.",
    )
    return parser.parse_args()


def truncate_text(text: str, max_chars: int = MAX_EMAIL_CHARS) -> str:
    # LLMs have token limits, so I'm cutting off the text if it's too long
    if not text:
        return ""
    text = str(text).strip()
    if len(text) <= max_chars:
        return text
    # I add this note so you know if an email was cut short
    return text[:max_chars] + "\n\n[TRUNCATED_FOR_TOKEN_SAVING]"


def load_existing_json(path: Path) -> List[Dict[str, Any]]:
    # Before starting, I check if we already have a save file so we can resume
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        # If the file is corrupted, I just start fresh with an empty list
        return []


def normalize_output(extraction: Any, source_id: str) -> Dict[str, Any]:
    # I'm turning the Pydantic model into a dictionary and adding the file ID
    payload = extraction.model_dump()
    payload["email_id"] = source_id
    payload["metadata"] = {
        "file": source_id,
        "status": "success",
    }
    return payload


def is_rate_limit_error(error_text: str) -> bool:
    # I wrote this to catch when the API tells us to slow down
    error_text = str(error_text).lower()
    signals = [
        "429",
        "rate limit",
        "rate_limit_exceeded",
        "tokens per day",
        "try again in",
        "credit limit",
    ]
    return any(signal in error_text for signal in signals)


def main() -> None:
    args = parse_args()
    project_root = resolve_project_root(__file__)

    # Setting up all the file paths here
    input_path = (
        Path(args.input)
        if args.input
        else project_root / "data" / "raw" / "sample_emails.csv"
    )
    output_path = (
        Path(args.output)
        if args.output
        else project_root / "data" / "processed" / "extracted_memories.json"
    )
    failed_output_path = (
        Path(args.failed_output)
        if args.failed_output
        else project_root / "data" / "processed" / "failed_emails.json"
    )

    # I'm making the folders just in case they don't exist yet
    output_path.parent.mkdir(parents=True, exist_ok=True)
    failed_output_path.parent.mkdir(parents=True, exist_ok=True)

    if not output_path.exists():
        save_json([], output_path)

    if not failed_output_path.exists():
        save_json([], failed_output_path)

    # You need an API key! I'm checking the arguments and environment variables
    api_key = args.api_key or os.getenv("GROQ_API_KEY") or "PASTE_YOUR_GROQ_API_KEY_HERE"
    if api_key == "PASTE_YOUR_GROQ_API_KEY_HERE":
        raise ValueError("Groq API key missing. Pass --api-key YOUR_KEY or set GROQ_API_KEY.")

    # Loading the big CSV of emails
    df = load_email_dataframe(input_path)
    text_column = df.attrs.get("text_column", "message")

    # Loading what we've already done so we don't pay for the same email twice
    existing_records = load_existing_json(output_path)
    failed_records = load_existing_json(failed_output_path)

    success_ids: Set[str] = {
        str(item.get("email_id"))
        for item in existing_records
        if item.get("email_id")
    }

    failed_ids: Set[str] = {
        str(item.get("email_id"))
        for item in failed_records
        if item.get("email_id")
    }

    already_seen_ids = success_ids | failed_ids

    extracted_records: List[Dict[str, Any]] = list(existing_records)
    failed_sources: List[Dict[str, Any]] = list(failed_records)

    # I print these out so you can track the progress in your terminal
    print(f"Total emails in CSV: {len(df)}")
    print(f"Using text column: {text_column}")
    print(f"Already successful: {len(success_ids)}")
    print(f"Already failed: {len(failed_ids)}")
    print(f"Already attempted total: {len(already_seen_ids)}")

    # Only pick the emails we haven't touched yet
    unprocessed_df = df[~df["file"].astype(str).isin(already_seen_ids)].copy()
    batch_df = unprocessed_df.head(args.batch_size)

    print(f"Unprocessed remaining: {len(unprocessed_df)}")
    print(f"Processing this run: {len(batch_df)}")
    print(f"Max chars per email: {MAX_EMAIL_CHARS}")

    if batch_df.empty:
        print("No new emails left to process in this batch.")
        return

    # Initializing the AI processor
    processor = EnronProcessor(api_key=api_key)

    newly_processed = 0
    newly_failed = 0

    # This is the main loop where the "work" happens
    for _, row in batch_df.iterrows():
        source_id = str(row["file"])
        email_text = truncate_text(str(row[text_column]))
        print(f"Processing: {source_id}")

        try:
            extraction = processor.process_email(source_id=source_id, email_text=email_text)

            if extraction is None:
                # If something went wrong but didn't crash, I log it as a failure
                error_record = {
                    "email_id": source_id,
                    "error": "process_email returned None",
                    "metadata": {
                        "file": source_id,
                        "status": "failed",
                    },
                }
                failed_sources.append(error_record)
                save_json(failed_sources, failed_output_path)
                newly_failed += 1
                continue

            # If it worked, I save the result to our main JSON
            record = normalize_output(extraction, source_id)
            extracted_records.append(record)
            save_json(extracted_records, output_path)
            newly_processed += 1

        except Exception as e:
            error_text = str(e)
            print(f"Error while processing {source_id}: {error_text}")

            # I catch all errors here so the whole script doesn't stop because of one bad email
            error_record = {
                "email_id": source_id,
                "error": error_text,
                "metadata": {
                    "file": source_id,
                    "status": "failed",
                },
            }
            failed_sources.append(error_record)
            save_json(failed_sources, failed_output_path)
            newly_failed += 1

            # If it's a rate limit, I stop the whole script gracefully
            if is_rate_limit_error(error_text):
                print("\nRate/credit limit reached. Stopping safely so you can resume later.")
                save_json(extracted_records, output_path)
                save_json(failed_sources, failed_output_path)
                return

    # Final report for the user!
    print("\n=== Extraction Summary ===")
    print(f"New successful this run: {newly_processed}")
    print(f"New failed this run: {newly_failed}")
    print(f"Total successful saved: {len(extracted_records)}")
    print(f"Total failed saved: {len(failed_sources)}")
    print(f"Saved output to: {output_path}")
    print(f"Saved failed records to: {failed_output_path}")


if __name__ == "__main__":
    # This calls the main function when you run 'python pipeline.py'
    main()