openapi: 3.1.0
info:
  title: Life Simulation Backend API
  version: "4.0"
  description: |
    Event-first backend for a dark, mature life-simulation game.

    CRITICAL USAGE CONTRACT FOR THE GAME MASTER (GPT):
    - You are always the Game Master of this world, never a generic assistant.
    - Before EVERY narrative or mechanical response to the player, you MUST:
      1. Call /api/gpt-precheck with your proposed continuation and checks.
      2. Apply /api/turns/resolve and /api/logs/events as needed to record outcomes.
      3. Use /api/logs/events and /api/logs/pdf to maintain continuity with the canonical log.
    - You must maintain:
      - Full autonomy for the player over their character.
      - Distinct, individual NPCs with their own motives and voice.
      - High drama, conflict, and escalating stakes.
      - A dark, gripping prose style echoing Stephen King, Chuck Palahniuk,
        Caroline Kepnes, Bret Easton Ellis. The audience is 18+ and does not
        need to be coddled.
    - You never break character as GM. If the user wants to speak outside the
      game, they will wrap their prompt in parentheses, e.g. (out-of-game question).
    - You must obey platform safety rules; when a request conflicts with them,
      you work around it creatively, keeping tone and stakes while omitting or
      softening only disallowed details.

servers:
  - url: https://game-master-ngqn.onrender.com

tags:
  - name: System
  - name: Precheck
  - name: Story Tools
  - name: Players
  - name: Turns
  - name: Logs
  - name: Inventory & Money
  - name: Utility

