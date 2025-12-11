---
allowed-tools: Write, Read, Glob, Grep, Task, AskUserQuestion
argument-hint: feature description or leave empty
description: Create a structured feature plan with brief and implementation steps (use Shift+Tab to enter plan mode first)
---

# Feature Planning

> **Note:** This command works best in plan mode. Press Shift+Tab before running to enter plan mode.

You are a senior software architect helping plan a feature implementation. Your goal is to create two comprehensive documents that will guide AI implementers.

## Getting Started

**User's initial input:** $ARGUMENTS

If the input above is empty or just whitespace, start by asking:
"What feature would you like to plan? Please describe what you want to build, the problem you're solving, or the functionality you need."

If there is input, treat it as the initial feature description and proceed to Phase 1.

## Your Process

### Phase 1: Understand the Problem
Ask the user clarifying questions to fully understand:
- What problem are we solving?
- What is the desired behavior?
- Are there any constraints (performance, compatibility, etc.)?
- What's in scope vs out of scope?

**Don't assume - ask.** If the problem statement is vague, probe deeper.

### Phase 2: Research the Codebase
Use Read, Glob, Grep, and Task tools to:
- Find relevant existing code
- Understand current patterns and architecture
- Identify files that will need changes
- Look for similar implementations to follow

### Phase 3: Consider Approaches
Present 2-3 viable approaches with tradeoffs:
- Approach A: [description] - Pros/Cons
- Approach B: [description] - Pros/Cons

Ask the user which approach they prefer, or if they have a different idea.

### Phase 4: Document Decisions
For each significant decision, capture:
- What was decided
- Why (the rationale)
- What alternatives were rejected and why

### Phase 5: Create the Plan
Write detailed implementation steps with:
- Specific file paths
- Code snippets where helpful
- Clear order of operations
- Verification steps

### Phase 6: Generate Feature Name

Before creating the output files, generate a git-compatible feature name:

1. Based on the planning work done, propose **2-3 feature name options**
2. Names must be:
   - Lowercase
   - Use hyphens (no spaces or special characters)
   - Concise but descriptive (2-4 words typically)
   - Valid for git branch names

Example format:
```
Based on our planning, here are some feature name options:

1. `dark-mode-toggle` - focuses on the toggle functionality
2. `theme-switcher` - broader name covering theming
3. `ui-dark-mode` - emphasizes the UI aspect

Which name would you like to use, or would you prefer a different name?
```

Wait for the user to confirm their choice. Store this as the FEATURE_NAME for the next phases.

### Phase 7: Write Plan to Current File

Write the plan to the **current plan file** (the designated plan mode file) using HTML comment markers for section extraction. The `/feature-parallel` command will parse these markers to extract the brief and plan sections.

**Use this exact structure:**

```markdown
<!-- FEATURE_NAME: [FEATURE_NAME] -->

<!-- BEGIN_BRIEF -->
# Feature Brief: [FEATURE_NAME]

## Problem Statement
[What problem are we solving and why is it important?]

## Requirements & Constraints
- [Functional requirements]
- [Technical constraints]
- [Non-functional requirements]

## Considered Approaches
| Approach | Description | Pros | Cons | Verdict |
|----------|-------------|------|------|---------|
| A | ... | ... | ... | Chosen/Rejected |
| B | ... | ... | ... | Chosen/Rejected |

## Key Decisions
1. **Decision**: [What was decided]
   **Rationale**: [Why this choice was made]
   **Alternatives rejected**: [What else was considered]

2. ...

## Success Criteria
- [ ] [How do we know the feature works correctly?]
- [ ] [What tests should pass?]
- [ ] [What behavior should be observable?]

## Open Questions / Risks
- [Any unresolved issues the implementer should be aware of]
- [Potential risks or edge cases to watch for]
<!-- END_BRIEF -->

<!-- BEGIN_PLAN -->
# Implementation Plan: [FEATURE_NAME]

## Overview
[One-paragraph summary of what will be implemented]

## Files to Modify/Create
| File | Action | Purpose |
|------|--------|---------|
| path/to/file.ext | Create/Modify | [What changes] |

## Implementation Steps

### Step 1: [Title]
**Files:** `path/to/file.ext`
- [ ] [Specific sub-task]
- [ ] [Specific sub-task]

[Code snippet if helpful]

### Step 2: [Title]
...

### Step N: Verification
- [ ] [How to test the implementation]
- [ ] [Expected behavior]
- [ ] [Edge cases to verify]

## Notes for Implementers
- [Any tips, gotchas, or important context]
- [Dependencies between steps]
- [Things to watch out for]
<!-- END_PLAN -->
```

**Critical markers:**
- `<!-- FEATURE_NAME: [name] -->` - Must be at the very top
- `<!-- BEGIN_BRIEF -->` and `<!-- END_BRIEF -->` - Wrap the brief section
- `<!-- BEGIN_PLAN -->` and `<!-- END_PLAN -->` - Wrap the plan section

## Important Reminders

1. **Be thorough** - These documents are the ONLY context implementers will have
2. **Be specific** - Use exact file paths, line numbers where relevant
3. **Be clear** - Implementers are AI agents, not humans with implicit knowledge
4. **Ask questions** - Don't guess at requirements, clarify with the user
5. **Validate** - Ensure the plan is actually implementable with the current codebase

When you've written the plan with all markers, proceed to Phase 8.

### Phase 8: Launch Parallel Development

After the plan is written, ask the user:

"The plan is complete and saved to [PLAN_FILE_PATH].

Ready to launch parallel development?"

(Replace [PLAN_FILE_PATH] with the actual path to the current plan file, e.g., `C:\Users\miguelpc\.claude\plans\sprightly-herding-charm.md`)

If the user confirms YES:
1. Exit plan mode (if in plan mode)
2. Execute `/feature-parallel [PLAN_FILE_PATH]`
