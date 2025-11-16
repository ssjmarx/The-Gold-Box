# Installation Guide for The Gold Box

## Quick Setup for Testing

### 1. Install the Module in Foundry VTT

1. Open your Foundry VTT instance
2. Go to **Game Settings** → **Module Management**
3. Click **Add Module** → **Upload Module**
4. Select the entire `/home/ssjmarx/Gold Box` folder
5. The module should appear as "The Gold Box" in your module list
6. Enable the module for your game world

### 2. Verify Installation

Once installed and enabled, you should see:

1. **Console Messages**: Open the browser developer console (F12) and look for:
   - "The Gold Box module initialized"
   - "The Gold Box is ready for AI adventures!"

2. **UI Elements**:
   - A "The Gold Box" button in the Game Settings menu
   - A "Take AI Turn" button in the chat sidebar
   - Clicking either should show the module info dialog

3. **Chat Notification**: Clicking "Take AI Turn" should show:
   - "The Gold Box: AI functionality coming soon!" notification

### 3. Module Structure

The module includes:

```
Gold Box/
├── module.json          # Module manifest (required by Foundry)
├── scripts/
│   └── gold-box.js       # Main module logic
├── styles/
│   └── gold-box.css      # UI styling
├── lang/
│   └── en.json           # English translations
├── templates/            # UI templates (empty for now)
├── packs/               # Compendium packs (empty for now)
├── README.md            # Project documentation
├── CHANGELOG.md         # Version history
├── LICENSE              # Creative Commons license
└── .gitignore           # Git ignore rules
```

### 4. Testing Steps

1. **Start Foundry VTT**
2. **Load a Game World** (or create a new one)
3. **Enable the Module** in world settings
4. **Check the Console** for initialization messages
5. **Test UI Elements**:
   - Go to Game Settings and look for "The Gold Box" button
   - Go to the Chat tab and look for "Take AI Turn" button
   - Click both buttons to verify they work

### 5. Expected Behavior

- ✅ Module loads without errors
- ✅ Console shows initialization messages
- ✅ UI elements appear in correct locations
- ✅ Buttons are clickable and show information
- ✅ No actual AI functionality yet (as intended)

### 6. Troubleshooting

If the module doesn't load:

1. **Check Console**: Look for JavaScript errors in F12 console
2. **Verify Files**: Ensure all files are present and readable
3. **Module.json**: Validate JSON syntax
4. **Foundry Version**: Ensure you're running Foundry VTT v12+

## Next Steps

Once you confirm the basic module loads successfully, you can proceed with:

1. **Phase 1**: Setting up the Python backend and basic LLM communication
2. **Phase 2**: Adding context awareness and game state gathering
3. **Phase 3**: Implementing tool-driven actions
4. **Phase 4**: Adding multi-modal capabilities

## Development Notes

- The module uses ES6 modules and requires Foundry VTT v12+
- All AI functionality is currently placeholder code
- The module is designed to be safe and won't modify any game data
- Socket support is enabled for future real-time communication
