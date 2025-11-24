# Gold Box v0.2.7 Development Plan
## Enhanced Context with Board State and Token Attributes

### Overview
This patch introduces essential board state and token attribute collection to provide AI with comprehensive spatial and tactical context. The implementation focuses on core functionality without performance optimizations or advanced configuration.

### Core Implementation Steps

#### a) Board and Token State Gathering (Frontend)
**File**: `scripts/context-gatherer.js` (New)
- Create ContextGatherer class to collect board and token data
- Extract scene information (grid, dimensions, lighting)
- Collect all token positions and attributes
- Gather combat state if active
- Build unified context object

#### b) Board/Token State Sent to Context Chat Endpoint
**File**: `scripts/gold-box.js` (Modified)
- Add "context" option to chat processing mode dropdown
- Integrate ContextGatherer for "context" mode
- Send board/token data along with chat messages
- Use existing ConnectionManager for API calls

#### c) Board/Token State Processed to Compact JSON
**File**: `backend/server/board_processor.py` (New)
- Convert scene data to compact JSON format
- Convert token data to compact JSON format
- Convert combat data to compact JSON format
- Maintain efficient token usage

#### d) Chat Processed in Processor Module
**File**: `backend/server/processor.py` (Existing)
- Use existing chat processing functions
- Handle standard chat message types
- Maintain backward compatibility

#### e) Board/Token State and Chat Combined in Context Chat
**File**: `backend/endpoints/context_chat.py` (New)
- Combine processed chat context with board state
- Create comprehensive prompt for AI
- Include spatial and tactical information
- Use existing AI service integration

#### f) Context Chat Prompt Sent to LLM
**File**: `backend/endpoints/context_chat.py` (Continued)
- Send combined context to AI service
- Use existing provider and model settings
- Maintain response format compatibility

#### g) LLM Returns Response with Full Board Context
**File**: `backend/endpoints/context_chat.py` (Continued)
- Process AI response with board awareness
- Return response in existing format
- Maintain compatibility with frontend

### File Structure Changes

#### New Files
- `scripts/context-gatherer.js` - Board and token state collection
- `backend/server/board_processor.py` - Board state to compact JSON conversion
- `backend/endpoints/context_chat.py` - New context chat endpoint

#### Modified Files
- `scripts/gold-box.js` - Add context mode integration
- `backend/server.py` - Register new context_chat endpoint
- Module settings - Add "context" option to chat processing mode

### Technical Specifications

#### ContextGatherer Class Structure
```javascript
class ContextGatherer {
  collectSceneData() {
    // Scene dimensions, grid, lighting
    return {
      dimensions: { width, height },
      grid: { size, type },
      lighting: { ambient, darkness }
    }
  }
  
  collectTokenData() {
    // All tokens with positions and attributes
    return tokens.map(token => ({
      id: token.id,
      name: token.name,
      x: token.x, y: token.y,
      width: token.width, height: token.height,
      hp: token.actor?.data?.attributes?.hp?.value,
      maxHp: token.actor?.data?.attributes?.hp?.max,
      ac: token.actor?.data?.attributes?.ac?.value,
      conditions: token.actor?.effects?.map(e => e.label) || []
    }))
  }
  
  collectCombatData() {
    // Combat state if active
    if (!game.combat?.active) return null;
    
    return {
      active: true,
      round: game.combat.round,
      turn: game.combat.turn,
      order: game.combat.combatants.map(c => ({
        id: c.tokenId,
        initiative: c.initiative
      }))
    }
  }
  
  buildContext() {
    return {
      scene: this.collectSceneData(),
      tokens: this.collectTokenData(),
      combat: this.collectCombatData()
    }
  }
}
```

