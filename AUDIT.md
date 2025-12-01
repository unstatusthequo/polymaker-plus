# Codebase Audit

## Summary
Follow-up review of the updated codebase focusing on runtime stability and data consistency. The issues below were identified and mitigated in this iteration.

## Findings & Mitigations
1. **Price changes before a book snapshot leave the order book uninitialized**: `process_price_change` assumed `global_state.all_data[asset]` existed and would crash if a `price_change` arrived first. The handler now bails out when no snapshot is present and only mutates the book when the matching `asset_id` is loaded.
2. **Market refresh fails silently when sheets are empty**: `update_markets` iterated over `global_state.df` even when `get_sheet_df` returned an empty frame, leading to `NoneType` errors. The refresh now returns early with a log message unless it has either new sheet rows or a cached dataframe.
3. **User websocket emitted misleading warnings**: A dangling `else` in `process_user_data` always logged "not in" even for valid tokens. The warning now fires only when a specific row references an unknown token and the message now clarifies the missing token mapping.
4. **Position and order refresh could crash on empty responses**: Defensive checks now skip updates when the client returns no rows rather than attempting to iterate `None` or empty frames, keeping background refresh loops alive.
