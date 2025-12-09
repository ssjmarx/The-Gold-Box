"""
Board State Collector - Gathers complete scene information
System-agnostic collection of all board elements
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class SceneInfo:
    """Basic scene information"""
    width: float
    height: float
    grid_size: float
    grid_type: str
    background_src: Optional[str] = None
    scale: Optional[float] = None


@dataclass
class WallData:
    """Wall and door information"""
    coordinates: List[tuple]  # x,y coordinates
    door_type: Optional[str] = None
    movement_blocking: bool = False
    vision_blocking: bool = False
    sound_blocking: bool = False


@dataclass
class LightingData:
    """Light source and vision information"""
    x: float
    y: float
    radius: float
    color: Optional[str] = None
    alpha: Optional[float] = None
    angle: Optional[float] = None
    darkness_level: Optional[float] = None


@dataclass
class MapNote:
    """Map note information"""
    x: float
    y: float
    text: str
    icon: Optional[str] = None
    icon_size: Optional[int] = None
    global_note: bool = False
    players_only: bool = False


@dataclass
class TokenData:
    """Complete token information"""
    id: str
    name: str
    x: float
    y: float
    width: float
    height: float
    rotation: float
    actor_id: Optional[str] = None
    disposition: Optional[int] = None
    hidden: bool = False
    vision_enabled: bool = False
    vision_range: Optional[float] = None
    facing: Optional[float] = None
    attributes: Dict[str, Any] = None  # Will be populated with system-agnostic attributes


@dataclass
class TemplateData:
    """Area template information"""
    id: str
    x: float
    y: float
    width: float
    height: float
    shape: str  # circle, square, cone, etc.
    affected_areas: List[tuple] = None  # Grid coordinates affected


class BoardStateCollector:
    """
    Gathers complete scene information
    Collects all tokens with positions/sizes/vision/facing
    Extracts walls, doors, lighting data
    Retrieves map notes and templates
    """
    
    def __init__(self, foundry_client):
        self.foundry_client = foundry_client
        self.logger = logging.getLogger(__name__)
    
    async def collect_complete_board_state(self, scene_id: str) -> Dict[str, Any]:
        """
        Collect all board state information for a scene
        
        Args:
            scene_id: Foundry scene ID
            
        Returns:
            Dictionary containing all board elements
        """
        
        try:
            board_state = {
                'scene': asdict(await self._collect_scene_info(scene_id)),
                'walls': [asdict(wall) for wall in await self._collect_walls(scene_id)],
                'lighting': [asdict(light) for light in await self._collect_lighting(scene_id)],
                'map_notes': [asdict(note) for note in await self._collect_map_notes(scene_id)],
                'tokens': [asdict(token) for token in await self._collect_tokens(scene_id)],
                'templates': [asdict(template) for template in await self._collect_templates(scene_id)]
            }
            
            self.logger.info(f"Collected complete board state for scene {scene_id}")
            return board_state
            
        except Exception as e:
            self.logger.error(f"Error collecting board state for scene {scene_id}: {e}")
            raise
    
    async def _collect_scene_info(self, scene_id: str) -> SceneInfo:
        """Collect basic scene information"""
        
        try:
            scene_data = await self.foundry_client.get_scene(scene_id)
            
            return SceneInfo(
                width=scene_data.get('width', 0),
                height=scene_data.get('height', 0),
                grid_size=scene_data.get('grid', {}).get('size', 0),
                grid_type=scene_data.get('grid', {}).get('type', 'square'),
                background_src=scene_data.get('background', {}).get('src'),
                scale=scene_data.get('grid', {}).get('scale')
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting scene info: {e}")
            return SceneInfo(0, 0, 0, 'square')
    
    async def _collect_walls(self, scene_id: str) -> List[WallData]:
        """Collect wall and door information"""
        
        try:
            walls_data = await self.foundry_client.get_scene_walls(scene_id)
            walls = []
            
            for wall in walls_data:
                wall_data = WallData(
                    coordinates=wall.get('c', []),  # Foundry uses 'c' for coordinates
                    door_type=wall.get('door'),
                    movement_blocking=wall.get('ds', False),  # 'ds' = door state/movement blocking
                    vision_blocking=wall.get('sight', False),
                    sound_blocking=wall.get('sound', False)
                )
                walls.append(wall_data)
            
            return walls
            
        except Exception as e:
            self.logger.error(f"Error collecting walls: {e}")
            return []
    
    async def _collect_lighting(self, scene_id: str) -> List[LightingData]:
        """Collect lighting and vision information"""
        
        try:
            # Collect global lighting settings
            scene_data = await self.foundry_client.get_scene(scene_id)
            global_lighting = []
            
            # Global darkness level
            if 'darkness' in scene_data:
                global_lighting.append(LightingData(
                    x=0, y=0, radius=0,
                    darkness_level=scene_data['darkness']
                ))
            
            # Collect ambient light sources
            if 'ambientLight' in scene_data:
                ambient = scene_data['ambientLight']
                if 'sources' in ambient:
                    for source in ambient['sources']:
                        lighting_data = LightingData(
                            x=source.get('x', 0),
                            y=source.get('y', 0),
                            radius=source.get('radius', 0),
                            color=source.get('color'),
                            alpha=source.get('alpha'),
                            angle=source.get('angle')
                        )
                        global_lighting.append(lighting_data)
            
            # Collect token-based lighting
            tokens = await self.foundry_client.get_scene_tokens(scene_id)
            for token in tokens:
                if token.get('light', {}).get('enabled', False):
                    light_config = token['light']
                    lighting_data = LightingData(
                        x=token.get('x', 0),
                        y=token.get('y', 0),
                        radius=light_config.get('radius', 0),
                        color=light_config.get('color'),
                        alpha=light_config.get('alpha'),
                        angle=light_config.get('angle')
                    )
                    global_lighting.append(lighting_data)
            
            return global_lighting
            
        except Exception as e:
            self.logger.error(f"Error collecting lighting: {e}")
            return []
    
    async def _collect_map_notes(self, scene_id: str) -> List[MapNote]:
        """Collect map notes"""
        
        try:
            notes_data = await self.foundry_client.get_scene_notes(scene_id)
            notes = []
            
            for note in notes_data:
                note_data = MapNote(
                    x=note.get('x', 0),
                    y=note.get('y', 0),
                    text=note.get('text', ''),
                    icon=note.get('icon'),
                    icon_size=note.get('iconSize'),
                    global_note=note.get('global', False),
                    players_only=note.get('playersOnly', False)
                )
                notes.append(note_data)
            
            return notes
            
        except Exception as e:
            self.logger.error(f"Error collecting map notes: {e}")
            return []
    
    async def _collect_tokens(self, scene_id: str) -> List[TokenData]:
        """Collect complete token data with all attributes"""
        
        try:
            tokens_data = await self.foundry_client.get_scene_tokens(scene_id)
            tokens = []
            
            for token in tokens_data:
                # Get actor data if token is linked
                attributes = {}
                actor_id = token.get('actorId')
                if actor_id:
                    try:
                        actor_data = await self.foundry_client.get_actor(actor_id)
                        if actor_data and 'system' in actor_data:
                            # Extract all attributes from actor.system (system-agnostic)
                            attributes = self._extract_all_attributes(actor_data['system'])
                    except Exception as e:
                        self.logger.warning(f"Could not get actor {actor_id} data: {e}")
                
                token_data = TokenData(
                    id=token.get('_id', ''),
                    name=token.get('name', ''),
                    x=token.get('x', 0),
                    y=token.get('y', 0),
                    width=token.get('width', 1),
                    height=token.get('height', 1),
                    rotation=token.get('rotation', 0),
                    actor_id=actor_id,
                    disposition=token.get('disposition'),
                    hidden=token.get('hidden', False),
                    vision_enabled=token.get('sight', {}).get('enabled', False),
                    vision_range=token.get('sight', {}).get('range'),
                    facing=token.get('rotation', 0)  # Use rotation as facing in most systems
                )
                
                # Add extracted attributes
                token_data.attributes = attributes
                tokens.append(token_data)
            
            return tokens
            
        except Exception as e:
            self.logger.error(f"Error collecting tokens: {e}")
            return []
    
    def _extract_all_attributes(self, system_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract all attributes from system data in a system-agnostic way
        This method traverses the entire system structure to find all attributes
        """
        
        attributes = {}
        
        def extract_recursive(data: Any, prefix: str = ""):
            if isinstance(data, dict):
                for key, value in data.items():
                    new_prefix = f"{prefix}.{key}" if prefix else key
                    
                    # Check if this looks like an attribute (has value property)
                    if isinstance(value, dict) and 'value' in value:
                        attributes[new_prefix] = value['value']
                    elif not isinstance(value, (dict, list)) and value is not None:
                        # Simple value, treat as attribute
                        attributes[new_prefix] = value
                    else:
                        # Recurse into nested structure
                        extract_recursive(value, new_prefix)
            elif isinstance(data, list):
                # Handle arrays - create numbered attributes
                for i, item in enumerate(data):
                    new_prefix = f"{prefix}[{i}]" if prefix else f"[{i}]"
                    extract_recursive(item, new_prefix)
        
        extract_recursive(system_data)
        return attributes
    
    async def _collect_templates(self, scene_id: str) -> List[TemplateData]:
        """Collect area templates and measured templates"""
        
        try:
            templates_data = await self.foundry_client.get_scene_templates(scene_id)
            templates = []
            
            for template in templates_data:
                template_data = TemplateData(
                    id=template.get('_id', ''),
                    x=template.get('x', 0),
                    y=template.get('y', 0),
                    width=template.get('width', 0),
                    height=template.get('height', 0),
                    shape=template.get('shape', 'square'),
                    affected_areas=template.get('affectedAreas', [])
                )
                templates.append(template_data)
            
            return templates
            
        except Exception as e:
            self.logger.error(f"Error collecting templates: {e}")
            return []


