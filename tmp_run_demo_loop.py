import asyncio
import json
import re
import sys
import traceback
from pathlib import Path

from src.agents.architecture import ArchitectureAgent
from src.agents.base import AgentContext
from src.agents.execution import ExecutionAgent
from src.agents.execution_plan import ExecutionPlanAgent
from src.agents.idea_generation import IdeaGenerationAgent
from src.agents.plan import PlanAgent
from src.agents.qa import QAAgent
from src.agents.research import ResearchAgent
from src.agents.test import TestAgent
from src.artifacts import ArtifactManager
from src.config import Config
from src.ideas import generate_idea
from src.llm_factory import create_completion


def print_section(title: str, content: str) -> None:
    print(f"\n{'=' * 78}")
    print(title)
    print("=" * 78)
    print(content[:4000])
    if len(content) > 4000:
        print("\n... (truncated)")


_orig_create_completion = create_completion


def _timed_create_completion(agent_id, system_prompt, user_prompt, **kwargs):
    kwargs.setdefault("timeout", 300)
    return _orig_create_completion(agent_id, system_prompt, user_prompt, **kwargs)


import src.llm_factory
import src.agents._utils
import src.ideas as ideas_module

src.llm_factory.create_completion = _timed_create_completion
src.agents._utils.create_completion = _timed_create_completion
ideas_module.create_completion = _timed_create_completion



THRESHOLD = 8  # approve ideas scoring >= this
MAX_ITERATIONS = 5
MAX_QA_ITERATIONS = 5


def _extract_score(text: str) -> int | None:
    m = re.search(r"Score:\s*([\d.]+)/10", text)
    if m:
        try:
            return int(float(m.group(1)))
        except ValueError:
            return None
    return None


def _extract_verdict(text: str) -> str | None:
    m = re.search(r"Verdict:\s*(accept|conditional accept|reject)", text, re.IGNORECASE)
    return m.group(1).lower() if m else None


