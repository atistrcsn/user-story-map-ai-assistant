import json
import os
from typing import List, Optional
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from pydantic import BaseModel, Field
from gemini_gitlab_workflow import config

# Configure the generative AI client
try:
    genai.configure(api_key=os.getenv("GEMINI_WORKER_API_KEY"))
except Exception as e:
    print(f"Error configuring Google Gemini API: {e}")
    genai = None

# --- Pydantic Schemas for Structured Output ---

class RelevantFiles(BaseModel):
    """Schema for the list of relevant files."""
    relevant_files: List[str] = Field(description="A list of file paths relevant to the user's request.")

class Dependencies(BaseModel):
    """Schema for issue dependencies."""
    is_blocked_by: Optional[List[str]] = None

class ProposedIssue(BaseModel):
    """Schema for a single proposed issue."""
    id: str = Field(description="A temporary, unique identifier for the new issue (e.g., 'NEW_1').")
    title: str = Field(description="A short, descriptive title for the issue from a user's perspective.")
    description: str = Field(description="The full Markdown description of the issue, following the user story template.")
    labels: List[str] = Field(description="A list of GitLab labels to be applied to the issue.")
    dependencies: Optional[Dependencies] = None

class ImplementationPlan(BaseModel):
    """Schema for the entire implementation plan."""
    proposed_issues: List[ProposedIssue] = Field(description="A list of all the new epics and stories to be created.")

# Define safety settings to block harmful content
safety_settings = [
    {
        "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
        "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    },
    {
        "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        "threshold": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    },
]

# --- Manual Schemas for Gemini API ---

RELEVANT_FILES_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant_files": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["relevant_files"]
}

IMPLEMENTATION_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "proposed_issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "dependencies": {
                        "type": "object",
                        "properties": {
                            "is_blocked_by": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["id", "title", "description", "labels"]
            }
        }
    },
    "required": ["proposed_issues"]
}


def call_google_gemini_api(messages: list, model_name: str, response_schema: dict) -> str:
    """Calls the Google Gemini API with a structured list of messages and a response schema."""
    if not genai:
        print("Error: Google Gemini API client is not configured.")
        return ''
    try:
        model = genai.GenerativeModel(model_name, safety_settings=safety_settings)
        config = genai.GenerationConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=response_schema,
        )
        response = model.generate_content(messages, generation_config=config)
        return response.text
    except Exception as e:
        print(f"An error occurred while calling the Gemini API: {e}")
        return None

def get_relevant_context_files(user_prompt: str, context_sources: list[dict], mock: bool = False) -> list[str] | None:
    """Uses an AI model to select the most relevant context files for a given user prompt."""
    if mock:
        print("--- AI API CALL (MOCKED for get_relevant_context_files) ---")
        return ["docs/architecture-design-document.md", "docs/feature-ai-story-map-creation.md"]

    system_prompt = "Your task is to select the most relevant context files for a new software development task."
    
    user_content = f"""
User Request: "{user_prompt}"

Available context files:
{os.linesep.join([f'- File: {s["path"]}, Description: {s["summary"]}' for s in context_sources])}
"""

    messages = [
        {'role': 'model', 'parts': [system_prompt.strip()]},
        {'role': 'user', 'parts': [user_content.strip()]}
    ]

    raw_response = call_google_gemini_api(
        messages,
        model_name=config.GEMINI_FAST_MODEL,
        response_schema=RELEVANT_FILES_SCHEMA
    )
    if raw_response is None:
        return None

    try:
        validated_response = RelevantFiles.model_validate_json(raw_response)
        return validated_response.relevant_files
    except Exception as e:
        print(f"[ERROR] Failed to validate the AI response for context files: {e}")
        return None


def generate_implementation_plan(user_prompt: str, context_content: str, existing_issues: list[dict], mock: bool = False) -> dict | None:
    """Uses a powerful AI model to generate a structured implementation plan from a business perspective."""
    if mock:
        # This mock would need to be updated to return a JSON string matching the Pydantic schema
        pass

    existing_issues_str = "\n".join(
        f"- Title: \"{issue['title']}\", Labels: {issue['labels']}, State: \"{issue.get('state', 'unknown')}\"" for issue in existing_issues
    ) if existing_issues else "N/A"

    system_prompt = f"""
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
5.  **Mandatory Description Template:** For EACH proposed issue, the `description` field MUST follow this exact Markdown template:
    ```markdown
    # {{{{title}}}}

    ### User Story

    **As a** [user type],
    **I want to** [perform some action],
    **So that** [I can achieve some goal].

    ---

    ### Acceptance Criteria
    *This list defines what must be true from the user's perspective for the story to be considered "done."

    - [ ] A criterion describing a verifiable outcome.
    - [ ] Another criterion.
    ```
6.  **Define Dependencies:** After proposing all issues, analyze them. If implementing one issue is a logical prerequisite for another, you **MUST** define this relationship. For example, if NEW_2 must be done before NEW_3, add this to NEW_3: `"dependencies": {{"is_blocked_by": ["NEW_2"]}}`.
7.  **CRITICAL DEPENDENCY RULE:** You MUST NOT propose a dependency on any issue that has a state of 'closed'. Closed issues are completed and cannot block new work. Only issues with a state of 'opened' can be considered as blockers.
8.  **LABEL INHERITANCE IS MANDATORY: All Story issues MUST inherit BOTH the `Epic::` and the `Backbone::` labels from their parent Epic, without exception.**

Generate the business-functional user story map now.
"""
    
    user_content = f"""
**User Request:** "{user_prompt}"

**Provided Context:**
---
{context_content}
---

**Already Existing Epics and Stories (Analyze these first!):**
---
{existing_issues_str}
---
"""

    messages = [
        {'role': 'model', 'parts': [system_prompt.strip()]},
        {'role': 'user', 'parts': [user_content.strip()]}
    ]

    raw_response = call_google_gemini_api(
        messages,
        model_name=config.GEMINI_SMART_MODEL,
        response_schema=IMPLEMENTATION_PLAN_SCHEMA
    )
    if raw_response is None:
        return None

    try:
        validated_plan = ImplementationPlan.model_validate_json(raw_response)
        # Return as a dictionary for compatibility with the rest of the system
        return validated_plan.model_dump(exclude_none=True)
    except Exception as e:
        print(f"[ERROR] Failed to validate the AI response for the implementation plan: {e}")
        return None