# Mock Foundry client for testing
class MockFoundryClient:
    """Mock client for testing BoardStateCollector"""
    
    async def get_scene(self, scene_id: str) -> Dict[str, Any]:
        return {
            'width': 1000,
            'height': 800,
            'grid': {'size': 50, 'type': 'square', 'scale': 1},
            'background': {'src': '/maps/dungeon.jpg'},
            'darkness': 0.2,
            'ambientLight': {
                'sources': [
                    {'x': 100, 'y': 100, 'radius': 200, 'color': '#ffaa00', 'alpha': 0.3}
                ]
            }
        }
    
    async def get_scene_walls(self, scene_id: str) -> List[Dict[str, Any]]:
        return [
            {'c': [[100, 100], [200, 100]], 'door': None, 'ds': True, 'sight': True},
            {'c': [[200, 100], [200, 200]], 'door': 'door', 'ds': False, 'sight': True}
        ]
    
    async def get_scene_notes(self, scene_id: str) -> List[Dict[str, Any]]:
        return [
            {'x': 150, 'y': 150, 'text': 'Treasure Room', 'icon': 'chest', 'playersOnly': False}
        ]
    
    async def get_scene_tokens(self, scene_id: str) -> List[Dict[str, Any]]:
        return [
            {
                '_id': 'token1',
                'name': 'Fighter',
                'x': 100,
                'y': 100,
                'width': 1,
                'height': 1,
                'rotation': 0,
                'actorId': 'actor1',
                'disposition': 1,
                'hidden': False,
                'sight': {'enabled': True, 'range': 60},
                'light': {'enabled': True, 'radius': 30, 'color': '#ffffff'}
            }
        ]
    
    async def get_actor(self, actor_id: str) -> Dict[str, Any]:
        return {
            'system': {
                'attributes': {
                    'hp': {'value': 45, 'max': 50},
                    'ac': {'value': 16},
                    'speed': {'value': 30},
                    'strength': {'value': 18}
                },
                'details': {
                    'level': 5,
                    'class': 'Fighter'
                }
            }
        }
    
    async def get_scene_templates(self, scene_id: str) -> List[Dict[str, Any]]:
        return [
            {'_id': 'template1', 'x': 150, 'y': 150, 'width': 100, 'height': 100, 'shape': 'circle'}
        ]


# Test the implementation
if __name__ == "__main__":
    import asyncio
    
    async def test_board_collector():
        collector = BoardStateCollector(MockFoundryClient())
        
        board_state = await collector.collect_complete_board_state("test_scene")
        
        print("Scene Info:", board_state['scene'])
        print("Walls:", board_state['walls'])
        print("Lighting:", board_state['lighting'])
        print("Map Notes:", board_state['map_notes'])
        print("Tokens:", board_state['tokens'])
        print("Templates:", board_state['templates'])
        
        # Test attribute extraction
        for token in board_state['tokens']:
            if token.attributes:
                print(f"Token '{token.name}' attributes:", token.attributes)
    
    asyncio.run(test_board_collector())
