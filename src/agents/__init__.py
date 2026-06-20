"""Agent implementations."""

from src.agents.architecture import ArchitectureAgent
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.agents.execution import ExecutionAgent
from src.agents.execution_plan import ExecutionPlanAgent
from src.agents.idea_generation import IdeaGenerationAgent
from src.agents.plan import PlanAgent
from src.agents.qa import QAAgent
from src.agents.research import ResearchAgent
from src.agents.social_media_manager import SocialMediaManagerAgent
from src.agents.supabase_design import SupabaseDesignAgent
from src.agents.test import TestAgent

AGENTS: dict[str, type[BaseAgent]] = {
    "idea-generation": IdeaGenerationAgent,
    "research": ResearchAgent,
    "plan": PlanAgent,
    "execution-plan": ExecutionPlanAgent,
    "architecture": ArchitectureAgent,
    "execution": ExecutionAgent,
    "test": TestAgent,
    "qa": QAAgent,
    "supabase-design": SupabaseDesignAgent,
    "social-media": SocialMediaManagerAgent,
}

__all__ = [
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "AGENTS",
    "ArchitectureAgent",
    "ExecutionAgent",
    "ExecutionPlanAgent",
    "IdeaGenerationAgent",
    "PlanAgent",
    "QAAgent",
    "ResearchAgent",
    "SocialMediaManagerAgent",
    "SupabaseDesignAgent",
    "TestAgent",
]
