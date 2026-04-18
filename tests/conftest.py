"""
pytest configuration for integration tests.
"""
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires AWS credentials)"
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-integration"):
        return
    skip_int = pytest.mark.skip(
        reason="Integration tests require --run-integration (uses AWS Bedrock)"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_int)
