from importlib.util import find_spec


def test_initial_dependencies_are_importable() -> None:
    modules = ("bs4", "groq", "dotenv", "pydantic_settings")
    assert all(find_spec(module) is not None for module in modules)
