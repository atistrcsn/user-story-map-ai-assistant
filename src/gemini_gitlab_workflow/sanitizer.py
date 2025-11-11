import os

class Sanitizer:
    def __init__(self):
        self.GGW_GITLAB_URL = os.environ.get("GGW_GITLAB_URL", "[PROJECT_URL]")
        self.GGW_GITLAB_PROJECT_ID = os.environ.get("GGW_GITLAB_PROJECT_ID", "[PROJECT_ID]")

    def anonymize_text(self, text: str) -> str:
        """Replaces project-specific identifiers with generic placeholders."""
        text = text.replace(self.GGW_GITLAB_URL, "[PROJECT_URL]")
        text = text.replace(self.GGW_GITLAB_PROJECT_ID, "[PROJECT_ID]")
        return text

    def deanonymize_text(self, text: str) -> str:
        """Restores project-specific identifiers from generic placeholders."""
        text = text.replace("[PROJECT_URL]", self.GGW_GITLAB_URL)
        text = text.replace("[PROJECT_ID]", self.GGW_GITLAB_PROJECT_ID)
        return text