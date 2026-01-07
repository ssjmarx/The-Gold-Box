/**
 * The Gold Box - Scene Data Collector Service
 * Collects scene spatial data for AI spatial queries
 * 
 * Purpose:
 * - Collect scene data (walls, doors, notes, lights, tokens)
 * - Collect grid settings (size, units)
 * - Collect distance unit preferences
 * - Provide scene data to backend for spatial filtering
 */

export class SceneDataCollector {
  constructor() {
    this.sceneData = null;
    this.gridSize = 100; // Default: 100 pixels per grid square
    this.distanceUnit = '5 feet'; // Default distance unit setting
    this.isSceneReady = false;
    
    console.log('The Gold Box: SceneDataCollector initialized');
  }

  /**
   * Check if scene is ready and collect data
   * Called when backend requests scene spatial data
   * 
   * @returns {Object|null} Scene data object or null if not ready
   */
  collectSceneData() {
    if (!game || !game.scenes) {
      console.warn('The Gold Box: Game or scenes not available');
      return null;
    }

    const scene = game.scenes.active;
    if (!scene) {
      console.warn('The Gold Box: No active scene');
      return null;
    }

    console.log(`The Gold Box: Collecting scene data for "${scene.name}" (${scene.id})`);

    // Collect grid settings
    this.collectGridSettings(scene);

    // Collect scene objects
    const walls = this.collectWalls(scene);
    const doors = this.collectDoors(scene);
    const notes = this.collectNotes(scene);
    const lights = this.collectLights(scene);
    const tokens = this.collectTokens(scene);

    // Assemble scene data
    this.sceneData = {
      scene_id: scene.id,
      scene_name: scene.name,
      grid_size: this.gridSize,
      distance_unit: this.distanceUnit,
      walls: walls,
      doors: doors,
      notes: notes,
      lights: lights,
      tokens: tokens,
      timestamp: Date.now()
    };

    this.isSceneReady = true;
    console.log(`The Gold Box: Scene data collected: ${walls.length} walls, ${doors.length} doors, ${notes.length} notes, ${lights.length} lights, ${tokens.length} tokens`);

    return this.sceneData;
  }

  /**
   * Collect grid settings from scene
   * 
   * @param {Scene} scene - Foundry scene object
   */
  collectGridSettings(scene) {
    // Get grid size from scene
    this.gridSize = scene.grid.size || 100;

    // Get distance unit from settings
    this.distanceUnit = this.getDistanceUnitSetting();

    console.log(`The Gold Box: Grid settings - size: ${this.gridSize}px, distance unit: ${this.distanceUnit}`);
  }

  /**
   * Collect walls from scene
   * 
   * @param {Scene} scene - Foundry scene object
   * @returns {Array} Array of wall objects
   */
  collectWalls(scene) {
    const walls = [];

    if (!scene.walls) {
      console.log('The Gold Box: No walls in scene');
      return walls;
    }

    for (const wall of scene.walls) {
      // Foundry V12: wall objects are already Documents, access properties directly
      walls.push({
        id: wall.id,
        c: [
          wall.c[0], // x1
          wall.c[1], // y1
          wall.c[2], // x2
          wall.c[3]  // y2
        ],
        blocks_vision: !!wall.dir, // Direction determines if it blocks vision
        blocks_movement: !!wall.sense, // Sense determines if it blocks movement
        coordinates: {
          start: { x: wall.c[0], y: wall.c[1] },
          end: { x: wall.c[2], y: wall.c[3] }
        }
      });
    }

    console.log(`The Gold Box: Collected ${walls.length} walls`);
    return walls;
  }

  /**
   * Collect doors from scene
   * 
   * @param {Scene} scene - Foundry scene object
   * @returns {Array} Array of door objects
   */
  collectDoors(scene) {
    const doors = [];

    if (!scene.walls) {
      return doors;
    }

    for (const wall of scene.walls) {
      // Foundry V12: Check if this wall is a door (has door property)
      if (wall.door === undefined) {
        continue;
      }

      const door = wall.door;

      doors.push({
        id: wall.id,
        door: door,
        state: this.getDoorState(door),
        locked: door === 1, // Door type 1 is locked
        blocks_vision: !!wall.dir,
        c: [
          wall.c[0],
          wall.c[1],
          wall.c[2],
          wall.c[3]
        ],
        coordinates: {
          start: { x: wall.c[0], y: wall.c[1] },
          end: { x: wall.c[2], y: wall.c[3] }
        }
      });
    }

    console.log(`The Gold Box: Collected ${doors.length} doors`);
    return doors;
  }

  /**
   * Get door state as human-readable string
   * 
   * @param {number} door - Door type constant
   * @returns {string} Door state
   */
  getDoorState(door) {
    // Foundry door constants
    // 0: None (no door)
    // 1: Door (closed)
    // 2: Double Door (closed)
    // 3: Secret Door (closed)
    // 4: Secret Door (open)
    // 5: Door (open)
    // 6: Double Door (open)
    
    if (door === undefined || door === 0) return 'none';
    if (door === 1) return 'closed';
    if (door === 2) return 'closed_double';
    if (door === 3) return 'secret_closed';
    if (door === 4) return 'secret_open';
    if (door === 5) return 'open';
    if (door === 6) return 'open_double';
    return 'unknown';
  }

