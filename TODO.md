# TODO — SafeChoice AI upgrades

## Step 1 — Emergency detection + escalation (most essential)
- [ ] Add `detect_emergency_symptoms(message)` in `chatbot/views.py`
- [ ] Add `build_emergency_response(...)` that:
  - [ ] Detects symptom category
  - [ ] Returns medical disclaimer + immediate care instruction
  - [ ] Optionally includes nearest facilities if lat/lon available
- [ ] Ensure emergency path bypasses LLM and is returned immediately
- [ ] Add small, non-intrusive disclaimer to non-emergency responses

## Step 2 — Personalized recommendation engine
- [ ] Add session-based structured profile fields (age range, goal, hormone preference, relationship/sti concern)
- [ ] Add parsing for user answers (regex/keyword extraction) in `chatbot/views.py`
- [ ] Add `rank_methods(profile, candidate_methods)` using:
  - [ ] suitability/advantages keywords
  - [ ] side-effect considerations (simple compatibility)
  - [ ] goal (short vs long-term)
- [ ] Update recommendation handler to:
  - [ ] Ask missing questions when profile incomplete
  - [ ] Otherwise return ranked methods + explanation grounded in DB snippets

## Step 3 — LLM prompt contract fixes (supporting)
- [ ] Fix `chatbot/groq_ai.py` to actually include history or remove unused parameter

## Step 4 — Tests / run
- [ ] Run Django migrations if models changed
- [ ] Run `python manage.py test`
- [ ] Manually test chat flows: emergency / recommendation / facilities

