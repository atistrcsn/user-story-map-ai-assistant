import json

# This is a placeholder for the actual API call.
# In a real scenario, this would interact with a library like google.generativeai.
def call_google_gemini_api(prompt: str) -> str:
    """Placeholder function for calling the Google Gemini API."""
    # This function will be mocked in tests, so its actual implementation
    # is not critical for the TDD cycle at this stage.
    print("--- AI API CALL (MOCKED) ---")
    print(prompt)
    print("----------------------------")
    # In a real implementation, we would handle API errors, retries, etc.
    return '[]' # Return empty JSON array by default

def get_relevant_context_files(user_prompt: str, context_sources: list[dict]) -> list[str]:
    """
    Uses an AI model to select the most relevant context files for a given user prompt.

    Args:
        user_prompt: The user's high-level feature request.
        context_sources: A list of dictionaries, where each dictionary represents a
                         potential context file (e.g., {"path": "...", "summary": "..."}).

    Returns:
        A list of file paths deemed most relevant by the AI.
    """
    context_lines = []
    for i, source in enumerate(context_sources, 1):
        context_lines.append(f'{i}. Fájl: {source["path"]}, Leírás: {source["summary"]}')
    
    context_string = "\n".join(context_lines)

    prompt = f"""
Feladat: Válaszd ki a legrelevánsabb kontextus fájlokat egy új szoftverfejlesztési feladathoz.
A válaszod egy JSON lista legyen, ami csak a legrelevánsabb fájlok elérési útját tartalmazza.
Például: ["docs/architecture.md", "gitlab_data/.../issue-101.md"]

Felhasználói kérés: "{user_prompt}"

Választható kontextus fájlok:
{context_string}
"""

    try:
        response_str = call_google_gemini_api(prompt.strip())
        relevant_files = json.loads(response_str)
        if not isinstance(relevant_files, list):
            # Handle cases where the AI returns a non-list object
            return []
        return relevant_files
    except (json.JSONDecodeError, TypeError):
        # Handle cases where the AI response is not valid JSON
        return []
