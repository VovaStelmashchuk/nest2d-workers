import pytest
from polygonizer.core import combine_polygon_parts
from polygonizer.dto import PolygonPart, Point, ClosedPolygon


class TestCombinePolygonParts:
    """Test cases for combine_polygon_parts function"""
    
    def test_empty_inputs_raises_error(self):
        """Test that empty open and closed parts raises ValueError"""
        with pytest.raises(ValueError, match="Open and closed parts are empty"):
            combine_polygon_parts([], [], 0.1)
    
    def test_only_closed_parts_returns_unchanged(self):
        """Test that when only closed parts are provided, they are returned unchanged"""
        closed_part1 = ClosedPolygon(
            points=[Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1), Point(0, 0)],
            handles=["handle1"]
        )
        closed_part2 = ClosedPolygon(
            points=[Point(2, 2), Point(3, 2), Point(3, 3), Point(2, 3), Point(2, 2)],
            handles=["handle2"]
        )
        
        open, close = combine_polygon_parts([], [closed_part1, closed_part2], 0.1)
        
        assert len(open) == 0
        assert len(close) == 2
        assert close[0] == closed_part1
        assert close[1] == closed_part2

    def test_two_close_polygone_one_inside_other(self): 
        parent_close_polygon = ClosedPolygon(
            points=[Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1), Point(0, 0)],
            handles=["parent_handle"]
        )
        closed_part2 = ClosedPolygon(
            points=[Point(0.5, 0.5), Point(1.5, 0.5), Point(1.5, 1.5), Point(0.5, 1.5), Point(0.5, 0.5)],
            handles=["child_handle"]
        )
        
        open, close = combine_polygon_parts([], [parent_close_polygon, closed_part2], 0.1)
        
        assert len(open) == 0
        assert len(close) == 1
        assert close[0] == parent_close_polygon
        
if __name__ == "__main__":
    pytest.main([__file__]) 