import pytest
from app import app as flask_app


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # A consistent secret key is needed for session testing
    flask_app.config.update({"TESTING": True, "SECRET_KEY": "test-secret-key"})
    yield flask_app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


def test_initial_state(client):
    """Test that the initial game state is set up correctly."""
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.get_json()
    assert data["game_mode"] == "501"
    assert data["team1_score"] == 501
    assert data["team2_score"] == 501
    assert data["current_player"] == 1
    assert data["turn_scores"] == []
    assert data["turn_log"] == []
    assert data["player1_name"] == "Player 1"
    assert data["player2_name"] == "Player 2"
    assert not data["game_over"]


def test_reset_game(client):
    """Test resetting the game to a different mode."""
    response = client.post("/api/reset", json={"mode": "301"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["game_mode"] == "301"
    assert data["team1_score"] == 301
    assert data["team2_score"] == 301


def test_record_simple_score(client):
    """Test recording a single valid score."""
    client.get("/api/state")  # Initialize session
    response = client.post("/api/score", json={"base_score": 20, "multiplier": 3})
    assert response.status_code == 200
    data = response.get_json()
    assert data["team1_score"] == 441  # 501 - 60
    assert len(data["turn_scores"]) == 1
    assert data["turn_scores"][0]["repr"] == "T20"


def test_full_turn_and_player_switch(client):
    """Test a full 3-dart turn that results in a player switch."""
    client.post("/api/reset", json={"mode": "501"})  # Start fresh
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})  # P1 Dart 1: 20
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})  # P1 Dart 2: 20
    response = client.post(
        "/api/score", json={"base_score": 20, "multiplier": 1}
    )  # P1 Dart 3: 20
    data = response.get_json()

    assert data["team1_score"] == 441  # 501 - 60
    assert data["current_player"] == 2  # Should be Player 2's turn
    assert len(data["turn_scores"]) == 0  # Turn scores reset for new player
    assert "Player 2 to throw" in data["message"]
    assert len(data["turn_log"]) == 1
    assert "Player 1: 60 (S20 S20 S20)" in data["turn_log"][0]


def test_bust_rule_below_zero(client):
    """Test the bust rule when score goes below 0."""
    client.post("/api/reset", json={"mode": "501"})
    # Manually set score to 40 for testing
    with client.session_transaction() as session:
        session["team1_score"] = 40

    # Player 1 throws T20 (60), which is a bust
    response = client.post("/api/score", json={"base_score": 20, "multiplier": 3})
    data = response.get_json()

    assert data["team1_score"] == 40  # Score should revert to start of turn
    assert data["current_player"] == 2  # Next player's turn
    assert "BUST" in data["message"]
    assert "BUST (T20)" in data["turn_log"][0]


def test_bust_rule_score_of_one(client):
    """Test the bust rule when remaining score is 1."""
    client.post("/api/reset", json={"mode": "501"})
    with client.session_transaction() as session:
        session["team1_score"] = 41

    # Player 1 throws S20, then S20, leaving 1. This is a bust.
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})  # Score is 21
    response = client.post(
        "/api/score", json={"base_score": 20, "multiplier": 1}
    )  # Score would be 1, bust!
    data = response.get_json()

    assert data["team1_score"] == 41  # Score reverts
    assert data["current_player"] == 2
    assert "BUST" in data["message"]
    assert "BUST (S20 S20)" in data["turn_log"][0]


def test_bust_rule_no_double_out(client):
    """Test the bust rule when finishing on a single or triple instead of a double."""
    client.post("/api/reset", json={"mode": "501"})
    with client.session_transaction() as session:
        session["team1_score"] = 40

    # Player 1 throws S20, then S20. This is a bust because it's not a D10.
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})
    response = client.post("/api/score", json={"base_score": 20, "multiplier": 1})
    data = response.get_json()

    assert data["team1_score"] == 40  # Score reverts
    assert data["current_player"] == 2
    assert "BUST" in data["message"]


def test_win_condition(client):
    """Test a valid win on a double."""
    client.post("/api/reset", json={"mode": "501"})
    with client.session_transaction() as session:
        session["team1_score"] = 40

    # Player 1 throws D20 to win
    response = client.post("/api/score", json={"base_score": 20, "multiplier": 2})
    data = response.get_json()

    assert data["game_over"] is True
    assert data["winner"] == 1
    assert data["team1_score"] == 0
    assert "GAME SHOT" in data["message"]
    assert "40 (D20)" in data["turn_log"][0]