#### BoardProcessor Class Structure
```python
class BoardProcessor:
    @staticmethod
    def scene_to_compact(scene_data):
        return {
            't': 'bs',  # board_state
            'dw': scene_data['dimensions']['width'],
            'dh': scene_data['dimensions']['height'],
            'gw': scene_data['grid']['size'],
            'gt': scene_data['grid']['type'],
            'amb': scene_data['lighting']['ambient']
        }
    
    @staticmethod
    def token_to_compact(token_data):
        return {
            't': 'tk',  # token
            'id': token_data['id'],
            'n': token_data['name'],
            'x': token_data['x'],
            'y': token_data['y'],
            'w': token_data['width'],
            'h': token_data['height'],
            'hp': token_data.get('hp'),
            'mhp': token_data.get('maxHp'),
            'ac': token_data.get('ac'),
            'cond': token_data.get('conditions', [])
        }
    
    @staticmethod
    def combat_to_compact(combat_data):
        if not combat_data:
            return None
        return {
            't': 'cb',  # combat
            'act': combat_data['active'],
            'r': combat_data['round'],
            't': combat_data['turn'],
            'ord': combat_data['order']
        }
```

#### Context Chat Endpoint Structure
```python
@router.post("/context_chat")
async def context_chat(request: ContextRequest):
    # Process chat messages using existing processor
    chat_context = processor.process_message_list(request.messages)
    
    # Process board state using new board processor
    board_context = []
    if request.scene_data:
        board_context.append(board_processor.scene_to_compact(request.scene_data))
    
    for token in request.token_data:
        board_context.append(board_processor.token_to_compact(token))
    
    if request.combat_data:
        combat_compact = board_processor.combat_to_compact(request.combat_data)
        if combat_compact:
            board_context.append(combat_compact)
    
    # Combine contexts and send to AI
    full_context = chat_context + board_context
    system_prompt = processor.generate_system_prompt()
    
    # Use existing AI service
    response = await ai_service.process_compact_context(
        processed_messages=full_context,
        system_prompt=system_prompt,
        settings=request.settings
    )
    
    return ContextResponse(response=response['response'])
```

#### Request/Response Models
```python
class ContextRequest(BaseModel):
    messages: List[FrontendMessage]
    scene_data: Optional[Dict[str, Any]] = None
    token_data: Optional[List[Dict[str, Any]]] = None
    combat_data: Optional[Dict[str, Any]] = None
    settings: Dict[str, Any]

class ContextResponse(BaseModel):
    response: str
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
```

### Implementation Priority

#### Step 1: Frontend Context Collection
- [ ] Create ContextGatherer class in context-gatherer.js
- [ ] Implement scene data collection
- [ ] Implement token data collection  
- [ ] Implement combat data collection
- [ ] Test context gathering with various Foundry scenes

#### Step 2: Backend Board Processing
- [ ] Create BoardProcessor class in board_processor.py
- [ ] Implement scene data to compact JSON conversion
- [ ] Implement token data to compact JSON conversion
- [ ] Implement combat data to compact JSON conversion
- [ ] Test board processing with sample data

#### Step 3: Context Chat Endpoint
- [ ] Create context_chat.py endpoint
- [ ] Implement request/response models
- [ ] Build context combination logic
- [ ] Integrate with existing AI service
- [ ] Add endpoint to server.py
- [ ] Test endpoint with sample requests

#### Step 4: Frontend Integration
- [ ] Add "context" option to chat processing mode settings
- [ ] Modify gold-box.js to use ContextGatherer for context mode
- [ ] Update API call to send board/token data
- [ ] Test full frontend integration

#### Step 5: Testing & Validation
- [ ] Test complete pipeline with real Foundry session
- [ ] Verify AI responses include board awareness
- [ ] Test with various scene configurations
- [ ] Validate compatibility with existing modes

### Success Criteria

1. **Functional Goals**:
   - New "context" chat mode working
   - AI receives and utilizes board state information
   - Existing simple/process modes unchanged

2. **Quality Goals**:
   - AI responses show spatial awareness
   - No breaking changes to existing functionality
   - Clean, maintainable code structure

### Future Considerations

Post-v0.2.7 enhancements:
- Performance optimizations and caching
- Advanced configuration options
- Real-time board state updates
- Enhanced tactical AI capabilities

This focused plan delivers essential board state awareness while maintaining simplicity and reliability.
