# Stabilization Plan

Based on Oracle analysis, the refactor is sound but needs stabilization. The original monolith had bugs and tight coupling - continuing with the refactor is the right path.

## Phase 1: Make Module Importable (Quick Win) ✅

- [x] Move PIL/pytesseract imports inside `main()` function
- [x] Add `if __name__ == "__main__"` guard
- [x] Remove unused imports (`string`, `custom_ord`)
- [x] Fix type hints (`-> (str, str, list[str])` → `-> tuple[str, str, list[str]]`)
- [x] Fix `get_potential_targets` return type (returns map iterator, should return list)

**Goal**: Tests can import modules without crashing on missing dependencies ✅

**Status**: Core module imports successfully! Remaining test failures are due to removed `src.message.Message` class and missing globals, not import crashes.

## Phase 2: Fix Parsing & Data Safety (Critical) ✅

- [x] Make `process_text` robust - handle missing sender/receiver gracefully
- [x] Return `Optional[str]` for sender/receiver instead of crashing on `None`
- [x] Guard frequency updates with `if receiver:` and `if sender:` checks
- [x] Avoid variable shadowing (`is_clear_text` function vs variable)

**Goal**: No crashes on malformed input, clean data persistence ✅

**Status**: `process_text` now safely handles missing sender/receiver without crashes. Frequency updates are guarded against None values. Variable shadowing eliminated.

## Phase 3: Restore Missing Functionality (Feature Parity) ✅

- [x] Reintroduce `seen_messages` tracking with `AppendOnlyFileBackedSet`
- [x] Add duplicate message detection
- [x] Restore persistence after cipher suggestions
- [x] Handle partial code cases (when diff length < GROUP_COUNT)

**Goal**: Feature parity with original, no duplicate processing ✅

**Status**: All missing functionality restored! Users can now avoid reprocessing duplicate messages, and the system properly tracks seen messages with optional persistence after successful cipher decoding. Partial codes are clearly identified to users.

## Phase 4: Polish & Test (Quality)

- [ ] Write unit tests for `process_text`
- [ ] Write unit tests for `is_clear_text`
- [ ] Write unit tests for `get_potential_targets`
- [ ] Write unit tests for `src.crack` functions
- [ ] Consider replacing `inflect` with simple ordinal helper to reduce dependencies

**Goal**: Well-tested, minimal dependencies

## Known Issues Fixed by Refactor

✅ **Bug Fix**: Original `get_potential_targets` had `len(word) == len(word)` instead of `len(word) == len(target_word)`
✅ **Architecture**: Better separation of CLI, crypto, and parsing logic
✅ **Testability**: Logic extracted to pure functions in modules

## Estimated Effort

- Phase 1: ~1-2 hours (immediate test fixes)
- Phase 2: ~2-3 hours (critical stability)
- Phase 3: ~3-4 hours (feature restoration)
- Phase 4: ~4-6 hours (testing & polish)

**Total**: 0.5-1.5 days (matches Oracle estimate)
