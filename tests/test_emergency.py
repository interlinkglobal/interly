from computer_agent.emergency import EmergencyStop


def test_emergency_stop_flag_can_be_reset() -> None:
    emergency = EmergencyStop()
    emergency._event.set()

    assert emergency.requested()
    emergency.reset()
    assert not emergency.requested()
