"""
Application settings loaded from environment variables.
Uses Pydantic Settings for validation and type safety.
"""

import base64
import json
import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configuration for the LinkedIn Authority Mentor agent."""

    # --- OpenAI ---
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")

    # --- Google Sheets ---
    google_sheets_credentials_b64: str = Field(
        default="", description="Base64-encoded Google service account JSON key (optional in dry-run mode)"
    )
    google_sheet_id: str = Field(
        default="1KbMDOnQuvRXQGCSIO1V0TBRUAprGtktN441Z_ktDUmk",
        description="Google Sheet document ID",
    )
    google_sheet_name: str = Field(
        default="Sheet1",
        description="Name of the worksheet/tab",
    )

    # --- LinkedIn ---
    linkedin_access_token: str = Field(..., description="LinkedIn OAuth2 access token")
    linkedin_person_urn: str = Field(
        ..., description="LinkedIn person URN (e.g., urn:li:person:abc123)"
    )

    # --- Schedule ---
    schedule_days: str = Field(
        default="mon,wed,fri", description="Comma-separated days to run"
    )
    schedule_hour: int = Field(default=18, description="Hour to run (24-hour format)")
    schedule_minute: int = Field(default=0, description="Minute to run")
    schedule_timezone: str = Field(
        default="Asia/Kolkata", description="Timezone for schedule"
    )

    # --- Dry Run / Testing ---
    dry_run: bool = Field(
        default=False,
        description="Run in dry-run mode: use local CSV instead of Google Sheets, skip LinkedIn posting",
    )
    test_csv_path: str = Field(
        default="",
        description="Path to test CSV file (used in dry-run mode). Defaults to data/test_queries.csv",
    )
    use_csv: bool = Field(
        default=False,
        description="Force use of local CSV instead of Google Sheets, even if not in dry-run mode",
    )

    # --- Logging ---
    log_level: str = Field(default="INFO", description="Logging level")

    # --- Server (for Health Checks) ---
    port: int = Field(default=10000, description="Port for the health check server")

    # --- Manual Trigger ---
    execute_now: bool = Field(
        default=False,
        description="If true, executes the pipeline immediately on startup before entering scheduler mode",
    )

    # --- Default Content Inputs ---
    default_story_input: str = Field(
        default=(
            "I once heard a dealer say, \"Anand, selling pumps is all about reliability, "
            "not efficiency.\" It struck a chord with me. In our industry, many believe that "
            "prioritizing speed can compromise quality. But here's the kicker: small mistakes "
            "in paperwork can lead to significant losses. I remember a time when a simple "
            "miscommunication about a motor's specifications not only delayed our shipment "
            "but also resulted in a costly return due to motor failure. The ripple effect? "
            "Lost deals, frustrated clients, and a damaged reputation. As painful as that "
            "experience was, it served as a wake-up call. I realized we were chasing quick "
            "sales instead of building lasting relationships with our clients. Selling reliable "
            "products that we fully understood had to be our priority. We revamped our "
            "communication with dealers and rebuilt our processes from the ground up. Now, "
            "every product going out undergoes rigorous quality checks, ensuring we're "
            "dispatching equipment that we trust. It's no longer just about meeting demands; "
            "it's about exceeding expectations through stellar support. The results have been "
            "remarkable. Complaints decreased by 60%, leading to a doubling of repeat orders "
            "over six months. Our dealers feel confident in what they're selling, and our "
            "revenue reflects that trust. The real lesson for us has been clear: trust in "
            "selling is just as important as product reliability. We're not just focused on "
            "one-time sales; we're committed to nurturing long-term partnerships with our "
            "clients. Ultimately, it's about building a business that thrives on trust rather "
            "than quick profits. What strategies have you implemented to build trust with your "
            "clients? P.S. If you've ever faced a similar challenge, I'd love to hear your story!"
        ),
        description="Default story input template",
    )
    default_industry: str = Field(
        default="Water Pump Manufacturing & Industrial Equipment Supply",
        description="Industry context for posts",
    )
    default_audience: str = Field(
        default="Water pump dealers, distributors, industrial buyers, and small business owners in manufacturing",
        description="Target audience for posts",
    )

    @field_validator("schedule_days")
    @classmethod
    def validate_days(cls, v: str) -> str:
        valid_days = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
        days = [d.strip().lower() for d in v.split(",")]
        for d in days:
            if d not in valid_days:
                raise ValueError(f"Invalid day: {d}. Must be one of {valid_days}")
        return v

    def get_google_credentials_dict(self) -> dict:
        """Decode the base64-encoded Google service account JSON."""
        if not self.google_sheets_credentials_b64:
            raise ValueError(
                "Google Sheets credentials not set. "
                "Either provide GOOGLE_SHEETS_CREDENTIALS_B64 or use --dry-run mode."
            )
        
        # Clean the string (strip whitespace and common accidental quotes)
        b64_str = self.google_sheets_credentials_b64.strip().strip('"').strip("'")
        
        # Remove all internal whitespace/newlines
        b64_str = "".join(b64_str.split())
        
        # Normalize padding: remove existing and re-add correctly
        b64_str = b64_str.rstrip("=")
        missing_padding = len(b64_str) % 4
        if missing_padding:
            b64_str += "=" * (4 - missing_padding)

        try:
            decoded = base64.b64decode(b64_str)
            return json.loads(decoded)
        except Exception as e:
            # Provide more context for debugging without leaking the secret
            length = len(b64_str)
            raw_length = len(self.google_sheets_credentials_b64)
            chars_sample = b64_str[:5] + "..." + b64_str[-5:] if length > 10 else b64_str
            raise ValueError(
                f"Failed to decode Google Sheets credentials: {e}\n"
                f"  - Cleaned length: {length} (multiple of 4: {length % 4 == 0})\n"
                f"  - Original length: {raw_length}\n"
                f"  - Sample: {chars_sample}\n"
                f"  - Tip: Ensure you encoded the JSON file with 'base64 -w 0 service-account.json'"
            )

    def get_schedule_days_list(self) -> list[str]:
        """Return schedule days as a list."""
        return [d.strip().lower() for d in self.schedule_days.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
