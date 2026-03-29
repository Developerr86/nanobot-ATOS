---
name: git
description: "Perform Git operations like status, add, commit, push, branch, revert, and more. Always confirm with the user before making changes."
metadata:
  nanobot:
    emoji: 📦
    requires:
      bins: ["git"]
    install:
      - id: git
        kind: brew
        formula: git
        bins: ["git"]
        label: "Install Git (brew)"
      - id: git-apt
        kind: apt
        package: git
        bins: ["git"]
        label: "Install Git (apt)"
---

# Git Skill

Use this skill to perform Git version control operations. **Only execute git commands when the user explicitly instructs you to do so.**

## Core Principles

1. **User Confirmation Required**: Before executing any git operation that modifies state (add, commit, push, revert, etc.), you MUST confirm with the user first.

2. **Commit Naming**: Before committing, ask the user if they want to:
   - Name the commit themselves
   - Let you decide on an appropriate commit message based on the changes

3. **Branch Selection**: Before pushing, always ask the user which branch they want to push to (e.g., `main`, `master`, or a feature branch).

4. **No Automatic Execution**: Never execute git commands automatically. Always wait for explicit user instruction.

## Git Operations

### Check Status
Before any operation, check the current state:
```bash
git status
```

View recent commits:
```bash
git log --oneline -10
```

View current branch:
```bash
git branch
```

### Add Changes to Staging
Stage all changes:
```bash
git add .
```

Stage specific files:
```bash
git add <file1> <file2>
```

Stage interactively:
```bash
git add -p
```

**Before staging**, inform the user what files will be staged and wait for confirmation.

### Commit Changes

**Step 1: Ask about commit message preference**
Before committing, ask the user:
> "How would you like to name this commit?
> 1. You provide a commit message
> 2. Let me (the agent) decide based on the changes"

**Step 2: If user provides message**
Use their exact message:
```bash
git commit -m "User's exact commit message"
```

**Step 3: If agent decides**
Analyze the staged changes and create a descriptive commit message:
```bash
git commit -m "<type>: <subject>"

# Examples:
# feat: add user authentication system
# fix: resolve null pointer in user service
# docs: update README with installation steps
# refactor: simplify channel routing logic
# test: add unit tests for memory module
```

### Push to Remote

**Before pushing**, always ask:
> "Which branch would you like to push to?"
> - main (default)
> - master
> - A feature branch (specify name)
> - Current branch name

Then push:
```bash
git push origin <branch-name>
```

Or with upstream:
```bash
git push -u origin <branch-name>
```

### Create Branch
```bash
git checkout -b <branch-name>
git push -u origin <branch-name>
```

### Pull Latest Changes
```bash
git pull origin <branch-name>
```

### Revert Changes

Revert last commit (keeps changes in working directory):
```bash
git reset --soft HEAD~1
```

Revert last commit (discards changes):
```bash
git reset --hard HEAD~1
```

Revert a specific commit:
```bash
git revert <commit-hash>
```

**Always warn the user before any revert operation and explain the consequences.**

### View Diff
```bash
git diff           # Unstaged changes
git diff --staged  # Staged changes
git diff HEAD      # All changes
```

## Interaction Flow

### For Commit Operations:
1. User says: "commit the changes" or similar
2. You: Check `git status` and show what will be committed
3. You: Ask "Would you like to name this commit, or should I decide?"
4. User: Provides preference
5. You: If user wants to name it, ask "What commit message would you like?"
6. You: If agent decides, propose a message and ask for confirmation
7. You: Execute `git commit` with the agreed message

### For Push Operations:
1. User says: "push the changes" or similar
2. You: Ask "Which branch would you like to push to? (main/master/feature-branch)"
3. User: Specifies branch
4. You: Confirm "Pushing to origin/<branch-name>. Continue?"
5. User: Confirms
6. You: Execute `git push`

### Complete Workflow Example:
```\nUser: "Commit and push my changes"\n\nAgent: "Let me first check what changes we have:\n[Shows git status output]\n\nBefore I commit, would you like to:\n1. Name the commit yourself\n2. Let me decide on a commit message based on the changes"\n\nUser: "You decide"\n\nAgent: "Based on the changes, I suggest: 'feat: add user authentication module'\nDoes this look good, or would you like to modify it?\n\nAlso, which branch would you like to push to? (main/master/feature branch)"\n\nUser: "Looks good, push to main"\n\nAgent: "To confirm:\n- Commit message: 'feat: add user authentication module'\n- Push to: origin/main\n\nProceed? [yes/no]"