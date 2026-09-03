import pytest

def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true", help="run integration tests")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--integration"):
        # --integration given in CLI: do not skip integration tests
        return
    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
