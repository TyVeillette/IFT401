import os

# config.py reads DATABASE_URL once, when it is first imported.
# Set the test database here, before any test module imports the app,
# so tests can never run against the database in .env.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key"
