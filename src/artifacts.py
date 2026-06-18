"""Read and write agent artifact files."""

from pathlib import Path

from src.config import Config

ARTIFACT_PATHS = {
    "research": "outputs/01-research-report.md",
    "plan": "outputs/02-plan-report.md",
    "execution-plan": "outputs/03-execution-plan.md",
    "architecture": "outputs/04-architecture-design.md",
    "human-in-loop": "outputs/05-human-decision.md",
    "execution": "outputs/06-implementation-summary.md",
    "test": "outputs/07-test-report.md",
    "qa": "outputs/08-qa-report.md",
}


class ArtifactManager:
    def __init__(self, outputs_dir: str = Config.OUTPUTS_DIR) -> None:
        self.outputs_dir = Path(outputs_dir)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def write(self, stage: str, content: str) -> str:
        path = self.outputs_dir / self._filename(stage)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def read(self, stage: str) -> str:
        path = self.outputs_dir / self._filename(stage)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _filename(self, stage: str) -> str:
        return Path(ARTIFACT_PATHS[stage]).name
