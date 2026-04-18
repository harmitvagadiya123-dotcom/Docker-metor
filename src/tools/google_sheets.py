"""
Google Sheets integration tool.
Reads unprocessed content rows and writes back generated posts.
Replaces the Google Sheets nodes from the n8n workflow.
"""

import logging
from typing import Any, Optional

import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


class GoogleSheetsService:
    """
    Manages all Google Sheets interactions:
    - Reading the first unprocessed row (LinkedInAuthorityStatus is empty)
    - Writing back the generated post and marking as "Done"
    """

    def __init__(self, credentials_dict: dict, sheet_id: str, sheet_name: str):
        """
        Initialize Google Sheets service.
        
        Args:
            credentials_dict: Decoded service account JSON credentials
            sheet_id: The Google Sheet document ID
            sheet_name: The worksheet/tab name
        """
        self.sheet_id = sheet_id
        self.sheet_name = sheet_name

        # Authenticate with service account
        creds = Credentials.from_service_account_info(
            credentials_dict, scopes=SCOPES
        )
        self.client = gspread.authorize(creds)

        logger.info(f"[-] Google Sheets connected: Sheet={sheet_id[:20]}..., Tab={sheet_name}")

    def _get_worksheet(self) -> gspread.Worksheet:
        """Get the target worksheet."""
        spreadsheet = self.client.open_by_key(self.sheet_id)
        return spreadsheet.worksheet(self.sheet_name)

    def read_next_unprocessed_row(self) -> Optional[dict[str, Any]]:
        """
        Read the first row where LinkedInAuthorityStatus is empty.
        Replicates the n8n Google Sheets node with filter:
        filtersUI.values[0].lookupColumn = "LinkedInAuthorityStatus" (empty)
        options.returnFirstMatch = true
        
        Returns:
            Dict with row data including row_number, or None if no unprocessed rows
        """
        logger.info("[-] Reading next unprocessed row from Google Sheets...")

        try:
            worksheet = self._get_worksheet()
            all_records = worksheet.get_all_records()

            if not all_records:
                logger.warning("[WARN] No records found in the sheet")
                return None

            # Find the first row where LinkedInAuthorityStatus is empty
            for idx, record in enumerate(all_records):
                status = str(record.get("LinkedInAuthorityStatus", "")).strip()
                if not status:
                    # Row number is idx + 2 (1 for header, 1 for 0-index)
                    row_number = idx + 2
                    result = {
                        "row_number": row_number,
                        "Query": record.get("Query", ""),
                        "LinkedInAuthorityStatus": status,
                        "Recreated Story": record.get("Recreated Story", ""),
                    }
                    logger.info(f"[OK] Found unprocessed row #{row_number}")
                    logger.info(f"  Query: {result['Query'][:100]}...")
                    return result

            logger.info("[-] No unprocessed rows found — all rows are marked Done")
            return None

        except Exception as e:
            logger.error(f"[FAIL] Error reading Google Sheets: {e}")
            raise

    def update_row_with_post(self, row_number: int, recreated_story: str) -> bool:
        """
        Update a row with the generated post and mark as "Done".
        Replicates the n8n Google Sheets1 (update) node:
        - Writes "Recreated Story" column
        - Sets "LinkedInAuthorityStatus" to "Done"
        
        Args:
            row_number: The row number to update (1-indexed)
            recreated_story: The generated LinkedIn post text
            
        Returns:
            True if update succeeded
        """
        logger.info(f"[-] Updating row #{row_number} in Google Sheets...")

        try:
            worksheet = self._get_worksheet()
            headers = worksheet.row_values(1)

            # Find column indices
            status_col = None
            story_col = None

            for i, header in enumerate(headers):
                if header == "LinkedInAuthorityStatus":
                    status_col = i + 1  # gspread is 1-indexed
                elif header == "Recreated Story":
                    story_col = i + 1

            if status_col is None or story_col is None:
                logger.error(
                    f"[FAIL] Required columns not found. Headers: {headers}"
                )
                return False

            # Batch update both cells
            worksheet.update_cell(row_number, story_col, recreated_story)
            worksheet.update_cell(row_number, status_col, "Done")

            logger.info(f"[OK] Row #{row_number} updated: Status=Done, Story written")
            return True

        except Exception as e:
            logger.error(f"[FAIL] Error updating Google Sheets: {e}")
            raise
