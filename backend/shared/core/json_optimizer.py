"""
JSON Optimizer - Compacts attribute names using simple codes
Removes redundant data and optimizes for token efficiency
"""

import json
import logging
from typing import Dict, Any, List, Union
from dataclasses import asdict, is_dataclass


class JSONOptimizer:
    """
    Compacts attribute names using simple codes
    Removes redundant data
    Optimizes for token efficiency
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.optimization_stats = {
            'original_size': 0,
            'optimized_size': 0,
            'compression_ratio': 0.0
        }
    
    def optimize_board_state(self, board_state: Dict[str, Any], 
                          attribute_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Optimize complete board state for token efficiency
        
        Args:
            board_state: Complete board state data
            attribute_mapping: Mapping from attribute names to codes
            
        Returns:
            Optimized board state with compact representation
        """
        
        try:
            # Calculate original size for stats
            original_json = json.dumps(board_state, separators=(',', ':'))
            self.optimization_stats['original_size'] = len(original_json)
            
            # Create optimized copy
            optimized_state = {}
            
            # Optimize each section
            if 'scene' in board_state:
                optimized_state['scn'] = self._optimize_scene(board_state['scene'])
            
            if 'walls' in board_state:
                optimized_state['wal'] = self._optimize_walls(board_state['walls'])
            
            if 'lighting' in board_state:
                optimized_state['lig'] = self._optimize_lighting(board_state['lighting'])
            
            if 'map_notes' in board_state:
                optimized_state['not'] = self._optimize_map_notes(board_state['map_notes'])
            
            if 'tokens' in board_state:
                optimized_state['tkn'] = self._optimize_tokens(board_state['tokens'], attribute_mapping)
            
            if 'templates' in board_state:
                optimized_state['tpl'] = self._optimize_templates(board_state['templates'])
            
            # Calculate optimized size for stats
            optimized_json = json.dumps(optimized_state, separators=(',', ':'))
            self.optimization_stats['optimized_size'] = len(optimized_json)
            self.optimization_stats['compression_ratio'] = (
                1.0 - (self.optimization_stats['optimized_size'] / self.optimization_stats['original_size'])
            ) if self.optimization_stats['original_size'] > 0 else 0.0
            
            self.logger.info(f"Optimized board state: {self.optimization_stats['original_size']} -> "
                           f"{self.optimization_stats['optimized_size']} bytes "
                           f"({self.optimization_stats['compression_ratio']:.1%} reduction)")
            
            return optimized_state
            
        except Exception as e:
            self.logger.error(f"Error optimizing board state: {e}")
            return board_state
    
    def _optimize_scene(self, scene_data: Any) -> Dict[str, Any]:
        """Optimize scene information with compact field names"""
        
        if hasattr(scene_data, '__dict__'):
            # Dataclass instance - convert to dict
            scene_dict = asdict(scene_data)
        elif isinstance(scene_data, dict):
            scene_dict = scene_data
        else:
            # Handle other types by converting to dict if possible
            try:
                scene_dict = dict(scene_data) if hasattr(scene_data, '__iter__') else scene_data
            except:
                return scene_data
        
        # Map to compact field names
        compact_mapping = {
            'width': 'w',
            'height': 'h',
            'grid_size': 'gs',
            'grid_type': 'gt',
            'background_src': 'bg',
            'scale': 'sc'
        }
        
        optimized = {}
        for key, value in scene_dict.items():
            if value is not None and value != "":
                compact_key = compact_mapping.get(key, key[:2])
                optimized[compact_key] = value
        
        return optimized
    
    def _optimize_walls(self, walls: List[Any]) -> List[Dict[str, Any]]:
        """Optimize wall data with compact field names"""
        
        optimized_walls = []
        
        for wall in walls:
            if hasattr(wall, '__dict__'):
                wall_dict = asdict(wall)
            elif isinstance(wall, dict):
                wall_dict = wall
            else:
                continue
            
            # Map to compact field names
            compact_mapping = {
                'coordinates': 'c',
                'door_type': 'dt',
                'movement_blocking': 'mb',
                'vision_blocking': 'vb',
                'sound_blocking': 'sb'
            }
            
            optimized_wall = {}
            for key, value in wall_dict.items():
                if value is not None and (value is False or value is True or value != ""):
                    compact_key = compact_mapping.get(key, key[:2])
                    optimized_wall[compact_key] = value
            
            optimized_walls.append(optimized_wall)
        
        return optimized_walls
    
    def _optimize_lighting(self, lighting: List[Any]) -> List[Dict[str, Any]]:
        """Optimize lighting data with compact field names"""
        
        optimized_lighting = []
        
        for light in lighting:
            if hasattr(light, '__dict__'):
                light_dict = asdict(light)
            elif isinstance(light, dict):
                light_dict = light
            else:
                continue
            
            # Map to compact field names
            compact_mapping = {
                'x': 'x',
                'y': 'y',
                'radius': 'r',
                'color': 'c',
                'alpha': 'a',
                'angle': 'an',
                'darkness_level': 'dl'
            }
            
            optimized_light = {}
            for key, value in light_dict.items():
                if value is not None and (value is False or value is True or value != ""):
                    compact_key = compact_mapping.get(key, key[:2])
                    optimized_light[compact_key] = value
            
            optimized_lighting.append(optimized_light)
        
        return optimized_lighting
    
    def _optimize_map_notes(self, notes: List[Any]) -> List[Dict[str, Any]]:
        """Optimize map note data with compact field names"""
        
        optimized_notes = []
        
        for note in notes:
            if hasattr(note, '__dict__'):
                note_dict = asdict(note)
            elif isinstance(note, dict):
                note_dict = note
            else:
                continue
            
            # Map to compact field names
            compact_mapping = {
                'x': 'x',
                'y': 'y',
                'text': 't',
                'icon': 'i',
                'icon_size': 'is',
                'global_note': 'g',
                'players_only': 'po'
            }
            
            optimized_note = {}
            for key, value in note_dict.items():
                if value is not None and (value is False or value is True or value != ""):
                    compact_key = compact_mapping.get(key, key[:2])
                    optimized_note[compact_key] = value
            
            optimized_notes.append(optimized_note)
        
        return optimized_notes
    
    def _optimize_tokens(self, tokens: List[Any], attribute_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Optimize token data with compact field names and attribute codes"""
        
        optimized_tokens = []
        
        for token in tokens:
            if hasattr(token, '__dict__'):
                token_dict = asdict(token)
            elif isinstance(token, dict):
                token_dict = token
            else:
                continue
            
            # Map to compact field names
            compact_mapping = {
                'id': 'id',
                'name': 'n',
                'x': 'x',
                'y': 'y',
                'width': 'w',
                'height': 'h',
                'rotation': 'r',
                'actor_id': 'aid',
                'disposition': 'd',
                'hidden': 'hd',
                'vision_enabled': 've',
                'vision_range': 'vr',
                'facing': 'f',
                'attributes': 'at'
            }
            
            optimized_token = {}
            for key, value in token_dict.items():
                if value is None:
                    continue
                    
                if key == 'attributes' and value:
                    # Apply attribute mapping to optimize attribute names
                    optimized_attributes = self._apply_attribute_mapping(value, attribute_mapping)
                    if optimized_attributes:
                        optimized_token[compact_mapping[key]] = optimized_attributes
                elif value is False or value is True or value != "":
                    compact_key = compact_mapping.get(key, key[:2])
                    optimized_token[compact_key] = value
            
            optimized_tokens.append(optimized_token)
        
        return optimized_tokens
    
    def _optimize_templates(self, templates: List[Any]) -> List[Dict[str, Any]]:
        """Optimize template data with compact field names"""
        
        optimized_templates = []
        
        for template in templates:
            if hasattr(template, '__dict__'):
                template_dict = asdict(template)
            elif isinstance(template, dict):
                template_dict = template
            else:
                continue
            
            # Map to compact field names
            compact_mapping = {
                'id': 'id',
                'x': 'x',
                'y': 'y',
                'width': 'w',
                'height': 'h',
                'shape': 's',
                'affected_areas': 'aa'
            }
            
            optimized_template = {}
            for key, value in template_dict.items():
                if value is not None and (value is False or value is True or value != ""):
                    compact_key = compact_mapping.get(key, key[:2])
                    optimized_template[compact_key] = value
            
            optimized_templates.append(optimized_template)
        
        return optimized_templates
    
    def _apply_attribute_mapping(self, attributes: Dict[str, Any], 
                              attribute_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Apply attribute mapping to optimize attribute names"""
        
        if not isinstance(attributes, dict):
            return attributes
        
        optimized_attributes = {}
        
        for attr_name, attr_value in attributes.items():
            if attr_name in attribute_mapping:
                code = attribute_mapping[attr_name]
                optimized_attributes[code] = attr_value
            else:
                # For unmapped attributes, create short code
                code = attr_name[:2] if len(attr_name) >= 2 else attr_name
                optimized_attributes[code] = attr_value
        
        return optimized_attributes
    
    def get_optimization_stats(self) -> Dict[str, Union[int, float]]:
        """Get statistics about the optimization performed"""
        return self.optimization_stats.copy()
    
    def reset_stats(self):
        """Reset optimization statistics"""
        self.optimization_stats = {
            'original_size': 0,
            'optimized_size': 0,
            'compression_ratio': 0.0
        }


# Test the implementation
if __name__ == "__main__":
    from dataclasses import dataclass
    from simple_attribute_mapper import SimpleAttributeMapper
    
    # Create test data
    test_board_state = {
        'scene': {'width': 1000, 'height': 800, 'grid_size': 50, 'grid_type': 'square'},
        'walls': [
            {'coordinates': [[100, 100], [200, 100]], 'movement_blocking': True, 'vision_blocking': True},
            {'coordinates': [[200, 100], [200, 200]], 'door_type': 'door', 'movement_blocking': False}
        ],
        'lighting': [
            {'x': 100, 'y': 100, 'radius': 200, 'color': '#ffaa00', 'alpha': 0.3}
        ],
        'tokens': [
            {
                'id': 'token1',
                'name': 'Fighter',
                'x': 100,
                'y': 100,
                'attributes': {
                    'health': 45,
                    'armor_class': 16,
                    'speed': 30,
                    'strength': 18,
                    'dexterity': 14
                }
            }
        ]
    }
    
    # Create attribute mapping
    test_attributes = {'health': 45, 'armor_class': 16, 'speed': 30, 'strength': 18, 'dexterity': 14}
    mapper = SimpleAttributeMapper()
    code_mapping, _ = mapper.map_attributes(test_attributes)
    
    print("Attribute Mapping:", code_mapping)
    
    # Optimize the board state
    optimizer = JSONOptimizer()
    optimized_state = optimizer.optimize_board_state(test_board_state, code_mapping)
    
    print("\nOptimized Board State:")
    print(json.dumps(optimized_state, indent=2))
    
    print("\nOptimization Stats:")
    stats = optimizer.get_optimization_stats()
    print(f"Original Size: {stats['original_size']} bytes")
    print(f"Optimized Size: {stats['optimized_size']} bytes")
    print(f"Compression: {stats['compression_ratio']:.1%}")
