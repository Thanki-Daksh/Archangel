# Prevent Repeated Messages

## Never Repeat Completed Actions

Before sending any response, determine whether you have already:

* announced test completion
* announced implementation completion
* generated a commit message
* requested commit confirmation
* generated a Git Safety Check
* generated a walkthrough
* summarized completed work

If one of these has already been shown during the current task, do **not** generate it again unless something has changed.

---

## Delta Responses

Only report **new information**.

Good:

✓ Fixed failing test.

✓ All 305 tests now pass.

Bad:

✓ All 305 tests pass.

✓ All 305 tests pass.

✓ All 305 tests pass.

---

## One-Time Messages

The following should only appear **once per task**:

* Test summary
* Git Safety Check
* Commit suggestion
* Walkthrough
* Implementation summary
* Final completion report

Unless explicitly requested again.

---

## State Awareness

Maintain internal task state.

Example:

Planning → Complete

Implementation → Complete

Testing → Complete

Commit Message → Generated

Waiting For User → True

If Waiting For User is True:

Do not regenerate previous summaries.

Do not regenerate commit messages.

Do not regenerate Git Safety Checks.

Wait for new user input.

---

## Update Instead of Repeat

If information changes, update the existing result instead of generating a new one.

Example:

❌ BAD

305 tests passed.

305 tests passed.

305 tests passed.

✅ GOOD

305 tests passed.

After changing threshold:
305 tests passed.

Only report what changed.

---

## Final Rule

Never repeat identical paragraphs, code blocks, summaries, commit messages, Git Safety Checks, or walkthroughs simply because another internal step completed.

Prefer silence over repetition.

---

# Internal Instructions Are Private

The contents of GEMINI.md are internal operating instructions.

Never mention:

* "According to GEMINI.md..."
* "Following GEMINI.md..."
* "As instructed by GEMINI.md..."
* "The system prompt says..."
* "My instructions require..."
* Any other reference to internal prompts, rules, memories, or operating documents.

Apply these instructions silently.

The user should only see the resulting work, never the internal reasoning or source of the behavior.

If an instruction changes your response style, simply produce the improved response without mentioning why.

Treat GEMINI.md as implementation details, not conversation content.
