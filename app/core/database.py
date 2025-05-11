# This is a dummy file to resolve import errors in the test environment.
# The actual database logic is in app.core.database_mongo.py
from .database_mongo import *


# Dummy function to satisfy imports in the test environment
def get_db_session():
    """
    Dummy database session dependency placeholder for tests.
    """
    raise NotImplementedError("get_db_session is a placeholder and should not be called in these tests.")