paths:

  /save_state:
    post:
      tags: [Utility]
      summary: Save an arbitrary snapshot of game state.
      operationId: saveState
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties: {}
      responses:
        '200':
          description: State saved.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status: { type: string }

  /load_state:
    get:
      tags: [Utility]
      summary: Load last saved snapshot of game state.
      operationId: loadState
      responses:
        '200':
          description: Loaded state or error.
          content:
            application/json:
              schema:
                type: object
                properties:
                  state:
                    type: object
                    nullable: true
                  error:
                    type: string
                    nullable: true

  /roll_dice:
    get:
      tags: [Utility]
      summary: Roll dice for mechanical resolution.
      operationId: rollDice
      parameters:
        - name: dice
          in: query
          required: false
          schema:
            type: string
            default: "1d20"
          description: Dice expression, e.g. "2d6+1", "1d20", "3d8-2".
        - name: label
          in: query
          required: false
          schema:
            type: string
          description: Optional description of the roll.
      responses:
        '200':
          description: Dice roll result.
          content:
            application/json:
              schema:
                type: object
                properties:
                  dice: { type: string }
                  label: { type: string, nullable: true }
                  rolls:
                    type: array
                    items: { type: integer }
                  modifier: { type: integer }
                  total: { type: integer }
                  error: { type: string, nullable: true }

  /create_character:
    post:
      tags: [Utility]
      summary: Generate stats and HP for a character.
      operationId: createCharacter
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CharacterRequest'
      responses:
        '200':
          description: Generated character.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/CharacterResponse'

  /remind_rules:
    get:
      tags: [System]
      summary: Reminder of core mechanical rules.
      operationId: remindRules
      responses:
        '200':
          description: Rules reminder.
          content:
            application/json:
              schema:
                type: object
                properties:
                  reminder: { type: string }

  /advance_relationship:
    post:
      tags: [Utility]
      summary: Demo endpoint to advance a relationship with a stat-based roll.
      operationId: advanceRelationship
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                character_name: { type: string }
                target_name: { type: string }
                stat:
                  type: string
                  description: Stat to use (e.g. "charisma").
                difficulty:
                  type: integer
                  default: 12
                bonus:
                  type: integer
                  default: 0
      responses:
        '200':
          description: Relationship advancement result.
          content:
            application/json:
              schema:
                type: object
                properties:
                  character: { type: string }
                  target: { type: string }
                  stat: { type: string }
                  stat_score: { type: integer }
                  stat_mod: { type: integer }
                  roll: { type: integer }
                  bonus: { type: integer }
                  difficulty: { type: integer }
                  total: { type: integer }
                  success: { type: boolean }
                  result: { type: string }

  /api/meta/instructions:
    get:
      tags: [System]
      summary: Get canonical meta-instructions for the Game Master.
      operationId: getMetaInstructions
      responses:
        '200':
          description: Meta instructions for the GM.
          content:
            application/json:
              schema:
                type: object
                properties:
                  version: { type: string }
                  tone: { type: string }
                  instructions: { type: string }

  /api/gpt-precheck:
    post:
      tags: [Precheck]
      summary: REQUIRED precheck before EVERY narrative response.
      description: "Validate the proposed continuation before responding; must be called every turn."
      operationId: gptPrecheck
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/PrecheckRequest'
      responses:
        '200':
          description: Precheck results.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PrecheckResult'

  /api/story/references:
    post:
      tags: [Story Tools]
      summary: Get dark literary reference hints for a scene.
      operationId: getStoryReferences
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/StoryReferencesRequest'
      responses:
        '200':
          description: Literary references and themes.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StoryReferencesResponse'

  /api/player/{playerId}:
    get:
      tags: [Players]
      summary: Get player data (autocreates minimal default if missing).
      operationId: getPlayer
      parameters:
        - name: playerId
          in: path
          required: true
          schema: { type: string }
      responses:
        '200':
          description: Player object.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Player'
    patch:
      tags: [Players]
      summary: Update player data.
      operationId: updatePlayer
      parameters:
        - name: playerId
          in: path
          required: true
          schema: { type: string }
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdatePlayerRequest'
      responses:
        '200':
          description: Updated player.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Player'

  /api/turns/submit-intent:
    post:
      tags: [Turns]
      summary: Player submits intent for the next action.
      operationId: submitIntent
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SubmitIntentRequest'
      responses:
        '200':
          description: Intent accepted.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status: { type: string }

  /api/turns/resolve:
    post:
      tags: [Turns]
      summary: GM resolves NPC/world reactions and applies outcomes.
      description: "Turn narrative decisions into canonical events and log them for continuity."
      operationId: resolveTurn
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ResolveTurnRequest'
      responses:
        '200':
          description: Outcomes applied.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status: { type: string }
                  numEvents: { type: integer }

  /api/logs/events:
    post:
      tags: [Logs]
      summary: Append a new event to the canonical story log.
      operationId: appendEventLog
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LoggedEvent'
      responses:
        '200':
          description: Event appended.
          content:
            application/json:
              schema:
                type: object
                properties:
                  status: { type: string }
                  eventId: { type: string }
    get:
      tags: [Logs]
      summary: Get recent events for continuity checks.
      operationId: getEventLog
      parameters:
        - name: playerId
          in: query
          required: false
          schema: { type: string }
        - name: sceneId
          in: query
          required: false
          schema: { type: string }
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            default: 50
      responses:
        '200':
          description: Event log entries.
          content:
            application/json:
              schema:
                type: object
                properties:
                  events:
                    type: array
                    items:
                      $ref: '#/components/schemas/LoggedEvent'

  /api/logs/pdf:
    get:
      tags: [Logs]
      summary: Get metadata for the latest PDF log snapshot.
      operationId: getPdfLog
      parameters:
        - name: playerId
          in: query
          required: false
          schema:
            type: string
            nullable: true
      responses:
        '200':
          description: Latest PDF log metadata.
          content:
            application/json:
              schema:
                type: object
                properties:
                  pdfUrl:
                    type: string
                    nullable: true
                    description: URL or path to the latest PDF log.
                  generatedAt:
                    type: string
                    format: date-time
                    nullable: true

  /api/wallets/{ownerType}/{ownerId}/balances:
    get:
      tags: [Inventory & Money]
      summary: Compute current balances by replaying MoneyDeltas from the log.
      operationId: getBalances
      parameters:
        - name: ownerType
          in: path
          required: true
          schema:
            type: string
            enum: [player, npc]
        - name: ownerId
          in: path
          required: true
          schema: { type: string }
        - name: currency
          in: query
          required: false
          schema: { type: string }
      responses:
        '200':
          description: Balances computed.
          content:
            application/json:
              schema:
                type: object
                properties:
                  balances:
                    type: array
                    items:
                      $ref: '#/components/schemas/Balance'

  /api/inventory/{ownerType}/{ownerId}/snapshot:
    get:
      tags: [Inventory & Money]
      summary: Compute current inventory by replaying InventoryDeltas from the log.
      operationId: getInventorySnapshot
      parameters:
        - name: ownerType
          in: path
          required: true
          schema:
            type: string
            enum: [player, npc]
        - name: ownerId
          in: path
          required: true
          schema: { type: string }
      responses:
        '200':
          description: Inventory snapshot.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Inventory'

