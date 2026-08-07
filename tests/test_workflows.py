from pathlib import Path

from computer_agent.dev_workflows import RepositoryWorkflow, WorkflowRegistry


def test_workflow_registry_persists_named_workflows(tmp_path: Path) -> None:
    registry = WorkflowRegistry(tmp_path / "workflows.json")
    registry.save_workflow("lint", {"command": ["ruff", "check", "."]})

    reloaded = WorkflowRegistry(tmp_path / "workflows.json")
    stored = reloaded.list_workflows()

    assert stored[0]["name"] == "lint"
    assert stored[0]["definition"]["command"] == ["ruff", "check", "."]


def test_repository_workflow_can_run_named_workflow(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    workflow = RepositoryWorkflow(repo)
    result = workflow.run_named_workflow(["python", "-c", "print('ok')"])

    assert result["returncode"] == 0
    assert "ok" in result["stdout"]
