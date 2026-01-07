#!/usr/bin/env python3
"""
Scene Spatial Filter Service for The Gold Box
Provides spatial awareness for AI to query scene objects within a radius

License: CC-BY-NC-SA 4.0
"""

import logging
import re
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DistanceUnit:
    """Represents a distance unit configuration"""
    unit: str  # 'feet', 'meters', 'squares'
    value: Optional[float]  # Number of grid units per unit (None for squares)


def parse_distance_unit(setting: str) -> DistanceUnit:
    """
    Parse plain language distance unit setting
    
    Args:
        setting: Plain language setting like "5 feet", "2 meters", "squares"
        
    Returns:
        DistanceUnit object with parsed unit and value
    """
    if not setting:
        return DistanceUnit(unit='squares', value=None)
    
    # Extract number and unit from plain language
    match = re.match(r'(\d+(?:\.\d+)?)\s*(feet|ft|meters|m|squares)?', setting.lower())
    
    if not match:
        return DistanceUnit(unit='squares', value=None)
    
    value = float(match.group(1))
    unit = match.group(2) or 'squares'
    
    # Normalize unit names
    unit_map = {
        'feet': 'feet',
        'ft': 'feet',
        'meters': 'meters',
        'm': 'meters'
    }
    
    return DistanceUnit(
        unit=unit_map.get(unit, 'squares'),
        value=value if unit_map.get(unit, 'squares') != 'squares' else None
    )


