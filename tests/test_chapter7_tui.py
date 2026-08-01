"""
Tests for Chapter 7 Part 1: interactive TUI menu.
We don't test the visuals — we mock questionary's .ask() responses
and assert the menu routes to the correct existing command function.
"""
from unittest.mock import patch, MagicMock

from cli.tui import run_menu, BACK


def _mock_ask_sequence(*return_values):
    """Returns a MagicMock whose .ask() yields each value in sequence, then None forever."""
    mock = MagicMock()
    mock.ask.side_effect = list(return_values) + [None] * 20
    return mock


@patch("cli.tui.agent_create")
@patch("cli.tui.questionary")
def test_create_agent_routes_correctly(mock_questionary, mock_agent_create):
    # First .select() picks "Create new agent", second picks "Exit"
    mock_questionary.select.side_effect = [
        _mock_ask_sequence("Create new agent"),
        _mock_ask_sequence("Exit"),
    ]
    # .text() for business name
    mock_questionary.text.return_value = _mock_ask_sequence("test-biz")

    run_menu()

    mock_agent_create.assert_called_once_with("test-biz")


@patch("cli.tui.agent_test")
@patch("cli.tui.questionary")
def test_test_agent_routes_correctly_with_two_prompts(mock_questionary, mock_agent_test):
    mock_questionary.select.side_effect = [
        _mock_ask_sequence("Test an agent"),
        _mock_ask_sequence("Exit"),
    ]
    mock_questionary.text.side_effect = [
        _mock_ask_sequence("test-biz"),
        _mock_ask_sequence("hello there"),
    ]

    run_menu()

    mock_agent_test.assert_called_once_with("test-biz", "hello there")


@patch("cli.tui.agent_create")
@patch("cli.tui.questionary")
def test_back_cancels_without_calling_command(mock_questionary, mock_agent_create):
    mock_questionary.select.side_effect = [
        _mock_ask_sequence("Create new agent"),
        _mock_ask_sequence("Exit"),
    ]
    # user types "back" at the business name prompt
    mock_questionary.text.return_value = _mock_ask_sequence("back")

    run_menu()

    mock_agent_create.assert_not_called()


@patch("cli.tui.agent_create")
@patch("cli.tui.questionary")
def test_empty_input_also_cancels(mock_questionary, mock_agent_create):
    mock_questionary.select.side_effect = [
        _mock_ask_sequence("Create new agent"),
        _mock_ask_sequence("Exit"),
    ]
    mock_questionary.text.return_value = _mock_ask_sequence("")

    run_menu()

    mock_agent_create.assert_not_called()


@patch("cli.tui.keys_set")
@patch("cli.tui.questionary")
def test_set_byok_key_routes_with_three_prompts(mock_questionary, mock_keys_set):
    mock_questionary.select.side_effect = [
        _mock_ask_sequence("Set BYOK key"),
        _mock_ask_sequence("Exit"),
    ]
    mock_questionary.text.side_effect = [
        _mock_ask_sequence("test-biz"),
        _mock_ask_sequence("groq"),
    ]
    mock_questionary.password.return_value = _mock_ask_sequence("fake-key-123")

    run_menu()

    mock_keys_set.assert_called_once_with("test-biz", provider="groq", key="fake-key-123")


@patch("cli.tui.agent_create")
@patch("cli.tui.questionary")
def test_exit_immediately_calls_nothing(mock_questionary, mock_agent_create):
    mock_questionary.select.return_value = _mock_ask_sequence("Exit")

    run_menu()

    mock_agent_create.assert_not_called()
