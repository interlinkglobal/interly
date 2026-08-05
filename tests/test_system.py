from unittest.mock import patch

from computer_agent.system import installed_applications, power_action, system_metrics


def test_system_metrics_contains_core_categories() -> None:
    result = system_metrics()

    assert '"cpu_percent"' in result
    assert '"memory"' in result
    assert '"system_disk"' in result


@patch("computer_agent.system.subprocess.run")
def test_installed_app_size_is_converted_to_megabytes(run: object) -> None:
    run.return_value.returncode = 0
    run.return_value.stdout = '[{"DisplayName":"Example","EstimatedSize":2048}]'
    run.return_value.stderr = ""

    result = installed_applications()

    assert '"estimated_size_mb": 2.0' in result


@patch("computer_agent.system.subprocess.Popen")
def test_restart_uses_fixed_shutdown_command(popen: object) -> None:
    assert power_action("restart") == "Windows restart started."
    popen.assert_called_once_with(["shutdown.exe", "/r", "/t", "0"])
