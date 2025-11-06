## Feature: AI-Assisted Story Map Creation - Detailed Understanding

This document captures the Gemini AI agent's detailed understanding of the "AI-Assisted Story Map Creation" feature, based on the `docs/backlog.md` and subsequent discussions. It serves as an internal specification for implementation.

### Core Purpose

The primary goal of this feature is to transform high-level business ideas (e.g., "users should have profile pictures") into structured, actionable development tasks within GitLab. The AI acts as a proactive, context-aware planning partner, leveraging the project's entire knowledge base (code, documentation, existing issues) to propose and facilitate the creation of new Epics, Stories, and their dependencies.

The process is interactive, with the AI performing analysis and proposing solutions, while the user retains ultimate control and decision-making authority.

### Enhanced End-to-End Workflow (Optimized Plan) - Gemini's Interpretation

**1. Smart Sync (Intelligent Synchronization)**
*   **Státusz:** `[KÉSZ]`
*   **Understanding:** This step ensures the AI always works with the most current project data without incurring long waiting times. Instead of a full re-download of all GitLab issues, the system performs a quick check of `updated_at` timestamps. Only issues whose timestamps have changed since the last sync (as recorded in a local cache, `/.gemini_cache/`) are fully downloaded.
*   **Importance:** Guarantees a responsive user experience and efficient use of API resources.

**2. User Input**
*   **Státusz:** `[KÉSZ]`
*   **Understanding:** The user initiates the process by providing a high-level concept, feature request, or business requirement in natural language.
*   **Importance:** This is the starting trigger for the entire planning workflow.

**3. Two-Phase AI Analysis (Context-Aware)**
*   **Státusz:** `[KÉSZ]`
*   **Understanding:** This strategy addresses the challenge of managing large project contexts and LLM token limits, ensuring scalability and accuracy.
    *   **Phase 1 (Pre-filtering):** A smaller, faster LLM is used to intelligently filter the vast amount of project documentation and existing issues. It receives the user's request and a list of all available documents/issues (typically with their titles and auto-generated summaries). Its task is to identify and return a list of the 10-15 most relevant files/issues.
    *   **Phase 2 (Deep Analysis):** The primary, more powerful LLM then performs a detailed analysis, but only on the pre-filtered, highly relevant subset of documents. This focused context allows for more accurate and efficient reasoning.
*   **Importance:** Prevents LLM context window overflows, reduces computational cost, and improves the precision of the AI's analysis by focusing on pertinent information.

**4. Structured Dialogue (User Confirmation)**
*   **Státusz:** `[KÉSZ]`
*   **Understanding:** The AI engages in an interactive, step-by-step conversation with the user. Instead of presenting a monolithic plan, it breaks down its proposals into logical chunks (e.g., task decomposition, hierarchical placement, dependency suggestions) and seeks explicit user confirmation or modification at each stage.
*   **Importance:** Enhances user control, makes the planning process transparent, reduces cognitive load on the user, and minimizes the chance of errors or misunderstandings.

**5. Local Generation**
*   **Státusz:** `[KÉSZ]`
*   **Understanding:** Once the user has approved the AI's proposals through the structured dialogue, the system generates the corresponding artifacts locally. This involves creating new Markdown files for Epics/Stories in the `gitlab_data` directory (following the agreed-upon template) and updating the `project_map.yaml` with new nodes and links representing the issues and their dependencies.
*   **Importance:** Provides a local, reviewable representation of the planned changes before any modifications are pushed to the remote GitLab instance, acting as a crucial staging step.

**6. Robust Upload to GitLab**
*   **Státusz:** `[FÜGGŐBEN]` - **Valós implementáció megkezdése**
*   **Understanding:** This is the final, critical phase where local changes are propagated to the remote GitLab server. This process is designed for reliability and data integrity.
    *   **Ordered Execution:** Changes are applied in a strict sequence: 1) Create any new labels required by the new issues. 2) Create the new issues themselves, capturing their GitLab IIDs. 3) Add dependency comments (`/blocks #<IID>` or `/blocked_by #<IID>`) to the relevant issues, using the newly obtained IIDs.
    *   **API Throttling:** Small, controlled delays are introduced between API calls to prevent hitting GitLab's rate limits and ensure smooth operation.
    *   **Transactional Logic & Rollback:** The system logs its intended actions. In case of any failure during the upload process (e.g., network error, API rejection), it attempts to roll back any changes already successfully made (e.g., delete partially created issues) to leave the GitLab project in a consistent, clean state. If a full rollback isn't feasible, it provides a clear report of partial success for manual intervention.
*   **Importance:** Ensures that the GitLab project remains consistent and uncorrupted, even in the face of errors, and that all new entities are correctly linked and represented on the remote server.