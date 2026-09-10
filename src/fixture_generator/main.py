"""
Fixture generation script for nicovideo provider tests.

This script uses authentication credentials to fetch actual responses from the Niconico API
and saves them as static fixtures for testing.

Note:
Fixtures generated with user credentials will contain personal user data.
Always submit fixtures created with a dedicated test account only.

Usage:
1. Set the NICONICO_SESSION environment variable
2. Run this script: python scripts/main.py
3. Fixture files will be generated in the fixtures/ directory
4. Copy generated fixtures to Music Assistant server repository

Authentication:
Environment variable (NICONICO_SESSION) is required for security.
This prevents accidental commits of hardcoded credentials.

"""

from __future__ import annotations

import asyncio
import logging
import os

from src.fixture_generator.constants import COLLECTION_FAILURE_REPORT_PATH
from src.fixture_generator.generation_orchestrator import (
    FixtureCollectionError,
    FixtureGenerationOrchestrator,
)

# Logging configuration
logging.basicConfig(level=logging.INFO)


async def main() -> None:
    """Run fixture generation with environment variable authentication.

    Required environment variable:
        NICONICO_SESSION: User session token for Niconico API access

    This approach prevents accidental commits of hardcoded credentials
    while maintaining provider isolation (no repository-wide pre-commit hooks).

    Fixtures that could not be collected are written to COLLECTION_FAILURE_REPORT_PATH
    before the error propagates, so a non-zero exit is accompanied by the failure list.
    """
    session = os.getenv("NICONICO_SESSION")

    if not session:
        msg = (
            "NICONICO_SESSION environment variable is required.\n"
            "Set it before running this script:\n"
            "  export NICONICO_SESSION='your_session_token'"
        )
        raise ValueError(msg)

    try:
        await FixtureGenerationOrchestrator().run_all_fixtures(session)
    except FixtureCollectionError as err:
        COLLECTION_FAILURE_REPORT_PATH.write_text(
            "\n".join(err.failed_fixtures) + "\n", encoding="utf-8"
        )
        raise


if __name__ == "__main__":
    asyncio.run(main())
