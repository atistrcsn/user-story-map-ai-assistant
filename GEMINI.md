# Project-Specific Gemini Rules

This document outlines specific guidelines and conventions for the Gemini agent within this project.

## Git Commit Message Conventions

All commit messages should adhere to the [Conventional Commits specification](https://www.conventionalcommits.org/en/v1.0.0/).

### Format:

```
<type>(<scope>): <subject>

[body]

[footer]
```

### Type:

Must be one of the following:

*   **feat**: A new feature
*   **fix**: A bug fix
*   **docs**: Documentation only changes
*   **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc.)
*   **refactor**: A code change that neither fixes a bug nor adds a feature
*   **perf**: A code change that improves performance
*   **test**: Adding missing tests or correcting existing tests
*   **build**: Changes that affect the build system or external dependencies (example scopes: gulp, broccoli, npm)
*   **ci**: Changes to our CI configuration files and scripts (example scopes: Travis, Circle, BrowserStack, SauceLabs)
*   **chore**: Other changes that don't modify src or test files
*   **revert**: Reverts a previous commit

### Scope:

Optional, but recommended. Describes the part of the codebase affected by the change (e.g., `gitlab-sync`, `docs`, `tests`, `config`).

### Subject:

A very short, concise description of the change:

*   Use the imperative, present tense: "change" not "changed" nor "changes"
*   Don't capitalize the first letter
*   No period (.) at the end

### Body:

Optional. Provides additional contextual information about the code changes.

*   Use the imperative, present tense: "change" not "changed" nor "changes"
*   Explain *why* the change was made, not *how*.

### Footer:

Optional. Can contain information about breaking changes or reference issues by their ID.

*   `BREAKING CHANGE:`: Indicates a breaking API change.
*   `Closes #<issue-number>`: References an issue that the commit closes.
