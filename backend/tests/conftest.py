import os
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("DATABASE_URL", "postgresql://penflow:penflow_dev_password@localhost:5432/penflow")

from fastapi.testclient import TestClient  #noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def test_client():
    """
    TestsClient instance, to simulate API requests
    """

    with TestClient(app) as client:
        yield client

