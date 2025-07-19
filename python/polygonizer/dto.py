from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

    
@dataclass(slots=True)
class Point:
    x: float
    y: float
   
    def eq_to(self, other: Point, tol: float) -> bool:
        return abs(self.x - other.x) < tol and abs(self.y - other.y) < tol
    
@dataclass(slots=True)
class ClosedPolygon:
    points: List[Point]
    handles: List[str]
    
@dataclass(slots=True)
class PolygonPart:
    points: List[Point]
    handles: List[str]
    
    def is_valid(self) -> bool:
        return len(self.points) >= 2 
    
    def is_closed(self, tol: float) -> bool:
        return self.is_valid() and self.points[0].eq_to(self.points[-1], tol)
    
    def to_closed_polygon(self) -> ClosedPolygon:
        return ClosedPolygon(points=self.points, handles=self.handles)
