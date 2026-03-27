"""Quick sanity test — run with: python3 test_zones.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from agv_safety.zone_checker import ZoneChecker

checker = ZoneChecker("config/zones.yaml")

test_points = [
    ( 0.34,  5.725, "Pickup exact position     → expect STOP"),
    (-0.58,  5.625, "Approach point            → expect STOP"),
    ( 0.434, 0.022, "Dropoff exact position    → expect SLOW"),
    ( 0.0,   3.0,   "Mid-aisle free space      → expect SAFE"),
    (-4.2,   3.0,   "Warehouse perimeter       → expect RESTRICTED"),
    ( 0.0,   4.8,   "Corridor entry            → expect SLOW"),
]

print("\n--- Zone Checker Test ---\n")
for x, y, desc in test_points:
    r = checker.check(x, y)
    status = "✓" if r.zone_type != "SAFE" or "SAFE" in desc else "?"
    print(f"  {status}  {desc}")
    print(f"     ({x:.3f}, {y:.3f}) → {r.zone_type:<12} "
          f"speed={r.speed_limit} m/s  "
          f"zones={r.inside_zones or ['none']}\n")