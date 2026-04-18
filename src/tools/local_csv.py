"""
Local CSV data source — Drop-in replacement for GoogleSheetsService.
Used for testing (--dry-run) without needing a Google service account.
Reads/writes to a local CSV file with the same column schema as the sheet.
"""

import csv
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "test_queries.csv")


class LocalCSVService:
    """
    Drop-in replacement for GoogleSheetsService that uses a local CSV file.
    Same interface: read_next_unprocessed_row() and update_row_with_post().
    """

    def __init__(self, csv_path: str = ""):
        """
        Initialize CSV data source.

        Args:
            csv_path: Path to the CSV file. Defaults to data/test_queries.csv.
        """
        self.csv_path = csv_path or os.path.abspath(DEFAULT_CSV_PATH)

        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(
                f"Test CSV not found at {self.csv_path}\n"
                f"Run with default data or create the file with columns: "
                f"Query, LinkedInAuthorityStatus, Recreated Story"
            )

        logger.info(f"[-] Local CSV data source: {self.csv_path}")

    def _read_all_rows(self) -> list[dict[str, str]]:
        """Read all rows from the CSV file."""
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def _write_all_rows(self, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
        """Write all rows back to the CSV file."""
        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def read_next_unprocessed_row(self) -> Optional[dict[str, Any]]:
        """
        Read the first row where LinkedInAuthorityStatus is empty.
        Same interface as GoogleSheetsService.read_next_unprocessed_row().

        Returns:
            Dict with row data including row_number, or None if no unprocessed rows.
        """
        logger.info("[-] Reading next unprocessed row from local CSV...")

        rows = self._read_all_rows()

        if not rows:
            logger.warning("[WARN] No records found in the CSV file")
            return None

        for idx, record in enumerate(rows):
            status = str(record.get("LinkedInAuthorityStatus", "")).strip()
            if not status:
                row_number = idx + 2  # Match sheet behavior (1 header + 0-index)
                result = {
                    "row_number": row_number,
                    "Query": record.get("Query", ""),
                    "LinkedInAuthorityStatus": status,
                    "Recreated Story": record.get("Recreated Story", ""),
                }
                logger.info(f"[OK] Found unprocessed row #{row_number}")
                logger.info(f"  Query: {result['Query'][:100]}...")
                return result

        logger.info("ℹ️ No unprocessed rows found — all rows are marked Done")
        return None

    def update_row_with_post(self, row_number: int, recreated_story: str) -> bool:
        """
        Update a row with the generated post and mark as Done.
        Same interface as GoogleSheetsService.update_row_with_post().

        Args:
            row_number: The row number to update (1-indexed, header = row 1)
            recreated_story: The generated LinkedIn post text

        Returns:
            True if update succeeded
        """
        logger.info(f"[-] Updating row #{row_number} in local CSV...")

        try:
            rows = self._read_all_rows()
            if not rows:
                logger.error("[FAIL] CSV file is empty")
                return False

            fieldnames = list(rows[0].keys())
            idx = row_number - 2  # Convert back (row 2 = index 0)

            if idx < 0 or idx >= len(rows):
                logger.error(f"[FAIL] Row #{row_number} out of range (CSV has {len(rows)} data rows)")
                return False

            rows[idx]["Recreated Story"] = recreated_story
            rows[idx]["LinkedInAuthorityStatus"] = "Done"

            self._write_all_rows(rows, fieldnames)

            logger.info(f"[OK] Row #{row_number} updated in CSV: Status=Done, Story written")
            return True

        except Exception as e:
            logger.error(f"[FAIL] Error updating CSV: {e}")
            raise
