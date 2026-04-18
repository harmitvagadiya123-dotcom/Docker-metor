"""
Pipeline Orchestrator — Runs the complete LinkedIn post generation workflow.
Coordinates all agents and tools in the correct sequence.

Workflow:
1. Read unprocessed row from Google Sheets
2. Prepare input fields
3. Run Agent 1 (Content Strategist) → Generate outline
4. Run Agent 2 (Post Formatter) → Polish into final post
5. Update Google Sheet with generated post + mark "Done"
6. Post to LinkedIn via API
"""

import logging
from datetime import datetime
from typing import Optional

from ..config.settings import Settings
from ..tools.google_sheets import GoogleSheetsService
from ..tools.local_csv import LocalCSVService
from ..tools.linkedin_api import LinkedInService
from .content_strategist import ContentStrategistAgent
from .post_formatter import PostFormatterAgent

logger = logging.getLogger(__name__)


class LinkedInMentorOrchestrator:
    """
    Orchestrates the complete LinkedIn authority post pipeline.
    This is the main controller that replaces the n8n + Make.com workflow.
    """

    def __init__(self, settings: Settings, dry_run: bool = False):
        """Initialize all agents and tools."""
        self.settings = settings
        self.dry_run = dry_run

        # Initialize tools
        logger.info("🔧 Initializing tools...")

        if self.dry_run or settings.use_csv:
            source_name = "local CSV"
            logger.info(f"[-] Data source: {source_name}")
            self.data_service = LocalCSVService(csv_path=settings.test_csv_path)
        else:
            source_name = "Google Sheets"
            logger.info(f"[-] Data source: {source_name}")
            self.data_service = GoogleSheetsService(
                credentials_dict=settings.get_google_credentials_dict(),
                sheet_id=settings.google_sheet_id,
                sheet_name=settings.google_sheet_name,
            )

        if not self.dry_run:
            self.linkedin_service = LinkedInService(
                access_token=settings.linkedin_access_token,
                person_urn=settings.linkedin_person_urn,
            )
        else:
            self.linkedin_service = None
            logger.info("[-] DRY-RUN MODE - LinkedIn posting will be skipped")

        # Initialize agents
        logger.info("🤖 Initializing agents...")
        self.content_strategist = ContentStrategistAgent(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )
        self.post_formatter = PostFormatterAgent(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
        )

        logger.info("✅ Orchestrator ready")

    def run_pipeline(self) -> dict:
        """
        Execute the complete pipeline.
        
        Returns:
            Dict with results of each step
        """
        run_start = datetime.now()
        logger.info("\n" + "=" * 70)
        logger.info(f"PIPELINE START - {run_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 70)

        result = {
            "started_at": run_start.isoformat(),
            "steps": {},
            "success": False,
        }

        try:
            # ─── Step 1: Read from data source ─────────────────────────
            source_name = "local CSV" if (self.dry_run or self.settings.use_csv) else "Google Sheets"
            logger.info(f"\nSTEP 1: Reading next unprocessed row from {source_name}...")
            row_data = self.data_service.read_next_unprocessed_row()

            if not row_data:
                logger.info("[-] No unprocessed rows found. Pipeline complete.")
                result["steps"]["read_sheet"] = "No unprocessed rows"
                result["success"] = True
                return result

            result["steps"]["read_sheet"] = {
                "row_number": row_data["row_number"],
                "query": row_data.get("Query", "")[:100],
            }

            # ─── Step 2: Prepare input fields ────────────────────────────
            logger.info("\nSTEP 2: Preparing input fields...")
            problem = row_data.get("Query", "")
            story_input = self.settings.default_story_input
            industry = self.settings.default_industry
            audience = self.settings.default_audience

            logger.info(f"  Problem/Query: {problem[:100]}...")
            logger.info(f"  Industry: {industry}")
            logger.info(f"  Audience: {audience[:80]}...")

            result["steps"]["prepare_fields"] = {"problem": problem[:100]}

            # ─── Step 3: Generate Outline (Agent 1) ──────────────────────
            logger.info("\nSTEP 3: Agent 1 (Content Strategist) generating outline...")
            outline = self.content_strategist.generate_outline(
                story_input=story_input,
                industry=industry,
                problem=problem,
                audience=audience,
                result="",  # The n8n workflow has this empty by default
            )

            result["steps"]["generate_outline"] = {
                "length": len(outline),
                "preview": outline[:200],
            }

            # ─── Step 4: Format Post (Agent 2) ───────────────────────────
            logger.info("\nSTEP 4: Agent 2 (Post Formatter) polishing post...")
            final_post = self.post_formatter.format_post(outline)

            result["steps"]["format_post"] = {
                "length": len(final_post),
                "preview": final_post[:200],
            }

            logger.info(f"\n{'-'*50}")
            logger.info("FINAL POST PREVIEW:")
            logger.info(f"{'-'*50}")
            # Show first 500 chars
            for line in final_post[:500].split("\n"):
                logger.info(f"  {line}")
            if len(final_post) > 500:
                logger.info(f"  ... ({len(final_post) - 500} more chars)")
            logger.info(f"{'─'*50}")

            # ─── Step 5: Update data source ────────────────────────────
            logger.info(f"\nSTEP 5: Writing post back to {source_name}...")
            sheet_updated = self.data_service.update_row_with_post(
                row_number=row_data["row_number"],
                recreated_story=final_post,
            )

            result["steps"]["update_sheet"] = {
                "success": sheet_updated,
                "row_number": row_data["row_number"],
            }

            # ─── Step 6: Post to LinkedIn ────────────────────────────────
            if self.dry_run:
                logger.info("\nSTEP 6: [DRY-RUN] Skipping LinkedIn post. Final post saved to CSV.")
                logger.info("\n" + "=" * 60)
                logger.info("GENERATED POST (would be posted to LinkedIn):")
                logger.info("=" * 60)
                print("\n" + final_post + "\n")
                logger.info("=" * 60)
                linkedin_result = {"success": True, "dry_run": True, "post_id": "dry-run-no-post"}
            else:
                logger.info("\nSTEP 6: Posting to LinkedIn...")
                linkedin_result = self.linkedin_service.create_post(
                    content=final_post,
                    visibility="PUBLIC",
                    feed_distribution="MAIN_FEED",
                )

            result["steps"]["post_linkedin"] = linkedin_result

            # ─── Done ────────────────────────────────────────────────────
            run_end = datetime.now()
            duration = (run_end - run_start).total_seconds()

            result["success"] = linkedin_result.get("success", False)
            result["completed_at"] = run_end.isoformat()
            result["duration_seconds"] = duration

            if result["success"]:
                logger.info(f"\nPIPELINE COMPLETE - Success! Duration: {duration:.1f}s")
            else:
                error_detail = linkedin_result.get("error", "Unknown error")
                logger.warning(
                    f"\n[FAIL] PIPELINE COMPLETE - LinkedIn post failed. "
                    f"Error: {error_detail} "
                    f"Duration: {duration:.1f}s"
                )

            return result

        except Exception as e:
            logger.error(f"\n[ERROR] PIPELINE FAILED: {e}", exc_info=True)
            result["error"] = str(e)
            result["completed_at"] = datetime.now().isoformat()
            return result
