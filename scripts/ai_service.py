import json
import os
import re
import google.generativeai as genai

# Configure the generative AI client
try:
    genai.configure(api_key=os.getenv("GEMINI_WORKER_API_KEY"))
except Exception as e:
    print(f"Error configuring Google Gemini API: {e}")
    genai = None

def _extract_json_from_response(text: str) -> str:
    """Extracts a JSON object or array from a string, ignoring Markdown fences."""
    # Find the start of the JSON (either { or [)
    match = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if match:
        return match.group(0)
    return "" # Return empty string if no JSON found

def call_google_gemini_api(prompt: str) -> str:
    """Calls the Google Gemini API with a given prompt."""
    if not genai:
        print("Error: Google Gemini API client is not configured.")
        return ''
    try:
        model = genai.GenerativeModel('gemini-2.5-pro')
        config = genai.GenerationConfig(temperature=0)
        response = model.generate_content(prompt, generation_config=config)
        return response.text
    except Exception as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        raise

def get_relevant_context_files(user_prompt: str, context_sources: list[dict], mock: bool = False) -> list[str]:
    """Uses an AI model to select the most relevant context files for a given user prompt."""
    if mock:
        print("--- AI API CALL (MOCKED for get_relevant_context_files) ---")
        return ["docs/architecture-design-document.md", "docs/feature-ai-story-map-creation.md"]

    # ... (prompt construction remains the same)
    prompt = f"""
CRITICAL: Your response must be ONLY a raw JSON list of strings, without any Markdown formatting or other text.

Feladat: Válaszd ki a legrelevánsabb kontextus fájlokat egy új szoftverfejlesztési feladathoz.
Például: ["docs/architecture.md", "gitlab_data/.../issue-101.md"]

Felhasználói kérés: "{user_prompt}"

Választható kontextus fájlok:
{os.linesep.join([f'{i}. Fájl: {s["path"]}, Leírás: {s["summary"]}' for i, s in enumerate(context_sources, 1)])}
"""

    raw_response = call_google_gemini_api(prompt.strip())
    json_str = _extract_json_from_response(raw_response)
    if not json_str:
        return []
    relevant_files = json.loads(json_str)
    if not isinstance(relevant_files, list):
        return []
    return relevant_files

def generate_implementation_plan(user_prompt: str, context_content: str, existing_issues: list[dict], mock: bool = False) -> dict:
    """Uses a powerful AI model to generate a structured implementation plan from a business perspective."""
    if mock:
        # Mock response updated to reflect the new persona and template
        # ... (omitted for brevity)
        pass

    existing_issues_str = "\n".join(
        f"- Title: \"{issue['title']}\", Labels: {issue['labels']}" for issue in existing_issues
    ) if existing_issues else "N/A"

    prompt = f"""
You are a **Product Owner**. Your primary role is to translate high-level business requirements into clear, functional user stories.

**CRITICAL CONTEXT:**
- **Audience:** Your output is for business stakeholders. It MUST be 100% free of technical jargon (NO APIs, databases, etc.).
- **Focus:** Focus exclusively on the **user's perspective** and functional value.

**YOUR TASK:**
Based on the "User Request", create a plan of user stories. Before you begin, carefully analyze the "Already Existing Epics and Stories".

**CRITICAL RULES FOR YOUR RESPONSE:**
1.  **Decision Framework:** Your first task is to decide if the user's request belongs to an existing Epic or requires a new one.
    a.  Review the 'Already Existing Epics'. If one provides a **strong and direct logical match** for the entire request, you must use it.
    b.  If no strong match exists, you **MUST create a new, single, appropriate Epic** that encapsulates the user's request.
2.  **Epic Creation Rule:** If you create a new Epic, it **MUST** be the first item in the `proposed_issues` list. It must not have a `Type::Story` label. Crucially, it **MUST** also have a label in the format `Epic::[Epic Title]`, where `[Epic Title]` is the same as the issue's title. All subsequent Story issues must then belong to this new Epic.
3.  **Hierarchy Enforcement:** You must follow a strict, flat hierarchy. An Epic can only be a child of a Backbone. A Story can only be a child of an Epic. **You are strictly forbidden from creating an Epic that is a child of another Epic.**
4.  **Analyze Existing Issues:** Do not create duplicate stories. If a functional story already covers part of the request, do not create it again. If the existing plan is sufficient, return an empty list for "proposed_issues".
5.  **JSON-Only Output:** Your entire response MUST be a single, valid, raw JSON object.
6.  **Mandatory Description Template:** For EACH proposed issue, the `description` field MUST follow this exact Markdown template:
    ```markdown
    # {{{{title}}}}

    ### User Story

    **As a** [user type],
    **I want to** [perform some action],
    **So that** [I can achieve some goal].

    ---

    ### Acceptance Criteria
    *This list defines what must be true from the user's perspective for the story to be considered "done."*

    - [ ] A criterion describing a verifiable outcome.
    - [ ] Another criterion.
    ```
7.  **JSON Structure for Each Issue:**
    - "id": A temporary, unique identifier (e.g., "NEW_1").
    - "title": A short, descriptive title from the user's perspective. No prefixes like 'Story:'.
    - "description": The full Markdown text from the template above.
    - "labels": A list of GitLab labels (e.g., `Type::Story`, `Epic::...`, `Backbone::...`).
    - "dependencies": An optional object for functional dependencies.
8.  **Define Dependencies:** After proposing all issues, analyze them. If implementing one issue is a logical prerequisite for another, you **MUST** define this relationship. For example, if NEW_2 must be done before NEW_3, add this to NEW_3: `"dependencies": {"is_blocked_by": ["NEW_2"]}`.

**User Request:** "{user_prompt}"

**Provided Context:**
---
{context_content}
---

**Already Existing Epics and Stories (Analyze these first!):**
---
{existing_issues_str}
---

**LABEL INHERITANCE IS MANDATORY: All Story issues MUST inherit BOTH the `Epic::` and the `Backbone::` labels from their parent Epic, without exception.**

Generate the business-functional user story map now.
"""

    raw_response = call_google_gemini_api(prompt.strip())
    json_str = _extract_json_from_response(raw_response)
    if not json_str:
        return {"proposed_issues": []}
    plan = json.loads(json_str)
    if not isinstance(plan, dict) or "proposed_issues" not in plan:
        return {"proposed_issues": []}
    return plan
