from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json(path: Path) -> List[Dict[str, Any]]:
    # First, I need to check if the file actually exists so the script doesn't just crash
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # I'm opening the file here to read all those extracted memories we saved earlier
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # You have to make sure the data is a list, otherwise the rest of my loops will fail
    if not isinstance(data, list):
        raise ValueError(f"Expected a list in {path}, got {type(data).__name__}")

    return data


def save_json(data: List[Dict[str, Any]], path: Path) -> None:
    # This part is cool: it creates the folder for you if you haven't made it yet
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        # I'm using indent=2 so you can actually read the JSON without it being one giant line
        json.dump(data, f, indent=2, ensure_ascii=False)


def normalize_text(value: Any) -> str:
    # Sometimes the AI returns 'None' or extra spaces, so I use this to clean things up
    if value is None:
        return ""
    return str(value).strip()


def dedupe_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # I'm using a set called 'seen' to keep track of names we already found
    seen: set[Tuple[str, str]] = set()
    deduped: List[Dict[str, Any]] = []

    for entity in entities or []:
        # You want to make everything lowercase when checking for duplicates so 'Apple' and 'apple' match
        name = normalize_text(entity.get("name")).lower()
        label = normalize_text(entity.get("label")).upper()

        key = (name, label)
        # If the name is blank or you've already seen this person/place, just skip it
        if not name or key in seen:
            continue

        seen.add(key)
        deduped.append({
            "name": normalize_text(entity.get("name")),
            "label": label,
        })

    return deduped


def dedupe_relationships(relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Similar to entities, I'm building a unique key for each relationship
    seen: set[Tuple[str, str, str]] = set()
    deduped: List[Dict[str, Any]] = []

    for rel in relationships or []:
        source_entity = normalize_text(rel.get("source_entity"))
        target_entity = normalize_text(rel.get("target_entity"))
        relation_type = normalize_text(rel.get("relation_type")).upper()
        evidence_quote = normalize_text(rel.get("evidence_quote")) or None

        # This key makes sure you don't save the same connection twice
        key = (
            source_entity.lower(),
            target_entity.lower(),
            relation_type,
        )

        if not source_entity or not target_entity or not relation_type or key in seen:
            continue

        seen.add(key)
        item = {
            "source_entity": source_entity,
            "target_entity": target_entity,
            "relation_type": relation_type,
        }
        # Only add the quote if it actually exists!
        if evidence_quote:
            item["evidence_quote"] = evidence_quote

        deduped.append(item)

    return deduped


def dedupe_claims(claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Claims are longer, so I'm checking the subject and the fact together
    seen: set[Tuple[str, str, str, str]] = set()
    deduped: List[Dict[str, Any]] = []

    for claim in claims or []:
        subject = normalize_text(claim.get("subject"))
        fact = normalize_text(claim.get("fact"))
        evidence_quote = normalize_text(claim.get("evidence_quote"))
        source_file = normalize_text(claim.get("source_file"))
        timestamp = normalize_text(claim.get("timestamp")) or None
        confidence = claim.get("confidence")

        key = (
            subject.lower(),
            fact.lower(),
            evidence_quote.lower(),
            source_file.lower(),
        )

        # If any major info is missing, you probably don't want to keep the claim
        if not subject or not fact or not evidence_quote or not source_file or key in seen:
            continue

        seen.add(key)

        item = {
            "subject": subject,
            "fact": fact,
            "evidence_quote": evidence_quote,
            "source_file": source_file,
        }

        # I made these optional because the AI doesn't always find a date or score
        if timestamp:
            item["timestamp"] = timestamp

        if confidence is not None:
            item["confidence"] = confidence

        deduped.append(item)

    return deduped


def dedupe_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # This is the main cleaner. I'm grouping everything by the email ID.
    latest_by_email_id: Dict[str, Dict[str, Any]] = {}

    for record in records:
        # You can find the ID in two places, so I'm checking both just in case
        email_id = normalize_text(record.get("email_id")) or normalize_text(
            record.get("metadata", {}).get("file")
        )

        if not email_id:
            continue

        # Here I am calling all the small dedupe functions I wrote above
        cleaned_record = {
            "email_id": email_id,
            "metadata": {
                "file": normalize_text(record.get("metadata", {}).get("file")) or email_id,
                "status": normalize_text(record.get("metadata", {}).get("status")) or "success",
            },
            "entities": dedupe_entities(record.get("entities", [])),
            "relationships": dedupe_relationships(record.get("relationships", [])),
            "claims": dedupe_claims(record.get("claims", [])),
        }

        # If we have the same email ID twice, the latest one will overwrite the old one
        latest_by_email_id[email_id] = cleaned_record

    return list(latest_by_email_id.values())


def main() -> None:
    # I'm setting up the paths so it knows exactly where to find the data folder
    project_root = Path(__file__).resolve().parent.parent
    input_path = project_root / "data" / "processed" / "extracted_memories.json"
    output_path = project_root / "data" / "processed" / "deduped_memories.json"

    # Step 1: Load the messy data
    records = load_json(input_path)
    # Step 2: Run the cleaner
    deduped_records = dedupe_records(records)
    # Step 3: Save the nice, clean version
    save_json(deduped_records, output_path)

    # I like printing a summary at the end so you can see how many duplicates I removed
    print("=== Deduplication Summary ===")
    print(f"Input records: {len(records)}")
    print(f"Deduped records: {len(deduped_records)}")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    # This is where the magic starts!
    main()