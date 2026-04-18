"""
Agent 2: Post Formatter
Transforms a structured outline into a polished, viral LinkedIn post.
Replicates the "Format LinkedIn Post" node from the n8n workflow.
"""

import logging

from ..config.prompts import POST_FORMATTER_PROMPT
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class PostFormatterAgent:
    """
    Post Formatter Agent — Takes a structured outline and transforms
    it into a polished, publication-ready LinkedIn post.
    """

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = ""):
        self.agent = BaseAgent(
            name="PostFormatter",
            role="LinkedIn copywriter who creates viral, authority-building posts",
            system_prompt="You are a LinkedIn copywriter who transforms structured outlines into viral, authority-building posts. Write like a founder sharing hard-won lessons.",
            model=model,
            api_key=api_key,
            temperature=0.7,
        )

    def format_post(self, outline: str) -> str:
        """
        Transform a structured outline into a final LinkedIn post.
        
        Args:
            outline: The structured outline from the Content Strategist
            
        Returns:
            Final polished LinkedIn post text ready for publishing
        """
        logger.info("✨ Formatting LinkedIn post from outline...")

        # Format the prompt with the outline
        prompt = POST_FORMATTER_PROMPT.format(outline=outline)

        final_post = self.agent.run(prompt)

        # Clean up any potential formatting artifacts
        final_post = final_post.strip()

        # Remove any wrapping quotes if the model adds them
        if final_post.startswith('"') and final_post.endswith('"'):
            final_post = final_post[1:-1]

        logger.info(f"✅ Post formatted ({len(final_post)} chars)")
        return final_post
