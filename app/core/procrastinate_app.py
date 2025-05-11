# This is a dummy file to resolve import errors in the test environment.
# It provides a mock for the Procrastinate App instance and a getter function.

from unittest.mock import MagicMock

# Dummy Procrastinate App instance to satisfy imports
procrastinate_app = MagicMock()


# Dummy getter function to satisfy imports
def get_procrastinate_app():
    """
    Dummy getter for the Procrastinate App instance for tests.
    """
    return procrastinate_app