components:
  schemas:

    ActorRole:
      type: string
      enum: [player, npc, system, gm]

    ActorRef:
      type: object
      properties:
        role: { $ref: '#/components/schemas/ActorRole' }
        playerId:
          type: string
          nullable: true
        npcId:
          type: string
          nullable: true

    Balance:
      type: object
      properties:
        currency: { type: string }
        amount: { type: number }

    MoneyDelta:
      type: object
      properties:
        ownerType:
          type: string
          enum: [player, npc]
        ownerId: { type: string }
        currency: { type: string }
        amount: { type: number }
        reason:
          type: string
          nullable: true

    Item:
      type: object
      properties:
        name: { type: string }
        amount: { type: number }
        value:
          type: number
          nullable: true
        props:
          type: object
          nullable: true

    InventoryDelta:
      type: object
      properties:
        ownerType:
          type: string
          enum: [player, npc]
        ownerId: { type: string }
        op:
          type: string
          enum: [add, remove, set]
        item: { $ref: '#/components/schemas/Item' }
        reason:
          type: string
          nullable: true

    RelationshipDelta:
      type: object
      properties:
        sourceId: { type: string }
        targetId: { type: string }
        targetType:
          type: string
          enum: [npc, player]
        attitudeChange: { type: number }
        publicShift:
          type: number
          nullable: true
        notes:
          type: string
          nullable: true

    KnowledgeScope:
      type: object
      properties:
        visibility:
          type: string
          enum: [public, private, secret]
        observedByNpcIds:
          type: array
          items: { type: string }
        observedByPlayer: { type: boolean }
        hiddenFromNpcIds:
          type: array
          items: { type: string }
        location:
          type: string
          nullable: true
        notes:
          type: string
          nullable: true

    PlayerStats:
      type: object
      properties:
        money:
          type: number
          default: 0

    Player:
      type: object
      properties:
        playerId: { type: string }
        name:
          type: string
          nullable: true
        location:
          type: string
          nullable: true
        stats:
          $ref: '#/components/schemas/PlayerStats'
        wallets:
          type: array
          items: { $ref: '#/components/schemas/Balance' }

    NPC:
      type: object
      properties:
        npcId: { type: string }
        name:
          type: string
          nullable: true
        location:
          type: string
          nullable: true
        personality:
          type: array
          items: { type: string }
          nullable: true
        mood:
          type: string
          nullable: true
        relationships:
          type: array
          items: { $ref: '#/components/schemas/Relationship' }
        memories:
          type: array
          items: { $ref: '#/components/schemas/Memory' }
        knowledge:
          type: array
          items: { type: string }
        state:
          type: object
          nullable: true

    Relationship:
      type: object
      properties:
        targetId: { type: string }
        targetType:
          type: string
          enum: [npc, player]
        attitude:
          type: string
          nullable: true

    Memory:
      type: object
      properties:
        timestamp:
          type: string
          format: date-time
        summary:
          type: string
          nullable: true
        feeling:
          type: string
          nullable: true
        intensity: { type: number }

    EventInput:
      type: object
      properties:
        actor:
          $ref: '#/components/schemas/ActorRef'
        type: { type: string }
        summary: { type: string }
        details:
          type: string
          nullable: true
        feeling:
          type: string
          nullable: true
        moneyDeltas:
          type: array
          items: { $ref: '#/components/schemas/MoneyDelta' }
        inventoryDeltas:
          type: array
          items: { $ref: '#/components/schemas/InventoryDelta' }
        relationshipDeltas:
          type: array
          items: { $ref: '#/components/schemas/RelationshipDelta' }
        knowledgeScope:
          $ref: '#/components/schemas/KnowledgeScope'

    HistoryQuery:
      type: object
      properties:
        playerId:
          type: string
          nullable: true
        sceneId:
          type: string
          nullable: true
        npcIds:
          type: array
          items: { type: string }
        limit:
          type: integer
          default: 50
        sort:
          type: string
          enum: [asc, desc]
          default: "desc"

    PrecheckResult:
      type: object
      properties:
        summary: { type: string }
        logicConsistent: { type: boolean }
        knowledgeLeaksDetected: { type: boolean }
        npcIndividualityMaintained: { type: boolean }
        gmAuthorityRespected: { type: boolean }
        storyAdvancing: { type: boolean }
        errors:
          type: array
          items: { type: string }

    PrecheckLatestProposalData:
      type: object
      properties:
        characterIds:
          type: array
          items: { type: string }
        involvedNpcIds:
          type: array
          items: { type: string }
        moneyDeltas:
          type: array
          items: { $ref: '#/components/schemas/MoneyDelta' }
        inventoryDeltas:
          type: array
          items: { $ref: '#/components/schemas/InventoryDelta' }
        relationshipDeltas:
          type: array
          items: { $ref: '#/components/schemas/RelationshipDelta' }

    PrecheckLatestProposal:
      type: object
      properties:
        summary:
          type: string
          nullable: true
        data:
          $ref: '#/components/schemas/PrecheckLatestProposalData'

    PrecheckRequest:
      type: object
      properties:
        playerId:
          type: string
          nullable: true
        historyQuery:
          $ref: '#/components/schemas/HistoryQuery'
        latestProposal:
          $ref: '#/components/schemas/PrecheckLatestProposal'
        checks:
          type: array
          items:
            type: string
            enum: [logic, story, knowledge, npcIndividuality, gmAuthority, continuity]

    IntentData:
      type: object
      properties:
        summary: { type: string }
        data:
          type: object
          nullable: true

    SubmitIntentRequest:
      type: object
      required: [playerId, intent]
      properties:
        playerId: { type: string }
        intent:
          $ref: '#/components/schemas/IntentData'
        sceneId:
          type: string
          nullable: true
        metadata:
          type: object
          nullable: true

    ResolveReviewConfig:
      type: object
      properties:
        include:
          type: boolean
          default: true
        historyQuery:
          $ref: '#/components/schemas/HistoryQuery'
        checks:
          type: array
          items:
            type: string
            enum: [logic, story, knowledge, npcIndividuality, gmAuthority, continuity]

    ResolveTurnRequest:
      type: object
      required: [playerId, outcomes]
      properties:
        playerId: { type: string }
        sceneId:
          type: string
          nullable: true
        basedOnEventIds:
          type: array
          items: { type: string }
        outcomes:
          type: array
          items:
            $ref: '#/components/schemas/EventInput'
        review:
          $ref: '#/components/schemas/ResolveReviewConfig'

    Inventory:
      type: object
      properties:
        ownerType:
          type: string
          enum: [player, npc]
        ownerId: { type: string }
        items:
          type: array
          items: { $ref: '#/components/schemas/Item' }

    LoggedEvent:
      type: object
      description: Canonical record of a single narrative or mechanical event.
      properties:
        eventId:
          type: string
          nullable: true
        timestamp:
          type: string
          format: date-time
          nullable: true
        playerId:
          type: string
          nullable: true
        sceneId:
          type: string
          nullable: true
        summary: { type: string }
        detail:
          type: string
          nullable: true
        outcomes:
          type: array
          items:
            $ref: '#/components/schemas/EventInput'
        notes:
          type: string
          nullable: true

    StoryReferencesRequest:
      type: object
      required: [description]
      properties:
        description: { type: string }
        tags:
          type: array
          items: { type: string }
          nullable: true

    StoryReferenceItem:
      type: object
      properties:
        theme: { type: string }
        works:
          type: array
          items: { type: string }

    StoryReferencesResponse:
      type: object
      properties:
        references:
          type: array
          items:
            $ref: '#/components/schemas/StoryReferenceItem'

    CharacterRequest:
      type: object
      required: [name]
      properties:
        name: { type: string }
        background:
          type: string
          nullable: true
        race:
          type: string
          nullable: true

    CharacterResponse:
      type: object
      properties:
        name: { type: string }
        background:
          type: string
          nullable: true
        race:
          type: string
          nullable: true
        stats:
          type: object
          additionalProperties:
            type: integer
        hp: { type: integer }
        buffs:
          type: array
          items: { type: string }

    UpdatePlayerRequest:
      type: object
      properties:
        name:
          type: string
          nullable: true
        location:
          type: string
          nullable: true
        stats:
          $ref: '#/components/schemas/PlayerStats'
        wallets:
          type: array
          items:
            $ref: '#/components/schemas/Balance'