class SceneSpatialFilter:
    """
    Service for filtering scene objects by spatial criteria
    
    Provides:
    - Radius-based filtering (Euclidean distance)
    - Line-of-sight filtering (wall blocking)
    - Distance unit conversion (feet, meters, squares)
    - Distance matrix for nearest tokens
    - Hierarchical object grouping
    """
    
    def __init__(self, grid_size: float, distance_unit_setting: str, max_nearest_tokens: int = 5):
        """
        Initialize scene spatial filter
        
        Args:
            grid_size: Foundry grid size (units per square)
            distance_unit_setting: Plain language distance setting (e.g., "5 feet")
            max_nearest_tokens: Maximum tokens to include in distance matrix
        """
        logger.info(f"SceneSpatialFilter init - grid_size type: {type(grid_size)}, value: {grid_size}")
        logger.info(f"SceneSpatialFilter init - distance_unit_setting type: {type(distance_unit_setting)}, value: {distance_unit_setting}")
        
        self.grid_size = grid_size
        self.distance_unit = parse_distance_unit(distance_unit_setting)
        self.max_nearest_tokens = max_nearest_tokens
        
        logger.info(f"SceneSpatialFilter initialized: grid_size={grid_size}, "
                   f"distance_unit={distance_unit_setting}, max_nearest_tokens={max_nearest_tokens}")
    
    def get_nearby_objects(self, scene_data: Dict[str, Any], origin: Any, 
                         radius: float, search_mode: str = "line_of_sight") -> Dict[str, Any]:
        """
        Get scene objects within a radius of a location or token
        
        Args:
            scene_data: Full scene data from frontend
            origin: Search origin (coordinates {x, y} or token_id string)
            radius: Search radius in grid units
            search_mode: "absolute" (all objects) or "line_of_sight" (visible only)
            
        Returns:
            Hierarchical object structure with nearby_scene_objects and distance_matrix
        """
        logger.info(f"get_nearby_objects called")
        logger.debug(f"scene_data type: {type(scene_data)}, origin type: {type(origin)}, radius: {radius}, search_mode: {search_mode}")
        
        # Validate scene_data is a dict
        if not isinstance(scene_data, dict):
            logger.error(f"scene_data is not a dict: type={type(scene_data)}, value={scene_data}")
            raise TypeError(f"scene_data must be a dict, got {type(scene_data).__name__}")
        
        # Parse origin (coordinates or token center)
        logger.debug(f"Parsing origin from tokens")
        origin_coords = self._parse_origin(origin, scene_data.get('tokens', []))
        logger.debug(f"Origin coordinates: {origin_coords}")
        
        # Filter objects by radius (Euclidean distance)
        in_radius = self._filter_by_radius(scene_data, origin_coords, radius)
        
        # If line-of-sight mode: filter by visibility
        if search_mode == "line_of_sight":
            visible = self._filter_by_los(origin_coords, in_radius, scene_data.get('walls', []))
        else:
            visible = in_radius
        
        # Sort by distance and format output
        sorted_objects = self._sort_and_format(origin_coords, visible)
        
        # Structure output hierarchically - pass origin_coords (always a dict) instead of origin (can be string)
        return self._structure_output(sorted_objects, origin_coords, radius, search_mode)
    
    def _parse_origin(self, origin: Any, tokens: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Parse origin from token_id or coordinates
        
        Args:
            origin: Token ID string or coordinates dict {x, y}
            tokens: List of tokens from scene data
            
        Returns:
            Coordinates dict {x, y}
            
        Raises:
            ValueError: If token_id not found
        """
        if isinstance(origin, str):  # token_id
            logger.debug(f"Parsing origin from token_id: {origin}")
            logger.debug(f"Available tokens: {[t.get('id') for t in tokens]}")
            token = next((t for t in tokens if t.get('id') == origin), None)
            if token:
                logger.debug(f"Found token: {token.get('name')} at ({token.get('x')}, {token.get('y')})")
                return {"x": token.get('x', 0), "y": token.get('y', 0)}
            logger.error(f"Token {origin} not found in {len(tokens)} tokens")
            raise ValueError(f"Token {origin} not found")
        else:  # coordinates
            return {"x": origin['x'], "y": origin['y']}
    
    def _filter_by_radius(self, scene_data: Dict[str, Any], origin: Dict[str, float], 
                         radius: float) -> List[Dict[str, Any]]:
        """
        Filter all scene objects by Euclidean distance from origin
        
        Args:
            scene_data: Full scene data
            origin: Origin coordinates {x, y}
            radius: Search radius in grid units
            
        Returns:
            List of objects within radius with distances
        """
        objects = []
        
        # Collect all objects (walls, doors, notes, lights, tokens)
        if 'walls' in scene_data:
            logger.debug(f"Processing walls: type={type(scene_data['walls'])}, count={len(scene_data['walls']) if isinstance(scene_data['walls'], (list, dict)) else 'N/A'}")
            if scene_data['walls'] and len(scene_data['walls']) > 0:
                logger.debug(f"First wall sample: {scene_data['walls'][0]}")
            objects.extend([{
                'type': 'wall',
                'id': w['id'],
                'coordinates': self._get_wall_center(w.get('c', [0, 0, 0, 0]))
            } for w in scene_data['walls']])
        
        if 'doors' in scene_data:
            objects.extend([{
                'type': 'door',
                'id': d['id'],
                'door': d.get('door'),
                'state': d.get('state', 'unknown'),
                'locked': d.get('locked', False),
                'blocks_vision': d.get('blocks_vision', False),
                'coordinates': self._get_door_center(d.get('c', [0, 0, 0, 0]))
            } for d in scene_data['doors']])
        
        if 'notes' in scene_data:
            objects.extend([{
                'type': 'journal_note',
                'id': n['id'],
                'entry_name': n.get('entry_name', 'Unknown'),
                'journal_entry_title': n.get('journal_entry_title', 'Unknown'),
                'note_type': n.get('note_type', 'location'),
                'coordinates': {'x': n['x'], 'y': n['y']}
            } for n in scene_data['notes']])
        
        if 'lights' in scene_data:
            objects.extend([{
                'type': 'token_light',
                'id': l['id'],
                'source_token': l.get('source_token', 'Unknown'),
                'radius': l.get('radius', 0),
                'color': l.get('color', '#ffffff'),
                'brightness': l.get('brightness', 'unknown'),
                'coordinates': {'x': l['x'], 'y': l['y']}
            } for l in scene_data['lights']])
        
        if 'tokens' in scene_data:
            objects.extend([{
                'type': 'token',
                'id': t['id'],
                'name': t['name'],
                'is_player': t.get('is_player', False),
                'coordinates': {'x': t['x'], 'y': t['y']}
            } for t in scene_data['tokens']])
        
        # Filter by Euclidean distance
        filtered = []
        for obj in objects:
            dist = self._euclidean_distance(origin, obj['coordinates'])
            if dist <= radius:
                obj['distance'] = dist
                filtered.append(obj)
        
        logger.debug(f"Filtered {len(filtered)}/{len(objects)} objects within radius {radius}")
        return filtered
    
    def _filter_by_los(self, origin: Dict[str, float], objects: List[Dict[str, Any]], 
                      walls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter objects by line-of-sight (respecting vision-blocking walls)
        
        Args:
            origin: Origin coordinates {x, y}
            objects: List of objects to filter
            walls: List of walls from scene data
            
        Returns:
            List of visible objects
        """
        visible = []
        for obj in objects:
            if self._check_line_of_sight(origin, obj['coordinates'], walls):
                visible.append(obj)
        
        logger.debug(f"Line-of-sight: {len(visible)}/{len(objects)} objects visible")
        return visible
    
    def _check_line_of_sight(self, origin: Dict[str, float], target: Dict[str, float], 
                            walls: List[Dict[str, Any]]) -> bool:
        """
        Check if line of sight exists from origin to target
        
        Args:
            origin: Origin coordinates {x, y}
            target: Target coordinates {x, y}
            walls: List of walls to check
            
        Returns:
            True if line of sight exists (no blocking walls)
        """
        logger.debug(f"_check_line_of_sight called with {len(walls)} walls")
        for wall in walls:
            logger.debug(f"Checking wall {wall.get('id', 'unknown')}, blocks_vision: {wall.get('blocks_vision', False)}")
            if wall.get('blocks_vision', False):
                # Walls have 'c' array [x1, y1, x2, y2], not 'coordinates' object
                c = wall.get('c', [0, 0, 0, 0])
                
                logger.debug(f"Wall 'c' value: {c}, type: {type(c)}")
                
                # Validate that c is a list before accessing indices
                if not isinstance(c, list) and not isinstance(c, tuple):
                    logger.warning(f"Invalid wall data: 'c' is {type(c).__name__}, expected list/tuple. Wall: {wall.get('id', 'unknown')}")
                    continue  # Skip this wall
                
                if len(c) < 4:
                    logger.warning(f"Invalid wall data: 'c' has {len(c)} elements, expected 4. Wall: {wall.get('id', 'unknown')}")
                    continue  # Skip this wall
                
                try:
                    wall_coords = {
                        'start': {'x': c[0], 'y': c[1]},
                        'end': {'x': c[2], 'y': c[3]}
                    }
                    logger.debug(f"Wall coordinates: {wall_coords}")
                    if self._ray_intersects_line(origin, target, wall_coords):
                        return False  # Blocked by wall
                except (TypeError, IndexError, KeyError) as e:
                    logger.error(f"Error processing wall {wall.get('id', 'unknown')}: {e}")
                    logger.debug(f"Wall data: c={c}, type={type(c)}, origin={origin}, target={target}")
                    continue  # Skip this wall
        
        return True  # No blocking walls found
    
    def _ray_intersects_line(self, origin: Dict[str, float], target: Dict[str, float], 
                            wall_coords: Dict[str, Any]) -> bool:
        """
        Check if ray from origin to target intersects wall line segment
        
        Args:
            origin: Origin coordinates {x, y}
            target: Target coordinates {x, y}
            wall_coords: Wall coordinates with 'start' and 'end' points
            
        Returns:
            True if ray intersects wall
        """
        ox, oy = origin['x'], origin['y']
        tx, ty = target['x'], target['y']
        
        # Get wall coordinates
        wall_start = wall_coords.get('start', {'x': 0, 'y': 0})
        wall_end = wall_coords.get('end', {'x': 0, 'y': 0})
        wx1, wy1 = wall_start['x'], wall_start['y']
        wx2, wy2 = wall_end['x'], wall_end['y']
        
        # Denominator for line-line intersection
        denom = (ox - tx) * (wy1 - wy2) - (oy - ty) * (wx1 - wx2)
        if denom == 0:
            return False  # Parallel lines
        
        # Check intersection
        ua = ((wx1 - wx2) * (oy - wy1) - (wy1 - wy2) * (ox - wx1)) / denom
        ub = ((wx1 - wx2) * (oy - wy1) - (wy1 - wy2) * (ox - wx1)) / denom
        
        if 0 <= ua <= 1 and 0 <= ub <= 1:
            return True  # Lines intersect
        return False
    
    def _euclidean_distance(self, p1: Dict[str, float], p2: Dict[str, float]) -> float:
        """
        Calculate Euclidean distance between two points
        
        Args:
            p1: First point {x, y}
            p2: Second point {x, y}
            
        Returns:
            Euclidean distance
        """
        return math.sqrt((p2['x'] - p1['x'])**2 + (p2['y'] - p1['y'])**2)
    
    def _get_wall_center(self, wall_coords: List[float]) -> Dict[str, float]:
        """Calculate center point of wall line segment"""
        logger.debug(f"_get_wall_center called with wall_coords: {wall_coords}, type: {type(wall_coords)}")
        
        # Validate input type
        if not isinstance(wall_coords, (list, tuple)):
            logger.warning(f"Invalid wall_coords type: {type(wall_coords).__name__}, expected list/tuple")
            return {'x': 0, 'y': 0}
        
        if len(wall_coords) >= 4:
            try:
                return {
                    'x': (float(wall_coords[0]) + float(wall_coords[2])) / 2,
                    'y': (float(wall_coords[1]) + float(wall_coords[3])) / 2
                }
            except (TypeError, ValueError, IndexError) as e:
                logger.error(f"Error calculating wall center: {e}, wall_coords={wall_coords}")
                return {'x': 0, 'y': 0}
        
        logger.warning(f"wall_coords has insufficient length: {len(wall_coords)}, expected >= 4")
        return {'x': 0, 'y': 0}
    
    def _get_door_center(self, door_coords: List[float]) -> Dict[str, float]:
        """Calculate center point of door line segment"""
        logger.debug(f"_get_door_center called with door_coords: {door_coords}, type: {type(door_coords)}")
        
        # Validate input type
        if not isinstance(door_coords, (list, tuple)):
            logger.warning(f"Invalid door_coords type: {type(door_coords).__name__}, expected list/tuple")
            return {'x': 0, 'y': 0}
        
        if len(door_coords) >= 4:
            try:
                return {
                    'x': (float(door_coords[0]) + float(door_coords[2])) / 2,
                    'y': (float(door_coords[1]) + float(door_coords[3])) / 2
                }
            except (TypeError, ValueError, IndexError) as e:
                logger.error(f"Error calculating door center: {e}, door_coords={door_coords}")
                return {'x': 0, 'y': 0}
        
        logger.warning(f"door_coords has insufficient length: {len(door_coords)}, expected >= 4")
        return {'x': 0, 'y': 0}
    
    def _sort_and_format(self, origin: Dict[str, float], objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort objects by distance and format distances
        
        Args:
            origin: Origin coordinates {x, y}
            objects: List of objects to sort
            
        Returns:
            Sorted list with formatted distances
        """
        # Sort by distance
        objects.sort(key=lambda o: o['distance'])
        
        # Format distances for each object
        for obj in objects:
            grid_squares = obj['distance'] / self.grid_size
            obj['formatted_distance'] = self._format_distance(grid_squares, self.distance_unit)
        
        return objects
    
    def _format_distance(self, grid_squares: float, distance_unit: DistanceUnit) -> str:
        """
        Format distance in user's preferred units
        
        Args:
            grid_squares: Distance in grid squares
            distance_unit: DistanceUnit configuration
            
        Returns:
            Formatted distance string
        """
        if distance_unit.unit == 'squares' or distance_unit.value is None:
            return f"{round(grid_squares, 1)} squares"
        
        # Calculate in user's units
        user_units = grid_squares * distance_unit.value
        return f"{round(user_units, 1)} {distance_unit.unit}"
    
    def _structure_output(self, objects: List[Dict[str, Any]], origin: Any, 
                       radius: float, search_mode: str) -> Dict[str, Any]:
        """
        Structure output hierarchically by object type
        
        Args:
            objects: Sorted list of objects
            origin: Original origin (token_id or coordinates)
            radius: Search radius used
            search_mode: Search mode used
            
        Returns:
            Hierarchical output structure
        """
        # Group objects by type
        grouped = {
            'tokens': [o for o in objects if o.get('type') == 'token'],
            'structures': [o for o in objects if o.get('type') in ['wall', 'door']],
            'locations_of_interest': [o for o in objects if o.get('type') == 'journal_note'],
            'lighting': [o for o in objects if o.get('type') == 'token_light']
        }
        
        # Generate distance matrix for tokens
        tokens = [o for o in objects if o.get('type') == 'token']
        distance_matrix = self._generate_distance_matrix(origin, tokens)
        
        return {
            'nearby_scene_objects': {
                'origin': {
                    'coordinates': origin if isinstance(origin, dict) else {'x': 0, 'y': 0},
                    'distance_unit': self.distance_unit.unit,
                    'description': 'Search center point'
                },
                'search_radius': radius,
                'search_mode': search_mode,
                'total_objects_found': len(objects),
                'visible_objects_count': len(objects),
                'tokens': {
                    'count': len(grouped['tokens']),
                    'items': self._format_tokens(grouped['tokens'], origin)
                },
                'structures': {
                    'count': len(grouped['structures']),
                    'items': self._format_structures(grouped['structures'])
                },
                'locations_of_interest': {
                    'count': len(grouped['locations_of_interest']),
                    'items': self._format_locations(grouped['locations_of_interest'])
                },
                'lighting': {
                    'count': len(grouped['lighting']),
                    'items': self._format_lighting(grouped['lighting'])
                }
            },
            'distance_matrix': distance_matrix
        }
    
    def _generate_distance_matrix(self, origin: Any, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate pairwise distance matrix for nearest N tokens
        
        Args:
            origin: Origin point
            tokens: List of token objects
            
        Returns:
            Distance matrix with pairwise distances
        """
        if not tokens:
            return {
                'origin_token_id': origin if isinstance(origin, str) else None,
                'nearest_objects': [],
                'pairwise_distances': {},
                'total_tokens_in_scene': 0
            }
        
        # Get origin coordinates for distance calculations
        origin_coords = {'x': 0, 'y': 0}
        if isinstance(origin, dict):
            origin_coords = origin
        elif isinstance(origin, str) and tokens:
            # Find origin token if origin is a token_id
            origin_token = next((t for t in tokens if t['id'] == origin), None)
            if origin_token:
                origin_coords = origin_token['coordinates']
        
        # Calculate distances from origin to each token
        token_distances = []
        for token in tokens:
            dist = self._euclidean_distance(origin_coords, token['coordinates'])
            token_distances.append({
                'token_id': token['id'],
                'name': token['name'],
                'distance': dist
            })
        
        # Sort by distance
        token_distances.sort(key=lambda t: t['distance'])
        
        # Get nearest N (configurable)
        nearest = token_distances[:self.max_nearest_tokens]
        
        # Generate pairwise distances between nearest N
        pairwise = {}
        for i, token1 in enumerate(nearest):
            distances = {}
            for j, token2 in enumerate(nearest):
                if i == j:
                    continue  # Skip self
                dist = self._euclidean_distance(
                    token1['coordinates'],
                    token2['coordinates']
                )
                grid_dist = dist / self.grid_size
                formatted = self._format_distance(grid_dist, self.distance_unit)
                distances[token2['name']] = formatted
            pairwise[token1['name']] = distances
        
        return {
            'origin_token_id': origin if isinstance(origin, str) else None,
            'nearest_objects': nearest,
            'pairwise_distances': pairwise,
            'total_tokens_in_scene': len(tokens)
        }
    
    def _format_tokens(self, tokens: List[Dict[str, Any]], origin: Dict[str, float]) -> List[Dict[str, Any]]:
        """Format token objects for output"""
        return [
            {
                'id': t.get('id'),
                'name': t.get('name'),
                'distance': t.get('formatted_distance'),
                'bearing': self._calculate_bearing(origin, t['coordinates']),
                'is_visible': True,  # Already filtered by LoS
                'coordinates': t['coordinates']
            }
            for t in tokens
        ]
    
    def _format_structures(self, structures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format structure objects (walls, doors) for output"""
        items = []
        for s in structures:
            if s['type'] == 'wall':
                items.append({
                    'type': 'wall',
                    'id': s.get('id'),
                    'distance': s.get('formatted_distance'),
                    'blocks_vision': s.get('blocks_vision', False),
                    'coordinates': s['coordinates']
                })
            elif s['type'] == 'door':
                items.append({
                    'type': 'door',
                    'id': s.get('id'),
                    'distance': s.get('formatted_distance'),
                    'state': s.get('state', 'unknown'),
                    'locked': s.get('locked', False),
                    'blocks_vision': s.get('blocks_vision', False),
                    'coordinates': s['coordinates']
                })
        return items
    
    def _format_locations(self, locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format journal note objects for output"""
        return [
            {
                'type': 'journal_note',
                'id': l.get('id'),
                'distance': l.get('formatted_distance'),
                'entry_name': l.get('entry_name'),
                'journal_entry_title': l.get('journal_entry_title'),
                'note_type': l.get('note_type'),
                'coordinates': l['coordinates']
            }
            for l in locations
        ]
    
    def _format_lighting(self, lights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format light source objects for output"""
        return [
            {
                'type': 'token_light',
                'source_token': l.get('source_token'),
                'distance': l.get('formatted_distance'),
                'radius': l.get('radius'),
                'color': l.get('color'),
                'brightness': l.get('brightness', 'unknown')
            }
            for l in lights
        ]
    
    def _calculate_bearing(self, origin: Dict[str, float], target: Dict[str, float]) -> str:
        """
        Calculate compass direction from origin to target
        
        Args:
            origin: Origin coordinates {x, y}
            target: Target coordinates {x, y}
            
        Returns:
            Compass direction (e.g., 'east', 'southeast', etc.)
        """
        dx = target['x'] - origin['x']
        dy = target['y'] - origin['y']
        angle = math.atan2(dy, dx) * 180 / math.pi  # Degrees
        
        # Normalize to 0-360
        if angle < 0:
            angle += 360
        
        # Map to compass directions
        directions = ['east', 'southeast', 'south', 'southwest', 'west', 'northwest', 'north', 'northeast']
        index = round(angle / 45) % 8
        return directions[index]
