# Netflix App Navigation Guide

- **Deep-Link & Internal Search Limitation:** Standard `am start` deep-links (`nflx://`) and internal UI searches are unreliable and often ignored by Netflix's Ninja engine.
- **The ONLY Working Workaround:** 
  Do not use direct app intents. Instead, use the **`trigger_global_search`** tool with a specifically formatted English query string:
  - Format: `"Play [Movie Title] on Netflix"` (e.g., `"Play Inception on Netflix"`).
- **Execution Flow:**
  1. Call the **`trigger_global_search`** tool with the query string containing the English movie title.
  2. If the Google TV UI lands on a confirmation card or search result tile, use the dedicated remote MCP tool for confirming/selecting to trigger actual playback.