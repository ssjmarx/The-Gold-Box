# Gold Box v0.3.0 - API Chat Endpoint Fix Plan

## Problem Summary

The API chat endpoint is failing because the Gold API module's WebSocket infrastructure is missing a handler for `chat-messages` message type. When the backend sends a request to retrieve chat messages via the relay server, the relay server forwards this to the Gold API module, but there's no router to handle the request, resulting in the error:

> logger.ts:40 foundryvtt-gold-api | No handler for message type: chat-messages

## Root Cause Analysis

1. **Missing Handler**: The Gold API module (`foundryvtt-gold-api`) has a JavaScript implementation in `/scripts/module.js` that handles `chat-messages` requests, but the TypeScript WebSocket infrastructure in `/src/ts/network/routers/all.ts` doesn't include a chat router.

2. **Architecture Gap**: 
   - Relay server correctly sends `chat-messages` requests to Gold API module
   - Gold API module receives the request but has no TypeScript handler
   - Backend times out waiting for response that never comes

3. **Data Flow Breakdown**:
   - Backend → Relay Server: `{"type": "chat-messages", "limit": X, "sort": "timestamp", "order": "desc"}`
   - Relay Server → Gold API: WebSocket message with `chat-messages` type
   - Gold API: ❌ No handler → Error logged → No response
   - Backend: ⏰ Times out → Generic AI response without context

## Solution Plan

### Phase 1: Create Chat Router in Gold API Module

**Objective**: Add TypeScript chat router to handle `chat-messages` requests properly.

#### Files to Create/Modify:

1. **Create `/home/ssjmarx/foundryvtt-gold-api/src/ts/network/routers/chat.ts`**
   - Implement chat router following existing patterns
   - Handle `chat-messages` requests with limit/sort/order parameters
   - Access `recentChatMessages` from JavaScript module's storage
   - Return properly formatted response

2. **Update `/home/ssjmarx/foundryvtt-gold-api/src/ts/network/routers/all.ts`**
   - Import the new chat router
   - Add it to the routers array

### Phase 2: Implementation Details

#### Chat Router Structure:
```typescript
import { Router } from "./baseRouter"
import { ModuleLogger } from "../../utils/logger"
import { moduleId } from "../../constants"

export const router = new Router("chatRouter");

router.addRoute({
    actionType: "chat-messages",
    handler: async (data, context) => {
        const socketManager = context?.socketManager;
        ModuleLogger.info("Received request for chat messages:", data);
        
        try {
            const limit = data.limit || 50;
            const sort = data.sort || "timestamp";
            const order = data.order || "desc";
            
            // Get messages from JavaScript module's storage
            const module = game.modules.get(moduleId);
            let messages = [...(module?.api?.getChatMessages() || [])];
            
            // Apply sorting
            if (sort === "timestamp") {
                messages.sort((a, b) => {
                    return order === "desc" ? b.timestamp - a.timestamp : a.timestamp - b.timestamp;
                });
            }
            
            // Apply limit
            const limitedMessages = messages.slice(0, limit);
            
            ModuleLogger.info(`Returning ${limitedMessages.length} chat messages`);
            
            // Send response back
            socketManager?.send({
                type: "chat-messages-result",
                requestId: data.requestId,
                messages: limitedMessages,
                total: messages.length
            });
            
        } catch (error) {
            ModuleLogger.error("Error processing chat messages request:", error);
            socketManager?.send({
                type: "chat-messages-result",
                requestId: data.requestId,
                error: error.message,
                messages: []
            });
        }
    }
});
```

#### Update to routers/all.ts:
```typescript
import {Router} from "./baseRouter"
import {router as PingPongRouter} from "./pingPong"
import {router as EntityRouter} from "./entity"
import {router as EncounterRouter} from "./encounter"
import {router as RollRouter} from "./roll"
import {router as SearchRouter} from "./search"
import {router as StructureRouter} from "./structure"
import {router as SheetRouter} from "./sheet"
import {router as MacroRouter} from "./macro"
import {router as UtilityRouter} from "./utility"
import {router as FileSystemRouter} from "./fileSystem"
import {router as Dnd5eRouter} from "./dnd5e"
import {router as ChatRouter} from "./chat"  // NEW

export const routers: Router[] = [
    PingPongRouter,
    EntityRouter,
    EncounterRouter,
    ChatRouter,  // NEW - Add chat router
    RollRouter,
    SearchRouter,
    StructureRouter,
    SheetRouter,
    MacroRouter,
    UtilityRouter,
    FileSystemRouter,
    Dnd5eRouter
]
```

### Phase 3: Integration Points

#### Key Integration Requirements:

1. **Data Access**: TypeScript router must access JavaScript module's `recentChatMessages` array
2. **Message Format**: Return messages in the exact format expected by the backend
3. **Request/Response Pattern**: Implement proper request-response with unique request IDs
4. **Error Handling**: Graceful error responses for invalid requests

#### Cross-Module Communication:

The TypeScript router needs to access the JavaScript module's message storage. The existing `/scripts/module.js` already has:
- `recentChatMessages` array for storage
- `getChatMessages()` method in the module's API object

### Phase 4: Testing Strategy

#### Success Criteria:
- ✅ No more "No handler for message type: chat-messages" errors
- ✅ Backend receives actual chat messages from relay server
- ✅ API chat endpoint returns AI responses with real context
- ✅ Backward compatibility maintained

#### Test Steps:
1. Build Gold API module with new chat router
2. Install updated module in Foundry
3. Test API chat mode in Gold Box settings
4. Verify chat context is properly retrieved and processed
5. Confirm AI responses include actual conversation context

## Implementation Benefits

### Technical Benefits:
- **Minimal Changes**: Only adding one new router file
- **Follows Existing Patterns**: Uses same architecture as other working routers
- **Maintains Compatibility**: Doesn't break existing functionality
- **Direct Fix**: Addresses the exact error message

### Expected Outcome:
After implementation, the data flow will work correctly:
1. Backend sends `chat-messages` request to relay server
2. Relay server forwards to Gold API module
3. Gold API module's new chat router handles the request
4. Chat messages are returned to relay server
5. Relay server forwards messages back to backend
6. Backend processes messages with AI and returns contextual response

## Files Summary

### New Files:
- `/home/ssjmarx/foundryvtt-gold-api/src/ts/network/routers/chat.ts`

### Modified Files:
- `/home/ssjmarx/foundryvtt-gold-api/src/ts/network/routers/all.ts`

This focused fix should resolve the core issue preventing the API chat endpoint from working with real Foundry chat context.
