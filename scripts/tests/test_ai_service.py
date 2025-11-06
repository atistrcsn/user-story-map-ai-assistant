import pytest
from unittest.mock import patch, MagicMock

from ai_service import get_relevant_context_files, generate_implementation_plan

class TestAIService:

    @patch('google.generativeai.GenerativeModel.generate_content')
    def test_get_relevant_context_files(self, mock_generate_content):
        # Arrange
        user_prompt = "Implement a new user profile page"
        context_sources = [
            {"path": "docs/architecture-design-document.md", "summary": "Describes the overall system architecture."},
            {"path": "gitlab_data/backbones/user-access/epics/profile-management.md", "summary": "Epic for user profile features."},
            {"path": "gitlab_data/backbones/core-functionality/epics/user-authentication.md", "summary": "Epic for login and registration."},
            {"path": "README.md", "summary": "Project overview."}
        ]

        # Mock the return value from the AI API
        mock_api_response = '["gitlab_data/backbones/user-access/epics/profile-management.md", "docs/architecture-design-document.md"]'
        mock_response_object = MagicMock()
        mock_response_object.text = mock_api_response
        mock_generate_content.return_value = mock_response_object

        # Act
        relevant_files = get_relevant_context_files(user_prompt, context_sources)

        # Assert
        # 1. Check if the API was called
        mock_generate_content.assert_called_once()
        
        # 2. Check if the prompt was constructed correctly (simplified check)
        call_args, _ = mock_generate_content.call_args
        prompt_sent_to_api = call_args[0]
        assert user_prompt in prompt_sent_to_api
        assert "docs/architecture-design-document.md" in prompt_sent_to_api
        assert "Epic for login and registration." in prompt_sent_to_api

        # 3. Check if the response was parsed correctly
        assert isinstance(relevant_files, list)
        assert len(relevant_files) == 2
        assert "gitlab_data/backbones/user-access/epics/profile-management.md" in relevant_files
        assert "docs/architecture-design-document.md" in relevant_files
        assert "README.md" not in relevant_files

    @patch('google.generativeai.GenerativeModel.generate_content')
    def test_generate_implementation_plan(self, mock_generate_content):
        # Arrange
        user_prompt = "Create a feature for users to upload a profile picture."
        context_content = """
---
File: docs/architecture-design-document.md
Content: The system uses a microservices architecture. User data is stored in a Postgres database.
---
File: gitlab_data/backbones/user-access/epics/profile-management.md
Content: This epic covers all features related to user profiles.
"""
        mock_api_response = """
        {
          "proposed_issues": [
            {
              "id": "NEW_1",
              "title": "Story: Upload Profile Picture",
              "description": "As a user, I can upload a JPG or PNG file to serve as my profile picture.",
              "labels": ["Type::Story", "Backbone::User-Access"],
              "dependencies": {"blocks": ["NEW_2"]}
            },
            {
              "id": "NEW_2",
              "title": "Task: Create API endpoint for upload",
              "description": "Develop a POST endpoint at /api/users/me/avatar.",
              "labels": ["Type::Task"]
            }
          ]
        }
        """
        mock_response_object = MagicMock()
        mock_response_object.text = mock_api_response
        mock_generate_content.return_value = mock_response_object

        # Act
        plan = generate_implementation_plan(user_prompt, context_content, [])

        # Assert
        mock_generate_content.assert_called_once()
        call_args, _ = mock_generate_content.call_args
        prompt_sent_to_api = call_args[0]
        assert user_prompt in prompt_sent_to_api
        assert "The system uses a microservices architecture" in prompt_sent_to_api

        assert isinstance(plan, dict)
        assert "proposed_issues" in plan
        issues = plan["proposed_issues"]
        assert len(issues) == 2
        assert issues[0]["id"] == "NEW_1"
        assert issues[0]["title"] == "Story: Upload Profile Picture"
        assert issues[1]["labels"] == ["Type::Task"]
        assert issues[0]["dependencies"]["blocks"] == ["NEW_2"]

