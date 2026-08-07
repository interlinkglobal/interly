from pathlib import Path

from computer_agent.dev_workflows import RepositoryWorkflow


def test_repository_workflow_inspects_repo_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")

    workflow = RepositoryWorkflow(repo)

    summary = workflow.inspect()

    assert summary["root"] == str(repo)
    assert summary["files"][0]["name"] == "pyproject.toml"
    assert summary["files"][1]["name"] == "app.py"


def test_repository_workflow_runs_safe_commands(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    workflow = RepositoryWorkflow(repo)
    result = workflow.run_command(["python", "-c", "print('ok')"], timeout=5)

    assert result["returncode"] == 0
    assert "ok" in result["stdout"]
