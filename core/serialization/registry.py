from dataclasses import dataclass
from typing import Callable


Version = tuple[int, int, int]
Availability = Callable[[Version], bool]


@dataclass(frozen=True)
class StgSpec:
    name: str
    factory: type
    roles: tuple[str, ...]
    available: Availability = lambda _version: True


class StrategySet:
    def __init__(self, blender_version: Version):
        self.blender_version = blender_version


class StgRegistry:
    def __init__(self, specs: tuple[StgSpec, ...], required_roles: tuple[str, ...]):
        self.specs = specs
        self.required_roles = required_roles

    def build(self, blender_version: list[int] | tuple[int, int, int]) -> StrategySet:
        version = tuple(blender_version)
        strategies = StrategySet(version)
        role_members = {role: [] for role in self.required_roles}
        names = set()

        for spec in self.specs:
            if spec.name in names:
                raise ValueError(f"Duplicate STG name: {spec.name}")
            names.add(spec.name)
            if not spec.available(version):
                continue

            strategy = spec.factory()
            setattr(strategies, spec.name, strategy)
            for role in spec.roles:
                if role not in role_members:
                    raise ValueError(f"Unknown STG role '{role}' for {spec.name}")
                role_members[role].append(strategy)

        for role, members in role_members.items():
            if not members:
                raise ValueError(f"STG role '{role}' is empty")
            fallback = getattr(strategies, "fallback", None)
            if fallback in members and members[-1] is not fallback:
                raise ValueError(f"Fallback STG must be last in role '{role}'")
            setattr(strategies, f"stg_list_{role}", members)

        return strategies
