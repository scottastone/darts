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


# --- Cricket Game Mode Tests ---
def test_cricket_initial_state(client):
    """Test the initial state of a Cricket game."""
    response = client.post("/api/reset", json={"mode": "cricket"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["game_mode"] == "cricket"
    assert data["team1_score"] == 0
    assert data["team2_score"] == 0
    assert "cricket_marks" in data
    assert data["cricket_marks"]["team1"]["20"] == 0
    assert data["cricket_marks"]["team2"]["15"] == 0


def test_cricket_marking_numbers(client):
    """Test marking numbers in Cricket and player switching."""
    client.post("/api/reset", json={"mode": "cricket"})
    # P1 hits S20
    response = client.post("/api/score", json={"base_score": 20, "multiplier": 1})
    data = response.get_json()
    assert data["cricket_marks"]["team1"]["20"] == 1
    assert "marked S20" in data["message"]

    # P1 hits T20, closing the number
    response = client.post("/api/score", json={"base_score": 20, "multiplier": 3})
    data = response.get_json()
    assert data["cricket_marks"]["team1"]["20"] == 3  # 1 + 2 (from T20)
    assert data["team1_score"] == 20  # One of the T20 hits scores points
    assert "scored 20" in data["message"]

    # P1 misses, turn ends
    response = client.post("/api/score", json={"base_score": 1, "multiplier": 1})
    data = response.get_json()
    assert data["current_player"] == 2
    assert "Player 2 to throw" in data["message"]


def test_cricket_scoring_points(client):
    """Test scoring points on an owned number in Cricket."""
    client.post("/api/reset", json={"mode": "cricket"})
    with client.session_transaction() as session:
        # Pre-close 20s for Player 1 and partially close 18 for P2
        session["cricket_marks"]["team1"]["20"] = 3  # P1 has 20s closed

    # P1 hits T20, scoring 60 points, then misses twice. Turn ends.
    client.post("/api/score", json={"base_score": 20, "multiplier": 3})  # 60 points
    client.post("/api/score", json={"base_score": 5, "multiplier": 1})  # Miss
    client.post("/api/score", json={"base_score": 7, "multiplier": 1})  # Miss

    # P2's turn. P2 needs to close 18s and score.
    # P2 hits D18 (2 marks)
    response = client.post("/api/score", json={"base_score": 18, "multiplier": 2})
    data = response.get_json()
    assert data["cricket_marks"]["team2"]["18"] == 2

    # P2 hits S18 (closes 18s)
    response = client.post("/api/score", json={"base_score": 18, "multiplier": 1})
    data = response.get_json()
    assert data["cricket_marks"]["team2"]["18"] == 3

    # P2 hits S18 again, now scoring 18 points.
    response = client.post("/api/score", json={"base_score": 18, "multiplier": 1})
    data = response.get_json()
    assert data["team2_score"] == 18
    # The turn is now over, so the message should be for the next player (P1)
    assert "Player 1 to throw" in data["message"]


def test_cricket_no_scoring_when_opponent_closed(client):
    """Test that no points are scored on a number closed by both players."""
    client.post("/api/reset", json={"mode": "cricket"})
    with client.session_transaction() as session:
        # Pre-close 20s for both players
        session["cricket_marks"]["team1"]["20"] = 3
        session["cricket_marks"]["team2"]["20"] = 3

    # P1 hits S20, should score 0 points
    response = client.post("/api/score", json={"base_score": 20, "multiplier": 1})
    data = response.get_json()
    assert data["team1_score"] == 0
    assert "marked S20" in data["message"]  # No "scored" message


def test_cricket_win_condition(client):
    """Test the win condition in Cricket."""
    client.post("/api/reset", json={"mode": "cricket"})
    with client.session_transaction() as session:
        # P1 has all numbers closed except 20, and is ahead on points
        for num in ["19", "18", "17", "16", "15", "25"]:
            session["cricket_marks"]["team1"][num] = 3
        session["team1_score"] = 100
        session["team2_score"] = 50

    # P1 hits T20 to close the last number and win
    response = client.post("/api/score", json={"base_score": 20, "multiplier": 3})
    data = response.get_json()

    assert data["game_over"] is True
    assert data["winner"] == 1
    assert "wins Cricket" in data["message"]


def test_cricket_no_win_on_lower_score(client):
    """Test that the game does not end if the player has a lower score."""
    client.post("/api/reset", json={"mode": "cricket"})
    with client.session_transaction() as session:
        # P1 closes all numbers but is behind on points
        for num in ["20", "19", "18", "17", "16", "15", "25"]:
            session["cricket_marks"]["team1"][num] = 3
        session["team2_score"] = 100

    # P1's turn, but game should not be over
    response = client.get("/api/state")
    data = response.get_json()
    assert data["game_over"] is False


def test_long_501_game_simulation(client):
    """Simulates a longer 501 game to test state over multiple turns."""
    client.post("/api/reset", json={"mode": "501"})

    # Turn 1 (P1): Scores 100, leaves 401
    client.post("/api/score", json={"base_score": 20, "multiplier": 3})
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})

    # Turn 2 (P2): Scores 45, leaves 456
    client.post("/api/score", json={"base_score": 15, "multiplier": 1})
    client.post("/api/score", json={"base_score": 15, "multiplier": 1})
    client.post("/api/score", json={"base_score": 15, "multiplier": 1})

    # Turn 3 (P1): Scores 140, leaves 261
    client.post("/api/score", json={"base_score": 20, "multiplier": 3})
    client.post("/api/score", json={"base_score": 20, "multiplier": 3})
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})

    # Turn 4 (P2): Scores 95, leaves 361
    client.post("/api/score", json={"base_score": 19, "multiplier": 3})
    client.post("/api/score", json={"base_score": 19, "multiplier": 1})
    client.post("/api/score", json={"base_score": 19, "multiplier": 1})

    # Turn 5 (P1): Scores 131, leaves 130
    client.post("/api/score", json={"base_score": 20, "multiplier": 3})
    client.post("/api/score", json={"base_score": 17, "multiplier": 3})
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})

    # Turn 6 (P2): Scores 100, leaves 261
    client.post("/api/score", json={"base_score": 20, "multiplier": 3})
    client.post("/api/score", json={"base_score": 20, "multiplier": 1})
    response = client.post("/api/score", json={"base_score": 20, "multiplier": 1})
    data = response.get_json()
    assert data["team2_score"] == 261  # Score reverts to start of turn

    # Turn 7 (P1): Wins with a 130 checkout (T20, T20, D5)
    client.post("/api/score", json={"base_score": 20, "multiplier": 3})  # 70 left
    client.post("/api/score", json={"base_score": 20, "multiplier": 3})  # 10 left
    response = client.post("/api/score", json={"base_score": 5, "multiplier": 2})  # Win
    data = response.get_json()

    assert data["game_over"] is True
    assert data["winner"] == 1
    assert data["team1_score"] == 0
    assert "GAME SHOT" in data["message"]
    assert len(data["turn_log"]) == 7  # 6 full turns + 1 winning turn
