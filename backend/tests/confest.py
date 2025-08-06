import sys
from unittest.mock import MagicMock
import pytest

@pytest.fixture(autouse=True)
def mock_heavy_ml_imports(monkeypatch):
    """
    This fixture automatically runs before any tests are collected.
    It mocks heavy or problematic ML libraries to allow unit tests
    for other parts of the app (like database logic or basic API endpoints)
    to run in isolation without crashing on import.
    """
    # Create a fake, harmless version of the sentence_transformers library
    mock_sentence_transformers = MagicMock()

    # Tell Python's import system to use our fake module whenever
    # any code tries to 'import sentence_transformers'.
    # This prevents the real library's incompatible torch code from ever running.
    monkeypatch.setitem(sys.modules, "sentence_transformers", mock_sentence_transformers)

    # You can add other problematic imports here as well if needed
    # For example, if 'ragas' was still causing issues:
    # monkeypatch.setitem(sys.modules, "ragas", MagicMock())


    