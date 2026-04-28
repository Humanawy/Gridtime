# gridtime/_base.py
from abc import ABC, abstractmethod
from typing import List, Iterator
from collections.abc import Sequence
from gridtime._registry import _GRIDTIME_REGISTRY, _all_unit_keys, _is_reachable


class GridtimeLeaf(ABC):
    def _structure_name(self) -> str:
        return self.__class__.__name__

    def unit_key(self) -> str:
        return _GRIDTIME_REGISTRY[self.__class__]["unit_key"]

    @abstractmethod
    def __repr__(self) -> str:
        pass

    def shift(self, steps: int = 1) -> "GridtimeLeaf":
        info = _GRIDTIME_REGISTRY[self.__class__]
        if "step" not in info:
            raise NotImplementedError(f"Brak klucza 'step' dla {self.__class__.__name__}")
        return info["step"](self, steps)

    def next(self): return self.shift(+1)
    def prev(self): return self.shift(-1)
    def __next__(self): return self.next()

    def _iter_children(self) -> Iterator["GridtimeLeaf"]:
        return iter(())

    def children_key(self) -> str | None:
        return _GRIDTIME_REGISTRY[self.__class__].get("children_key")

    def _validate_unit(self, unit: str) -> None:
        if unit not in _all_unit_keys():
            raise ValueError(
                f"Nieznana jednostka '{unit}'. Dostępne: {sorted(_all_unit_keys())}"
            )
        if not _is_reachable(self.__class__, unit):
            raise ValueError(
                f"Jednostka '{unit}' nie występuje w gałęzi drzewa z korzeniem "
                f"{self._structure_name()} ('{self.unit_key()}')."
            )

    def __iter__(self) -> Iterator["GridtimeLeaf"]:
        return self._iter_children()

    def __len__(self) -> int:
        return sum(1 for _ in self._iter_children())

    def __contains__(self, other: object) -> bool:
        if not isinstance(other, GridtimeLeaf):
            return False
        return any(node == other for node in self.walk(other.unit_key()))

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, self.__class__)
            and getattr(self, "start_time", None) == getattr(other, "start_time", None)
            and getattr(self, "end_time", None)   == getattr(other, "end_time", None)
        )

    def __hash__(self) -> int:
        return hash((self.__class__, getattr(self, "start_time", None), getattr(self, "end_time", None)))

    def count(self, unit: str) -> int:
        self._validate_unit(unit)
        if self.unit_key() == unit:
            return 1
        if self.children_key() is None:
            return 0
        return sum(child.count(unit) for child in self._iter_children())

    def get(self, unit: str) -> List["GridtimeLeaf"]:
        self._validate_unit(unit)
        if self.unit_key() == unit:
            return [self]
        if self.children_key() is None:
            return []
        out: List["GridtimeLeaf"] = []
        for child in self._iter_children():
            out.extend(child.get(unit))
        return out

    def walk(self, unit: str) -> Iterator["GridtimeLeaf"]:
        self._validate_unit(unit)
        if self.unit_key() == unit:
            yield self
        elif self.children_key() is not None:
            for child in self._iter_children():
                yield from child.walk(unit)

    def tree(
        self,
        unit_stop: str | None = None,
        show_root: bool = True,
        _prefix: str = "",
        _is_last: bool = True,
    ) -> str:
        lines: list[str] = []
        if show_root:
            connector = "└── " if _is_last else "├── "
            lines.append(f"{_prefix}{connector}{repr(self)}")
            _prefix += "    " if _is_last else "│   "

        if (unit_stop is not None and self.unit_key() == unit_stop) \
           or self.children_key() is None:
            return "\n".join(lines)

        children = list(self._iter_children())
        for idx, child in enumerate(children):
            is_last = idx == len(children) - 1
            lines.append(child.tree(unit_stop, True, _prefix, is_last))
        return "\n".join(lines)


    def print_tree(self, **kwargs):
        print(self.tree(**kwargs))

class GridtimeStructure(GridtimeLeaf):
    def __init__(self):
        self._children: Sequence[GridtimeLeaf] | None = None

    @abstractmethod
    def _create_children(self) -> list[GridtimeLeaf]:
        ...

    def _iter_children(self) -> Iterator[GridtimeLeaf]:
        if self._children is None:
            self._children = self._create_children()
        return iter(self._children)