def test_undo_functionality(client):
    """Test that the undo endpoint reverts the state."""
    client.post("/api/reset", json={"mode": "501"})
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})  # Score is 481

    # Undo the last throw
    undo_response = client.post("/api/undo")
    assert undo_response.status_code == 200
    data = undo_response.get_json()

    assert data["team1_score"] == 501  # Back to original score
    assert len(data["turn_scores"]) == 0
    assert "Undo successful" in data["message"]

    # Test undo at the beginning of a game
    client.post("/api/reset", json={"mode": "501"})
    undo_response_at_start = client.post("/api/undo")
    data_at_start = undo_response_at_start.get_json()
    assert "Cannot undo further" in data_at_start["message"]


def test_update_player_names(client):
    """Test updating player names and ensuring they persist and appear in logs."""
    client.post("/api/reset", json={"mode": "501"})
    client.post("/api/names", json={"player1_name": "Alice", "player2_name": "Bob"})

    # Make a turn
    client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    response = client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    data = response.get_json()

    assert data["player1_name"] == "Alice"
    assert data["player2_name"] == "Bob"
    assert "Bob to throw" in data["message"]
    assert "Alice: 3 (S1 S1 S1)" in data["turn_log"][0]


def test_teams_mode_toggle(client):
    """Test toggling teams mode and player rotation."""
    client.post("/api/reset", json={"mode": "501"})

    # Enable teams mode
    response = client.post("/api/settings", json={"teams_mode": True})
    data = response.get_json()
    assert data["teams_mode"] is True

    # Player 1 (Team 1)
    client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    client.post("/api/score", json={"base_score": 1, "multiplier": 1})

    # Player 2 (Team 2)
    client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    client.post("/api/score", json={"base_score": 1, "multiplier": 1})

    # Player 3 (Team 1)
    client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    response = client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    data = response.get_json()

    assert data["current_player"] == 4  # Should be Player 4's turn


def test_around_the_world_logic(client):
    """Test the core logic for 'Around the World' mode."""
    client.post("/api/reset", json={"mode": "around_the_world"})

    # Player 1 (Team 1) needs to hit 1
    response = client.post(
        "/api/score", json={"base_score": 5, "multiplier": 1}
    )  # Miss
    data = response.get_json()
    assert data["team1_target"] == 1
    assert "needs 1" in data["message"]

    response = client.post("/api/score", json={"base_score": 1, "multiplier": 1})  # Hit
    data = response.get_json()
    assert data["team1_target"] == 2
    assert "hit 1! Now on 2" in data["message"]

    # Player 1 hits 2, turn ends, player 2's turn
    response = client.post("/api/score", json={"base_score": 2, "multiplier": 1})  # Hit
    data = response.get_json()
    assert data["team1_target"] == 3
    assert data["current_player"] == 2  # Player 2's turn
    assert "to throw for 1" in data["message"]  # Player 2 is on target 1


def test_around_the_world_win(client):
    """Test winning 'Around the World' by hitting the bull."""
    client.post("/api/reset", json={"mode": "around_the_world"})
    with client.session_transaction() as session:
        session["team1_target"] = 25  # Set target to Bull

    response = client.post(
        "/api/score", json={"base_score": 25, "multiplier": 1}
    )  # Hit the bull
    data = response.get_json()

    assert data["game_over"] is True
    assert data["winner"] == 1
    assert "wins Around the World" in data["message"]


def test_get_stats(client):
    """Test the statistics calculation endpoint."""
    client.post("/api/reset", json={"mode": "501"})
    client.post("/api/names", json={"player1_name": "P1", "player2_name": "P2"})

    # P1 turn: 100 points (T20, S20, S20)
    client.post("/api/score", json={"base_score": 20, "multiplier": 3})
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})

    # P2 turn: BUST
    with client.session_transaction() as session:
        session["team2_score"] = 20
    client.post("/api/score", json={"base_score": 20, "multiplier": 3})  # Bust

    response = client.get("/api/stats")
    assert response.status_code == 200
    stats = response.get_json()

    assert "P1" in stats
    assert "P2" in stats
    assert stats["P1"]["total_score"] == 100
    assert stats["P1"]["darts_thrown"] == 3
    assert stats["P1"]["average"] == 100.0

    assert stats["P2"]["total_score"] == 0
    assert stats["P2"]["darts_thrown"] == 1  # Bust on first dart
    assert stats["P2"]["average"] == 0.0
