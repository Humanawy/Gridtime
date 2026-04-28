# gridtime/_registry.py
from typing import Optional

_GRIDTIME_REGISTRY = {}

def print_structure_tree(cls: type, indent: str = ""):
    """Rekurencyjnie drukuje drzewo struktury jednostek czasu zaczynając od `cls`."""
    unit_key = _GRIDTIME_REGISTRY.get(cls, {}).get("unit_key", cls.__name__)
    print(f"{indent}{cls.__name__} [{unit_key}]")

    child_key = _GRIDTIME_REGISTRY.get(cls, {}).get("children_key")
    if child_key:
        child_classes = [
            child_cls for child_cls, props in _GRIDTIME_REGISTRY.items()
            if props["unit_key"] == child_key
        ]
        for child_cls in child_classes:
            print_structure_tree(child_cls, indent + "  ")

def register_unit(unit_key: str, children_key: Optional[str] = None, step: Optional[str] = None):
    """Dekorator rejestrujący klasę jednostki czasu w `_GRIDTIME_REGISTRY`."""
    def decorator(cls):
        _GRIDTIME_REGISTRY[cls] = {
            "unit_key": unit_key,
            "children_key": children_key,
            "step": step,
        }
        return cls
    return decorator

def _all_unit_keys() -> set[str]:
    """Zwraca zbiór wszystkich zarejestrowanych unit_key-ów."""
    return {props["unit_key"] for props in _GRIDTIME_REGISTRY.values()}

def _is_reachable(cls: type, target_unit: str) -> bool:
    """
    Czy z danej klasy istnieje ścieżka do jednostki `target_unit`
    (włącznie z nią samą)?
    """
    props = _GRIDTIME_REGISTRY.get(cls, {})
    if props.get("unit_key") == target_unit:
        return True

    child_key = props.get("children_key")
    if child_key is None:
        return False

    # wszystkie klasy, które reprezentują dziecko o podanym key‑u
    child_classes = [
        c for c, p in _GRIDTIME_REGISTRY.items()
        if p["unit_key"] == child_key
    ]
    return any(_is_reachable(c, target_unit) for c in child_classes)

def list_registered_units() -> dict[str, str]:
    """Zwraca słownik {nazwa_klasy: unit_key} dla wszystkich zarejestrowanych jednostek."""
    return {cls.__name__: props["unit_key"] for cls, props in _GRIDTIME_REGISTRY.items()}
