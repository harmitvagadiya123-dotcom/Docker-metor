"""
Agent 1: Content Strategist
Generates a structured LinkedIn post outline from raw inputs.
Replicates the "Generate Outline" node from the n8n workflow.
"""

import logging

from ..config.prompts import CONTENT_STRATEGIST_PROMPT
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ContentStrategistAgent:
    """
    Content Strategist Agent — Takes story input, industry context,
    problem, audience, and result to generate a structured LinkedIn
    authority-building post outline.
    """

    def __init__(self, model: str = "gpt-4o-mini", api_key: str = ""):
        self.agent = BaseAgent(
            name="ContentStrategist",
            role="LinkedIn Content Strategist specializing in founder-style authority posts",
            system_prompt="You are a LinkedIn content strategist specializing in founder-style authority posts for industrial businesses.",
            model=model,
            api_key=api_key,
            temperature=0.7,
        )

    def generate_outline(
        self,
        story_input: str,
        industry: str,
        problem: str,
        audience: str,
        result: str = "",
    ) -> str:
        """
        Generate a structured LinkedIn post outline.
        
        Args:
            story_input: The base story/narrative to transform
            industry: Industry context (e.g., Water Pump Manufacturing)
            problem: The core problem/challenge to address
            audience: Target audience for the post
            result: Business results/metrics to include
            
        Returns:
            Structured LinkedIn post outline text
        """
        logger.info("📝 Generating LinkedIn post outline...")
        logger.info(f"  Problem: {problem[:100]}...")
        logger.info(f"  Industry: {industry}")

        # Format the prompt with actual values
        prompt = CONTENT_STRATEGIST_PROMPT.format(
            story_input=story_input,
            industry=industry,
            problem=problem,
            audience=audience,
            result=result or "Improved business metrics and client satisfaction",
        )

        outline = self.agent.run(prompt)

        logger.info(f"✅ Outline generated ({len(outline)} chars)")
        return outline
