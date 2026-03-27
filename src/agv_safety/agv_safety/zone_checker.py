"""
zone_checker.py

Pure Python utility — no ROS 2 dependencies.
Loads zone definitions from a YAML file and checks
whether a given (x, y) position falls inside any zone.

Fully testable without launching any simulation.
"""

from __future__ import annotations
import yaml
from dataclasses import dataclass, field
from typing import Optional


class ZoneType:
    SAFE       = "SAFE"
    SLOW       = "SLOW"
    STOP       = "STOP"
    RESTRICTED = "RESTRICTED"

    PRIORITY = [SAFE, SLOW, STOP, RESTRICTED]

    @classmethod
    def higher_priority(cls, a: str, b: str) -> str:
        idx_a = cls.PRIORITY.index(a) if a in cls.PRIORITY else 0
        idx_b = cls.PRIORITY.index(b) if b in cls.PRIORITY else 0
        return a if idx_a >= idx_b else b


@dataclass
class SafetyZone:
    name:        str
    zone_type:   str
    speed_limit: float
    description: str
    polygon:     list[list[float]]


@dataclass
class ZoneCheckResult:
    active_zone:  Optional[SafetyZone] = None
    zone_type:    str                  = ZoneType.SAFE
    speed_limit:  float                = 1.0
    inside_zones: list[str]            = field(default_factory=list)


def _point_in_polygon(x: float, y: float, polygon: list[list[float]]) -> bool:
    """Ray-casting algorithm. Returns True if (x, y) is inside the polygon."""
    n = len(polygon)
    inside = False
    px, py = polygon[0]

    for i in range(1, n + 1):
        qx, qy = polygon[i % n]
        if ((py > y) != (qy > y)) and (x < (qx - px) * (y - py) / (qy - py) + px):
            inside = not inside
        px, py = qx, qy

    return inside


class ZoneChecker:
    """
    Loads safety zones from YAML and evaluates AGV position against them.
    Returns the highest-severity zone if multiple zones overlap.
    """

    def __init__(self, zones_yaml_path: str):
        self._zones: list[SafetyZone] = []
        self._load_zones(zones_yaml_path)

    def _load_zones(self, path: str) -> None:
        with open(path, "r") as f:
            config = yaml.safe_load(f)

        for entry in config.get("safety_zones", []):
            zone = SafetyZone(
                name        = entry["name"],
                zone_type   = entry["type"],
                speed_limit = float(entry["speed_limit"]),
                description = entry["description"],
                polygon     = entry["polygon"],
            )
            self._zones.append(zone)

    def check(self, x: float, y: float) -> ZoneCheckResult:
        """
        Check position (x, y) against all zones.
        Returns highest-severity result if inside multiple zones.
        """
        result = ZoneCheckResult()

        for zone in self._zones:
            if _point_in_polygon(x, y, zone.polygon):
                result.inside_zones.append(zone.name)
                if ZoneType.higher_priority(zone.zone_type, result.zone_type) == zone.zone_type:
                    result.active_zone = zone
                    result.zone_type   = zone.zone_type
                    result.speed_limit = zone.speed_limit

        return result

    @property
    def zones(self) -> list[SafetyZone]:
        return self._zones