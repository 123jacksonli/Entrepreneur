"""Social Media Manager Agent: creates and executes a social media plan.

Reads the approved idea and plan, then produces a content calendar, sample
posts, and (if API keys are configured) publishes the first post.
"""

import logging
from dataclasses import dataclass, field

from src.agents._utils import call_llm
from src.agents.base import BaseAgent, AgentContext, AgentResult
from src.artifacts import ArtifactManager
from src.tools.social_poster import publish_posts

logger = logging.getLogger(__name__)


@dataclass
class SocialMediaManagerAgent(BaseAgent):
    id: str = "social-media"
    name: str = "Social Media Manager Agent"
    artifact_manager: ArtifactManager = field(default_factory=ArtifactManager)

    async def run(self, context: AgentContext) -> AgentResult:
        logs: list = []
        idea_brief = context.artifacts.get("idea-generation", context.idea)
        plan_report = context.artifacts.get("plan", "")
        research_report = context.artifacts.get("research", "")

        user_prompt = f"""Idea brief:
{idea_brief}

Plan report:
{plan_report}

Research report:
{research_report}

Create a social media launch plan for this SaaS."""

        system_prompt = (
            "You are the Social Media Manager Agent. Produce a social media plan "
            "with these sections:\n"
            "1. Brand Voice & Positioning\n"
            "2. Target Channels (X, LinkedIn, Reddit, Threads, etc.)\n"
            "3. Content Pillars\n"
            "4. 7-Day Launch Calendar — day, channel, post copy, CTA\n"
            "5. Sample Posts — at least one per chosen channel\n"
            "6. Posting Schedule & Best Times\n"
            "7. Metrics to Track\n"
            "8. Optional Paid/Organic Boost Ideas\n\n"
            "Keep posts concise and platform-appropriate."
        )

        fallback = f"""# Social Media Launch Plan

## Brand Voice & Positioning
Helpful, founder-led, and data-driven. Focus on the problem first, then the solution.

## Target Channels
- X/Twitter for founder updates and quick tips.
- LinkedIn for B2B storytelling and case studies.
- Reddit for niche community engagement.
- Threads for lightweight behind-the-scenes content.

## Content Pillars
1. Problem awareness — why the status quo is painful.
2. Solution showcase — how the product solves it.
3. Social proof — testimonials, metrics, milestones.
4. Founder journey — building in public.

## 7-Day Launch Calendar
- Day 1: Teaser post on X and LinkedIn.
- Day 2: Problem thread on X.
- Day 3: LinkedIn article announcing the launch.
- Day 4: Reddit post in a relevant subreddit.
- Day 5: Customer pain-point poll on X.
- Day 6: Demo video or screenshot on Threads.
- Day 7: Week-one recap and thank-you post.

## Sample Posts
- **X:** "Launching [Idea] today — a dead-simple way to [value prop]. Here's the problem we solve 🧵"
- **LinkedIn:** "After talking to 20 founders, I realized [problem]. So we built [solution]. Here's what we learned..."
- **Reddit:** "I built a tool to [solve problem]. Would love feedback from this community."

## Posting Schedule & Best Times
- Weekdays, 9–11 AM and 6–8 PM in the target timezone.

## Metrics to Track
- Impressions, engagement rate, link clicks, sign-ups, follower growth.

## Optional Paid/Organic Boost Ideas
- Repurpose the best-performing post into a short video.
- Run a small X/LinkedIn ad campaign to the landing page.
"""

        content = call_llm(self.id, system_prompt, user_prompt, fallback)

        # Optional: attempt to publish the first X post if keys are configured.
        first_post = self._extract_first_x_post(content)
        if first_post:
            try:
                results = publish_posts([{"platform": "x", "text": first_post}])
                for r in results:
                    logs.append(
                        self.log(
                            f"Social post to {r.platform}: posted={r.posted}, "
                            f"url={r.url}, error={r.error}"
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                logs.append(self.log(f"Social publishing failed: {exc}", level="warn"))
        else:
            logs.append(self.log("No X post extracted; social publishing skipped"))

        artifact_path = self.artifact_manager.write("social-media", content)
        logs.append(self.log(f"Wrote social media plan to {artifact_path}"))

        return AgentResult(
            status="completed",
            outputs=[artifact_path],
            logs=logs,
            artifact_text=content,
        )

    def _extract_first_x_post(self, content: str) -> str | None:
        """Naively extract the first X/Twitter sample post from the plan."""
        for line in content.splitlines():
            if "**X:**" in line or "**Twitter:**" in line or line.strip().startswith("- X:"):
                return line.split(":", 1)[-1].strip().strip('"')
        return None
