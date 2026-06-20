import pytest

from src.agents.base import AgentContext
from src.agents.social_media_manager import SocialMediaManagerAgent
from src.agents.supabase_design import SupabaseDesignAgent
from src.artifacts import ArtifactManager


@pytest.fixture
def artifact_manager(tmp_path, monkeypatch):
    monkeypatch.setattr("src.config.Config.OUTPUTS_DIR", str(tmp_path / "outputs"))
    monkeypatch.setattr("src.llm_factory.API_KEY", None)
    return ArtifactManager(run_id="support-run")


@pytest.mark.anyio
async def test_supabase_design_agent_produces_artifact(artifact_manager):
    agent = SupabaseDesignAgent(artifact_manager=artifact_manager)
    context = AgentContext(run_id="support-run", idea="A SaaS for carbon tracking")
    result = await agent.run(context)

    assert result.status == "completed"
    assert "08-supabase-design.md" in result.outputs[0]
    assert "Row Level Security" in result.artifact_text or "RLS" in result.artifact_text


@pytest.mark.anyio
async def test_social_media_manager_agent_produces_artifact(artifact_manager):
    agent = SocialMediaManagerAgent(artifact_manager=artifact_manager)
    context = AgentContext(run_id="support-run", idea="A SaaS for carbon tracking")
    result = await agent.run(context)

    assert result.status == "completed"
    assert "09-social-media-plan.md" in result.outputs[0]
    assert "Content Pillars" in result.artifact_text