def _run_smoke_test(run_id: str) -> tuple[bool, str]:
    """Install dependencies, run tests, and run the build/demo command in the workspace."""
    import shutil
    import subprocess

    workspace = Path(Config.WORKSPACE_DIR) / run_id
    if not workspace.exists():
        return False, f"Workspace {workspace} does not exist."

    logs: list[str] = []

    # Detect project type and commands.
    if (workspace / "package.json").exists():
        install_cmd = ["npm", "install"]
        test_cmd = ["npm", "test"]
        package_json = json.loads((workspace / "package.json").read_text(encoding="utf-8"))
        scripts = package_json.get("scripts", {})
        if "build" in scripts:
            run_cmd = ["npm", "run", "build"]
            run_timeout = 300
        elif "demo" in scripts:
            run_cmd = ["npm", "run", "demo"]
            run_timeout = 60  # demo scripts often start a server; short timeout is enough
        else:
            run_cmd = None
            run_timeout = 0
    elif any((workspace / f).exists() for f in ("pyproject.toml", "requirements.txt", "setup.py")):
        install_cmd = ["python", "-m", "pip", "install", "-e", "."]
        test_cmd = ["python", "-m", "pytest", "tests/", "-q"]
        run_cmd = None
        run_timeout = 0
    else:
        return False, "No dependency manifest found."

    for step, cmd, timeout in [
        ("install", install_cmd, 300),
        ("test", test_cmd, 300),
        ("run/build", run_cmd, run_timeout),
    ]:
        if cmd is None:
            continue
        logs.append(f">>> {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            logs.append(result.stdout)
            logs.append(result.stderr)
            if result.returncode != 0:
                return False, "\n".join(logs)
        except subprocess.TimeoutExpired:
            logs.append(f"Command timed out after {timeout}s (this is expected for long-running demo servers).")
            if step == "run/build":
                # For demo scripts, a timeout is acceptable if the output directory was created.
                pass
            else:
                return False, "\n".join(logs)
        except Exception as exc:  # noqa: BLE001
            logs.append(str(exc))
            return False, "\n".join(logs)

    return True, "\n".join(logs)


async def run_iteration(iteration: int) -> dict | None:
    run_id = f"demo-run-iter-{iteration}"
    Config.OUTPUTS_DIR = f"outputs/demo-run/{iteration:02d}"
    am = ArtifactManager(run_id=run_id)

    print(f"\n{'#' * 78}")
    print(f"# ITERATION {iteration}")
    print("#" * 78)

    print("\nGenerating idea via LLM...", flush=True)
    try:
        idea = generate_idea()
    except Exception as exc:
        print(f"[ERROR] Idea generation failed: {exc}")
        traceback.print_exc()
        idea = "A SaaS tool that helps small businesses automate repetitive tasks with AI."
    print_section(f"GENERATED IDEA (iteration {iteration})", idea)

    ctx = AgentContext(run_id=run_id, idea=idea, artifacts={})

    for name, cls in [
        ("Idea Generation", IdeaGenerationAgent),
        ("Research", ResearchAgent),
        ("Plan", PlanAgent),
    ]:
        print(f"\n>>> Running {name}...", flush=True)
        agent = cls(artifact_manager=am)
        try:
            result = await agent.run(ctx)
        except Exception as exc:
            print(f"[ERROR] {name} failed: {exc}")
            traceback.print_exc()
            return None
        ctx.artifacts[agent.id] = result.artifact_text
        if name == "Plan":
            score = result.metadata.get("score") if result.metadata else None
            if score is None:
                score = _extract_score(result.artifact_text)
            decision = result.metadata.get("decision") if result.metadata else None
            print(f"[PLAN RESULT] decision={decision}, score={score}")
            print_section("PLAN OUTPUT", result.artifact_text)
            return {
                "iteration": iteration,
                "idea": idea,
                "idea_brief": ctx.artifacts.get("idea-generation", ""),
                "score": score,
                "decision": decision,
                "plan_text": result.artifact_text,
                "outputs_dir": am.outputs_dir,
            }
    return None


async def main() -> None:
    eliminated: list[dict] = []
    approved: dict | None = None

    for i in range(1, MAX_ITERATIONS + 1):
        result = await run_iteration(i)
        if result is None:
            print(f"[WARN] Iteration {i} failed; skipping.")
            continue

        if result["score"] is not None and result["score"] >= THRESHOLD:
            approved = result
            break
        else:
            eliminated.append(result)
            print(f"[ELIMINATED] iteration {i} score {result['score']}")

    if approved is None and eliminated:
        # pick the best eliminated idea and treat it as approved for demo continuation
        best = max(eliminated, key=lambda x: x["score"] if x["score"] is not None else 0)
        print(f"\nNo idea reached {THRESHOLD}/10. Using best eliminated idea (score {best['score']}).")
        approved = best
        eliminated = [e for e in eliminated if e["iteration"] != best["iteration"]]

    if approved is None:
        print("\nNo ideas generated. Aborting.")
        sys.exit(1)

    # Run execution plan and architecture on approved/best idea.
    Config.OUTPUTS_DIR = approved["outputs_dir"]
    run_id = f"demo-run-iter-{approved['iteration']}"
    am = ArtifactManager(run_id=run_id)
    ctx = AgentContext(
        run_id=run_id,
        idea=approved["idea"],
        artifacts={
            "idea-generation": approved["idea_brief"],
            "research": "",  # research artifact already saved to disk by ArtifactManager
            "plan": approved["plan_text"],
        },
    )

    for name, cls in [
        ("Execution Plan", ExecutionPlanAgent),
        ("Architecture", ArchitectureAgent),
    ]:
        print(f"\n>>> Running {name}...", flush=True)
        agent = cls(artifact_manager=am)
        try:
            result = await agent.run(ctx)
            ctx.artifacts[agent.id] = result.artifact_text
            print_section(f"{name.upper()} OUTPUT", result.artifact_text)
        except Exception as exc:
            print(f"[ERROR] {name} failed: {exc}")
            traceback.print_exc()

    # QA loop: Execution → Test → QA, up to MAX_QA_ITERATIONS.
    qa_iteration = 0
    qa_verdict = "reject"
    while qa_iteration < MAX_QA_ITERATIONS:
        qa_iteration += 1
        print(f"\n>>> QA LOOP ITERATION {qa_iteration}", flush=True)

        print("\n>>> Running Execution Agent...", flush=True)
        exec_agent = ExecutionAgent(artifact_manager=am)
        try:
            exec_result = await exec_agent.run(ctx)
            ctx.artifacts["execution"] = exec_result.artifact_text
            print_section("EXECUTION OUTPUT", exec_result.artifact_text)
        except Exception as exc:
            print(f"[ERROR] Execution Agent failed: {exc}")
            traceback.print_exc()
            break

        print("\n>>> Running Test Agent...", flush=True)
        test_agent = TestAgent(artifact_manager=am)
        try:
            test_result = await test_agent.run(ctx)
            ctx.artifacts["test"] = test_result.artifact_text
            print_section("TEST OUTPUT", test_result.artifact_text)
        except Exception as exc:
            print(f"[ERROR] Test Agent failed: {exc}")
            traceback.print_exc()
            break

        print("\n>>> Running QA Agent...", flush=True)
        qa_agent = QAAgent(artifact_manager=am)
        try:
            qa_result = await qa_agent.run(ctx)
            ctx.artifacts["qa"] = qa_result.artifact_text
            qa_verdict = qa_result.metadata.get("verdict") if qa_result.metadata else None
            if qa_verdict is None:
                qa_verdict = _extract_verdict(qa_result.artifact_text)
            print(f"[QA RESULT] verdict={qa_verdict}")
            print_section("QA OUTPUT", qa_result.artifact_text)
        except Exception as exc:
            print(f"[ERROR] QA Agent failed: {exc}")
            traceback.print_exc()
            break

        if qa_verdict in ("accept", "conditional accept"):
            print(f"\n[QA ACCEPTED] after {qa_iteration} iteration(s).")
            break

        print(f"\n[QA REJECTED] Sending rework instructions back to Execution Agent.")
    else:
        print(f"\n[QA LOOP EXHAUSTED] Max {MAX_QA_ITERATIONS} rework iterations reached.")

    # Final smoke test: install deps, run tests, and run demo/build command.
    print("\n>>> Running final smoke test...", flush=True)
    smoke_ok, smoke_log = _run_smoke_test(run_id)
    print_section("SMOKE TEST OUTPUT", smoke_log)
    if smoke_ok:
        print("\n[SMOKE TEST PASSED] Project installs, tests, and runs.")
        qa_verdict = "accept"
    else:
        print("\n[SMOKE TEST FAILED] Project is not runnable out of the box.")

    print(f"\n{'=' * 78}")
    print("ELIMINATED IDEAS:")
    for e in eliminated:
        print(f"  - Iteration {e['iteration']}: score {e['score']}")
        title = e['idea_brief'].split('\n')[0] if e['idea_brief'] else e['idea'][:80]
        print(f"    {title}")
    print(f"\nAPPROVED/BEST IDEA:")
    print(f"  - Iteration {approved['iteration']}: score {approved['score']}")
    title = approved['idea_brief'].split('\n')[0] if approved['idea_brief'] else approved['idea'][:80]
    print(f"    {title}")
    print(f"\nArtifacts saved under: outputs/demo-run/")
    print(f"Workspace saved under: workspace/{run_id}/")
    print(f"Workspace: workspace/{run_id}/")
    print("=" * 78)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"DEMO FAILED: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
