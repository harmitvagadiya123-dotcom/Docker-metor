"""
LinkedIn Authority Mentor — Main Entry Point

This is the entry point for the Dockerized agent.
Runs the LinkedIn post pipeline on a schedule (default: Mon/Wed/Fri at 6 PM IST).

Usage:
    # Run with scheduler (default — keeps running)
    python -m src.main

    # Run once immediately (for testing / manual execution)
    python -m src.main --run-now

    # Run in dry-run mode (local CSV, no LinkedIn posting)
    python -m src.main --dry-run

    # Verify configuration only
    python -m src.main --verify
"""

import argparse
import json
import logging
import signal
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .config.settings import get_settings, Settings
from .agents.orchestrator import LinkedInMentorOrchestrator


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)


logger = logging.getLogger("linkedin-mentor")


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Minimal handler for Render health checks."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        # Suppress logging for health checks to keep logs clean
        return


def start_health_server(port: int):
    """Start a lightweight health check server in a background thread."""
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"🚀 Health check server started on port {port}")
        return server
    except Exception as e:
        logger.error(f"❌ Failed to start health check server: {e}")
        return None


def run_job(settings: Settings) -> None:
    """Execute one pipeline run. Called by the scheduler or --run-now."""
    logger.info("⏰ Scheduled job triggered")
    try:
        orchestrator = LinkedInMentorOrchestrator(settings, dry_run=settings.dry_run)
        result = orchestrator.run_pipeline()

        # Log summary
        if result.get("success"):
            logger.info(f"[OK] Job completed successfully in {result.get('duration_seconds', 0):.1f}s")
        else:
            logger.warning(f"[WARN] Job completed with issues: {result.get('error', 'Unknown')}")

    except Exception as e:
        logger.error(f"[ERROR] Job failed with exception: {e}", exc_info=True)


