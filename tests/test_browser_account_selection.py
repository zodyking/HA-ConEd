import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


SERVICE_DIR = Path(__file__).parents[1] / "coned_scraper" / "python-service"
sys.path.insert(0, str(SERVICE_DIR))

playwright_module = ModuleType("playwright")
playwright_async_module = ModuleType("playwright.async_api")
playwright_async_module.async_playwright = None
playwright_async_module.TimeoutError = TimeoutError
sys.modules.setdefault("playwright", playwright_module)
sys.modules.setdefault("playwright.async_api", playwright_async_module)
sys.modules.setdefault("db", SimpleNamespace())

from browser_automation import _address_match_score  # noqa: E402


def test_address_matching_prefers_the_configured_unit():
    desired = "TEST SERVICE LOCATION ALPHA UNIT A"
    correct = "TEST SERVICE LOCATION ALPHA A"
    wrong = "TEST SERVICE LOCATION ALPHA B"

    assert _address_match_score(desired, correct) > _address_match_score(
        desired, wrong
    )
