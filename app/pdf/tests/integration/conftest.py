# conftest.py for app/pdf/tests/integration
# This file is intentionally left mostly empty for now.
# Its presence helps pytest discover plugins and fixtures in this directory.

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