  /**
   * Collect journal notes from scene
   * 
   * @param {Scene} scene - Foundry scene object
   * @returns {Array} Array of note objects
   */
  collectNotes(scene) {
    const notes = [];

    if (!scene.notes) {
      console.log('The Gold Box: No notes in scene');
      return notes;
    }

    for (const note of scene.notes) {
      // Get journal entry name
      const journalEntry = game.journal.get(note.entryId);
      
      notes.push({
        id: note.id,
        entry_id: note.entryId,
        entry_name: journalEntry?.name || 'Unknown',
        journal_entry_title: journalEntry?.name || 'Unknown',
        note_type: journalEntry?.flags?.['gold-box']?.noteType || 'location',
        x: note.x,
        y: note.y,
        icon_size: note.iconSize,
        text_color: note.textColor,
        icon_tint: note.iconTint
      });
    }

    console.log(`The Gold Box: Collected ${notes.length} journal notes`);
    return notes;
  }

  /**
   * Collect light sources from scene
   * 
   * @param {Scene} scene - Foundry scene object
   * @returns {Array} Array of light objects
   */
  collectLights(scene) {
    const lights = [];

    if (!scene.lights) {
      console.log('The Gold Box: No lights in scene');
      return lights;
    }

    for (const light of scene.lights) {
      // Get source token if this is a token light
      const sourceToken = light.document?.tokenId ? 
        game.tokens.get(light.document.tokenId) : null;

      lights.push({
        id: light.id,
        source_token: sourceToken?.name || 'Scene Light',
        x: light.x,
        y: light.y,
        radius: light.document?.radius || 0,
        color: light.document?.color || '#ffffff',
        brightness: this.getBrightnessLevel(light.document?.bright || 0),
        alpha: light.document?.alpha || 0.5
      });
    }

    console.log(`The Gold Box: Collected ${lights.length} lights`);
    return lights;
  }

  /**
   * Get brightness level as human-readable string
   * 
   * @param {number} bright - Brightness value
   * @returns {string} Brightness level
   */
  getBrightnessLevel(bright) {
    if (bright <= 0) return 'none';
    if (bright < 10) return 'dim';
    if (bright < 20) return 'normal';
    if (bright < 30) return 'bright';
    return 'very_bright';
  }

  /**
   * Collect tokens from scene
   * 
   * @param {Scene} scene - Foundry scene object
   * @returns {Array} Array of token objects
   */
  collectTokens(scene) {
    const tokens = [];

    if (!scene.tokens) {
      console.log('The Gold Box: No tokens in scene');
      return tokens;
    }

    for (const token of scene.tokens) {
      const actor = token.actor;
      
      // Calculate center coordinates for spatial queries
      const centerX = token.x + (token.width * this.gridSize) / 2;
      const centerY = token.y + (token.height * this.gridSize) / 2;
      
      tokens.push({
        id: token.id,
        name: actor?.name || 'Unknown',
        actor_id: actor?.id || null,
        x: centerX,
        y: centerY,
        width: token.width,
        height: token.height,
        is_player: token.actor?.hasPlayerOwner || false,
        disposition: token.document?.disposition || 0, // -1: hostile, 0: neutral, 1: friendly
        is_hidden: token.document?.hidden || false
      });
    }

    console.log(`The Gold Box: Collected ${tokens.length} tokens`);
    return tokens;
  }

  /**
   * Get distance unit setting from settings
   * 
   * @returns {string} Distance unit setting (e.g., "5 feet", "2 meters", "squares")
   */
  getDistanceUnitSetting() {
    // Try to get from The Gold Box settings
    if (window.goldBoxSettings?.distanceUnit) {
      return window.goldBoxSettings.distanceUnit;
    }

    // Fallback: try to detect from Foundry canvas
    if (canvas?.scene?.grid?.units) {
      const gridUnits = canvas.scene.grid.units;
      const gridDistance = canvas.scene.grid.distance;
      
      // Foundry uses: grid.distance grid.units per square
      // e.g., "5 ft", "2 m", "1 sq"
      if (gridUnits === 'ft') {
        return `${gridDistance} feet`;
      } else if (gridUnits === 'm') {
        return `${gridDistance} meters`;
      } else {
        return 'squares';
      }
    }

    // Default fallback
    return '5 feet';
  }

  /**
   * Refresh scene data (called when scene changes)
   */
  refresh() {
    console.log('The Gold Box: Refreshing scene data');
    this.sceneData = null;
    this.isSceneReady = false;
    this.collectSceneData();
  }

  /**
   * Get cached scene data
   * 
   * @returns {Object|null} Cached scene data or null
   */
  getSceneData() {
    return this.sceneData;
  }

  /**
   * Check if scene data is ready
   * 
   * @returns {boolean} True if scene data is ready
   */
  isReady() {
    return this.isSceneReady;
  }
}

// Create global instance and attach to window
if (!window.SceneDataCollector) {
  window.SceneDataCollector = new SceneDataCollector();
  console.log('The Gold Box: SceneDataCollector attached to window');
}

// Register hooks for scene updates
Hooks.on('updateScene', (scene, data, options, userId) => {
  if (scene.active) {
    window.SceneDataCollector?.refresh();
  }
});

Hooks.on('createToken', (token, options, userId) => {
  window.SceneDataCollector?.refresh();
});

Hooks.on('deleteToken', (token, options, userId) => {
  window.SceneDataCollector?.refresh();
});

Hooks.on('updateToken', (token, data, options, userId) => {
  // Only refresh if position changed
  if (data.x !== undefined || data.y !== undefined) {
    window.SceneDataCollector?.refresh();
  }
});

console.log('The Gold Box: Scene data collector loaded and hooks registered');
