# Refactor Scripts into a Production-Ready Python Package

This document outlines the detailed, step-by-step plan for refactoring the Python scripts in the `scripts/` directory into a formal, installable Python package named `gemini-gitlab-workflow`. This plan serves as a living document to track the progress of the refactoring effort.

## Guiding Principles

*   **Structural Clarity:** Adopt the industry-standard `src-layout` to cleanly separate source code from tests and configuration.
*   **Reproducibility:** Ensure a consistent development environment for all contributors using `uv` and `pyproject.toml`.
*   **Incremental Progress:** Break down the refactoring into logical, self-contained phases. Each phase will result in a stable, testable state.
*   **Automation:** Implement a CI/CD pipeline to automate testing and quality checks.
*   **Living Documentation:** Keep all project documentation synchronized with the state of the code.

---

## Phase 1: Project Structure Transformation (src-layout)

**Status:** [PLANNED]

**Goal:** Migrate the current scripts into a standard `src-layout` structure directly within the project root.

- [ ] Create a new `src` directory in the project root (`/workspaces`).
- [ ] Create a new `tests` directory in the project root.
- [ ] Create a package directory: `src/gemini_gitlab_workflow`.
- [ ] Move Python source files from `scripts/` to `src/gemini_gitlab_workflow/`.
- [ ] Create an `__init__.py` file in `src/gemini_gitlab_workflow/` to mark it as a package.
- [ ] Move test files from `scripts/tests/` to the new root `tests/` directory.
- [ ] Move `scripts/pyproject.toml` to the project root (`/workspaces/pyproject.toml`).
- [ ] Update `pyproject.toml` to reflect the new `src-layout` structure.
- [ ] Update all import paths in the source code and tests to be absolute based on the new package structure.
- [ ] Run the test suite (`uv run pytest`) to verify that all changes are working correctly.
- [ ] Document the new project structure in `docs/architecture-design-document.md`.

---

## Phase 2: Create an Installable Python Package

**Status:** [PLANNED]

**Goal:** Make the project a formal, installable Python package with a command-line entry point (`ggw`).

- [ ] Enhance `pyproject.toml` with project metadata (version, author, description).
- [ ] Define a command-line script entry point in `pyproject.toml` (e.g., `ggw = "gemini_gitlab_workflow.cli:app"`).
- [ ] Rename `gemini_cli.py` to `cli.py` for clarity.
- [ ] Create a `setup.sh` script to install the package in editable mode using `uv`.
- [ ] Test the installation and verify that the `ggw` command is available and functional.
- [ ] Update `README.md` with new installation and usage instructions.

---

## Phase 3: Implement a Centralized Configuration System

**Status:** [PLANNED]

**Goal:** Decouple configuration from the code, allowing for easier management of different environments.

- [ ] Create a `config.py` module within the `gemini_gitlab_workflow` package.
- [ ] Implement a configuration class (e.g., using Pydantic) to load settings from `.env` files and environment variables.
- [ ] Refactor the codebase to use the centralized configuration object instead of direct `os.getenv` calls.
- [ ] Adapt tests to use a dedicated test configuration.
- [ ] Document the configuration options and how to set them.

---

## Phase 4: Introduce a GitLab CI/CD Pipeline

**Status:** [PLANNED]

**Goal:** Automate testing and code quality checks on every commit.

- [ ] Create a `.gitlab-ci.yml` file in the project root.
- [ ] Define pipeline stages (e.g., `lint`, `test`).
- [ ] Create a `lint` job that runs `ruff` to check code style and quality.
- [ ] Create a `test` job that installs dependencies with `uv` and runs the full `pytest` suite.
- [ ] Document the CI/CD pipeline's purpose and operation.

---

## Phase 5: Final Documentation and Cleanup

**Status:** [PLANNED]

**Goal:** Finalize the project's documentation and remove obsolete files.

- [ ] Conduct a full review and update of all documentation (`README.md`, `docs/*.md`).
- [ ] Add comprehensive docstrings to all public modules, classes, and functions.
- [ ] Delete the old `scripts` directory and its contents.
- [ ] Write a summary of the refactoring process and outcomes in `docs/technical-design-document.md`.
