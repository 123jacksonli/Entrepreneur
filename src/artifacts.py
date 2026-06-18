"""Read and write agent artifact files.

Artifacts are written under ``outputs/{run_id}/`` when a ``run_id`` is provided,
so each pipeline run keeps its own set of artifacts. If no ``run_id`` is given,
files are written directly to ``outputs/`` for backward compatibility.
"""

from pathlib import Path

from src.config import Config

ARTIFACT_PATHS = {
    "idea-generation": "outputs/00-idea-brief.md",
    "research": "outputs/01-research-report.md",
    "plan": "outputs/02-plan-report.md",
    "execution-plan": "outputs/03-execution-plan.md",
    "architecture": "outputs/04-architecture-design.md",
    "execution": "outputs/05-implementation-summary.md",
    "test": "outputs/06-test-report.md",
    "qa": "outputs/07-qa-report.md",
}


class ArtifactManager:
    def __init__(
        self,
        outputs_dir: str = Config.OUTPUTS_DIR,
        run_id: str | None = None,
    ) -> None:
        base = Path(outputs_dir)
        self.outputs_dir = base / run_id if run_id else base
        self.run_id = run_id
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

    def read_path(self, path: str) -> str:
        file_path = Path(path)
        if not file_path.exists():
            return ""
        return file_path.read_text(encoding="utf-8")

    def list_artifacts(self) -> dict[str, str]:
        """Return a mapping of stage -> file path for existing artifacts."""
        result = {}
        for stage in ARTIFACT_PATHS:
            path = self.outputs_dir / self._filename(stage)
            if path.exists():
                result[stage] = str(path)
        return result

    def _filename(self, stage: str) -> str:
        return Path(ARTIFACT_PATHS[stage]).name
