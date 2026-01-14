"""
Agent Runner

Executes individual agents by:
1. Loading agent prompts from disk
2. Assembling context
3. Calling LLM API
4. Returning structured output
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from .llm_client import LLMClient


class AgentRunner:
    """Runs individual agents from prompts."""

    def __init__(
        self,
        prompts_dir: str,
        agents_config_path: str,
        llm_client: Optional[LLMClient] = None,
    ):
        """Initialize agent runner.

        Args:
            prompts_dir: Directory containing agent prompt files
            agents_config_path: Path to agents.yaml configuration
            llm_client: LLM client instance (creates default if None)
        """
        self.prompts_dir = Path(prompts_dir)
        self.agents_config_path = Path(agents_config_path)
        self.llm_client = llm_client or LLMClient()

        # Load agents configuration
        with open(self.agents_config_path, 'r') as f:
            config = yaml.safe_load(f)
            self.agents_config = config.get('agents', {})

    def load_prompt(self, agent_id: str) -> str:
        """Load agent prompt from file.

        Args:
            agent_id: Agent identifier (e.g., 'requirements_gatherer')

        Returns:
            Full prompt text

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        # Get prompt file path from config
        agent_config = self.agents_config.get(agent_id)
        if not agent_config:
            raise ValueError(f"Agent '{agent_id}' not found in configuration")

        prompt_file = agent_config.get('prompt_file')
        if not prompt_file:
            # Try default naming convention
            prompt_file = f"{agent_id}.md"

        # Resolve path (handle both absolute and relative)
        if prompt_file.startswith('/agents/'):
            # Path starting with /agents/ is relative to project root
            # Strip the leading /agents/ and use prompts_dir
            relative_path = prompt_file.replace('/agents/prompts/', '')
            prompt_path = self.prompts_dir / relative_path
        elif prompt_file.startswith('/'):
            # Absolute path from project root
            prompt_path = Path(os.getcwd()) / prompt_file.lstrip('/')
        else:
            prompt_path = self.prompts_dir / prompt_file

        # If file doesn't exist, try converting hyphens to underscores
        if not prompt_path.exists():
            # Try underscore version (e.g., requirements-gatherer.md -> requirements_gatherer.md)
            alternate_name = prompt_path.name.replace('-', '_')
            alternate_path = prompt_path.parent / alternate_name
            if alternate_path.exists():
                prompt_path = alternate_path
            else:
                raise FileNotFoundError(f"Prompt file not found: {prompt_path} (also tried {alternate_path})")

        with open(prompt_path, 'r') as f:
            return f.read()

    def run_agent(
        self,
        agent_id: str,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run an agent with given input and context.

        Args:
            agent_id: Agent to run (e.g., 'requirements_gatherer')
            user_input: User message/task for the agent
            context: Optional context dictionary (for future use)
            max_tokens: Override max tokens for response

        Returns:
            Dict with:
                - agent_id: Agent that ran
                - content: Agent's response
                - usage: Token usage stats
                - prompt_tokens: Estimated input tokens
                - model: Model used
        """
        # Load agent prompt (system prompt)
        system_prompt = self.load_prompt(agent_id)

        # For MVP: simple context assembly
        # Future: integrate with context_manager for full context assembly
        user_message = self._assemble_user_message(user_input, context)

        # Execute via LLM
        response = self.llm_client.create_message_with_retry(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
        )

        # Estimate prompt tokens (system + user)
        prompt_tokens = self.llm_client.estimate_tokens(system_prompt + user_message)

        return {
            "agent_id": agent_id,
            "content": response["content"],
            "usage": response["usage"],
            "prompt_tokens": prompt_tokens,
            "model": response["model"],
            "stop_reason": response["stop_reason"],
        }

    def _assemble_user_message(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Assemble user message with context.

        For MVP: simple concatenation.
        Future: sophisticated context assembly via context_manager.

        Args:
            user_input: User's task/input
            context: Optional context dictionary

        Returns:
            Formatted user message
        """
        if not context:
            return user_input

        # Build context section
        context_parts = []

        if 'project_name' in context:
            context_parts.append(f"Project: {context['project_name']}")

        if 'current_sprint' in context:
            context_parts.append(f"Sprint: {context['current_sprint']}")

        if 'artifacts' in context:
            context_parts.append("\n## Available Artifacts\n")
            for artifact in context['artifacts']:
                context_parts.append(f"- {artifact}")

        # Combine context + user input
        if context_parts:
            context_section = "## Context\n\n" + "\n".join(context_parts)
            return f"{context_section}\n\n## Task\n\n{user_input}"
        else:
            return user_input

    def get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        """Get agent configuration.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent configuration dict

        Raises:
            ValueError: If agent not found
        """
        config = self.agents_config.get(agent_id)
        if not config:
            raise ValueError(f"Agent '{agent_id}' not found in configuration")
        return config
