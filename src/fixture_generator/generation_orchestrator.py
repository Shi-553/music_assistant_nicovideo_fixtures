"""Main fixture generation orchestrator."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, override

from niconico import NicoNico
from niconico.exceptions import LoginFailureError
from pydantic import BaseModel, ValidationError

from src.fixture_generator.api_fixture_collector import APIFixtureCollector
from src.fixture_generator.constants import GENERATED_FIXTURE_TYPES_PATH, GENERATED_FIXTURES_DIR
from src.fixture_generator.field_stabilizer import FieldStabilizer
from src.fixture_generator.fixture_saver import FixtureSaver
from src.fixture_generator.fixture_types import (
    FixtureAPIResultOptional,
    FixtureCategory,
    FixtureProcessorProtocol,
)
from src.fixture_generator.helpers import to_dict_for_fixture
from src.fixture_generator.type_mapping_generator import (
    FixtureTypeMappingCollector,
    FixtureTypeMappingFileGenerator,
)

logger = logging.getLogger(__name__)


API_CALL_DELAY_SECONDS = 1.0
FIXTURE_LIMIT = 1


class FixtureCollectionError(Exception):
    """Raised when one or more fixtures could not be collected."""

    def __init__(self, failed_fixtures: list[str]) -> None:
        """Initialize with the identifiers of the fixtures that failed."""
        self.failed_fixtures = failed_fixtures
        super().__init__("Failed to collect fixtures: " + ", ".join(failed_fixtures))


class FixtureGenerationOrchestrator(FixtureProcessorProtocol):
    """Main orchestrator for fixture generation process.

    Implements FixtureProcessorProtocol to expose only the necessary interface
    to APIFixtureCollector, preventing tight coupling to internal components
    (field_stabilizer, fixture_saver, fixture_type_mapping).
    """

    def __init__(self) -> None:
        """Initialize the fixture generation orchestrator."""
        self.limit = FIXTURE_LIMIT

        # Initialize components with clear responsibilities
        self.type_mapping_collector = FixtureTypeMappingCollector()
        self.fixture_saver = FixtureSaver()
        self.field_stabilizer = FieldStabilizer()

        # Failures are accumulated instead of raised so that a single broken endpoint
        # does not hide the state of every other fixture
        self.failed_fixtures: list[str] = []

    @override
    async def process_fixture[T: BaseModel, **P](
        self,
        category: FixtureCategory,
        name: str,
        api_call: Callable[
            P, FixtureAPIResultOptional[T] | Coroutine[Any, Any, FixtureAPIResultOptional[T]]
        ],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> FixtureAPIResultOptional[T]:
        """Save API response as fixture and return the data."""
        try:
            logger.info(f"Fetching {category}/{name}...")

            # Add delay before API call
            await asyncio.sleep(API_CALL_DELAY_SECONDS)

            # API call
            if asyncio.iscoroutinefunction(api_call):
                response = await api_call(*args, **kwargs)
            else:
                response = await asyncio.to_thread(api_call, *args, **kwargs)

            if response is None:
                logger.warning(f"No data returned for {category}/{name}")
                return None

            # If response is a list, truncate to self.limit
            if isinstance(response, list):
                response = response[: self.limit]

            # Stabilize the response data before processing
            response = self.field_stabilizer.stabilize(response)

            # Record type mapping for automatic generation
            self.type_mapping_collector.record_type_mapping(response, category, name)

            # Convert to JSON serializable format
            data = to_dict_for_fixture(response)

            # Save fixture data
            fixture_path = GENERATED_FIXTURES_DIR / category / f"{name}.json"
            self.fixture_saver.save_fixture_data(data, fixture_path)

            # Return original response object
            return response

        except ValidationError as e:
            logger.error(f"Validation error for {category}/{name}:")
            detailed_errors = e.errors()
            for error in detailed_errors:
                logger.error(f"  Field: {error.get('loc', 'Unknown')}")
                logger.error(f"  Type: {error.get('type', 'Unknown')}")
                logger.error(f"  Message: {error.get('msg', 'Unknown')}")
                logger.error(f"  Input: {error.get('input', 'Unknown')}")
            logger.error(f"Full validation error: {e}")
            self.failed_fixtures.append(f"{category}/{name}")
            return None
        except Exception as e:
            logger.error(f"Failed to fetch {category}/{name}: {e}")
            self.failed_fixtures.append(f"{category}/{name}")
            return None

    async def run_all_fixtures(self, test_user_session: str) -> None:
        """Run all fixtures generation and post-processing.

        Raises:
            FixtureCollectionError: If any fixture could not be collected.
        """
        try:
            client = NicoNico()

            logger.info("Logging in with user session...")
            client.login_with_session(test_user_session)
            logger.info("Login successful!")

            logger.info("=== Collecting nicovideo fixtures ===")

            api_collector = APIFixtureCollector(self, client, limit=self.limit)
            await api_collector.collect_all_fixtures()

            logger.info("=== Generating fixture types file ===")
            generator = FixtureTypeMappingFileGenerator(
                self.type_mapping_collector.get_all_mappings()
            )
            generator.generate_file(GENERATED_FIXTURE_TYPES_PATH)

            # Show diff summary
            self.fixture_saver.log_summary()

        except LoginFailureError as e:
            logger.error(f"Login failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

        if self.failed_fixtures:
            raise FixtureCollectionError(self.failed_fixtures)

        logger.info("=== All fixtures collected successfully! ===")