def verify_config(settings: Settings) -> bool:
    """Verify all configuration and connections."""
    logger.info("🔍 Verifying configuration...")
    all_ok = True

    # Check OpenAI
    logger.info("  Checking OpenAI API key...")
    if settings.openai_api_key and settings.openai_api_key.startswith("sk-"):
        logger.info("  [OK] OpenAI API key format looks valid")
    else:
        logger.error("  [FAIL] OpenAI API key missing or invalid format")
        all_ok = False

    # Check Google Sheets credentials
    logger.info("  Checking Google Sheets credentials...")
    try:
        creds = settings.get_google_credentials_dict()
        if "client_email" in creds:
            logger.info(f"  [OK] Google credentials valid - Service account: {creds['client_email']}")
        else:
            logger.error("  [FAIL] Google credentials missing client_email")
            all_ok = False
    except Exception as e:
        logger.error(f"  [ERROR] Google credentials error: {e}")
        all_ok = False

    # Check LinkedIn
    logger.info("  Checking LinkedIn access token...")
    if settings.linkedin_access_token:
        from .tools.linkedin_api import LinkedInService
        linkedin = LinkedInService(settings.linkedin_access_token, settings.linkedin_person_urn)
        if linkedin.verify_token():
            logger.info("  [OK] LinkedIn token is valid")
        else:
            logger.error("  [FAIL] LinkedIn token is invalid or expired")
            all_ok = False
    else:
        logger.error("  [FAIL] LinkedIn access token not set")
        all_ok = False

    # Check schedule
    logger.info(f"  Schedule: {settings.schedule_days} at {settings.schedule_hour}:{settings.schedule_minute:02d} {settings.schedule_timezone}")

    if all_ok:
        logger.info("\n[OK] All checks passed! Ready to run.")
    else:
        logger.error("\n[FAIL] Some checks failed. Please fix the issues above.")

    return all_ok


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="LinkedIn Authority Mentor — Agentic AI for LinkedIn Content Posting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main              # Start scheduler (Mon/Wed/Fri at 6 PM IST)
  python -m src.main --run-now    # Run pipeline once immediately
  python -m src.main --dry-run    # Run once locally without Google/LinkedIn
  python -m src.main --verify     # Verify configuration and connections
        """,
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run the pipeline once immediately and exit",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify configuration and connections, then exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run once immediately using local CSV and skipping LinkedIn post",
    )
    parser.add_argument(
        "--use-csv",
        action="store_true",
        help="Force use of local CSV instead of Google Sheets as data source",
    )

    args = parser.parse_args()

    # Load settings
    try:
        settings = get_settings()
    except Exception as e:
        print(f"❌ Failed to load settings: {e}")
        print("   Make sure .env file exists or environment variables are set.")
        print("   Copy .env.example to .env and fill in your values.")
        sys.exit(1)

    # Setup logging
    setup_logging(settings.log_level)

    logger.info("=" * 60)
    logger.info("🏢 LinkedIn Authority Mentor — Agentic AI")
    logger.info("   Replacing n8n + Make.com with pure Python agents")
    logger.info("=" * 60)
    logger.info("  Model: " + settings.openai_model)
    if not args.dry_run and not settings.dry_run:
        if args.use_csv or settings.use_csv:
            logger.info("  Mode: [CSV] (Local CSV)")
        else:
            logger.info("  Sheet: " + settings.google_sheet_id[:20] + "...")
            logger.info("  Tab: " + settings.google_sheet_name)
    else:
        logger.info("  Mode: [TEST] DRY-RUN (Local CSV)")
        logger.info("  Test CSV: " + (settings.test_csv_path or 'data/test_queries.csv'))
    
    logger.info(f"  Schedule: {settings.schedule_days} @ {settings.schedule_hour}:{settings.schedule_minute:02d} {settings.schedule_timezone}")

    # Verify mode
    if args.verify:
        success = verify_config(settings)
        sys.exit(0 if success else 1)

    # Run now or Dry run mode
    if args.run_now or args.dry_run or args.use_csv:
        if args.dry_run:
            settings.dry_run = True
            logger.info("\n[TEST] Running in DRY-RUN mode...")
        elif args.use_csv:
            settings.use_csv = True
            logger.info("\n[CSV] Using local CSV as data source...")
        
        if args.run_now:
            logger.info("\n[RUN] Running pipeline immediately (--run-now mode)...")
        
        run_job(settings)
        logger.info("Done. Exiting.")
        sys.exit(0)

    # Scheduler mode (default)
    logger.info("\n📅 Starting scheduler...")

    # Build cron trigger from settings
    days_map = {
        "mon": "0", "tue": "1", "wed": "2", "thu": "3",
        "fri": "4", "sat": "5", "sun": "6",
    }
    day_numbers = ",".join(
        days_map.get(d.strip(), d.strip())
        for d in settings.schedule_days.split(",")
    )

    scheduler = BlockingScheduler(timezone=settings.schedule_timezone)
    scheduler.add_job(
        run_job,
        trigger=CronTrigger(
            day_of_week=settings.schedule_days,
            hour=settings.schedule_hour,
            minute=settings.schedule_minute,
            timezone=settings.schedule_timezone,
        ),
        args=[settings],
        id="linkedin_mentor_job",
        name="LinkedIn Authority Mentor Pipeline",
        max_instances=1,
        replace_existing=True,
    )

    # Graceful shutdown
    def shutdown_handler(signum, frame):
        logger.info("\n🛑 Shutdown signal received. Stopping scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    # Start health check server (Required for Render Free Tier)
    start_health_server(settings.port)

    logger.info(
        f"✅ Scheduler started. Next run: "
        f"{settings.schedule_days} at {settings.schedule_hour}:{settings.schedule_minute:02d} "
        f"{settings.schedule_timezone}"
    )
    logger.info("   Press Ctrl+C to stop.\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Scheduler stopped. Goodbye!")


if __name__ == "__main__":
    main()
