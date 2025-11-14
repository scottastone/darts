import os
import json
from flask import Flask, render_template_string, jsonify, request, session

# Initialize the Flask app
app = Flask(__name__)
# A secret key is required for Flask to use 'session'
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    print("WARNING: SECRET_KEY environment variable not set. Using a temporary key. This is not suitable for production with multiple workers.")
    SECRET_KEY = os.urandom(24).hex()

app.secret_key = SECRET_KEY


# --- App Logic ---

# Load checkouts from JSON file
try:
    with open('checkouts.json', 'r') as f:
        CHECKOUTS = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    print("WARNING: checkouts.json not found or is invalid. Checkout suggestions will be unavailable.")
    CHECKOUTS = {}

def get_checkout_suggestions(score, darts_left=3):
    """Returns a list of checkout suggestions for a given score and number of darts remaining."""
    if 1 < score <= 170:
        # Keys in the JSON-loaded dictionary are strings
        all_suggestions = CHECKOUTS.get(str(score), [])
        # Filter suggestions based on the number of darts left
        valid_suggestions = [s for s in all_suggestions if len(s.split(',')) <= darts_left]
        return valid_suggestions
    return []

def get_throw_string(base_score, multiplier):
    """Generates a string representation of a dart throw (e.g., T20, DB)."""
    if base_score == 0:
        return "MISS"
    if base_score == 25:
        return "DB" if multiplier == 2 else "SB"
    
    prefix = ""
    if multiplier == 3: prefix = "T"
    elif multiplier == 2: prefix = "D"
    elif multiplier == 1: prefix = "S"
    
    return f"{prefix}{base_score}"

def _get_target_display(target):
    """Returns 'Bull' for target 25, otherwise the number."""
    if target == 25:
        return "Bull"
    return str(target)

def _start_game(game_mode='501'):
    """Helper function to initialize or reset the game state in the session."""
    session['game_mode'] = game_mode
    session['teams_mode'] = session.get('teams_mode', False)
    session['player1_name'] = session.get('player1_name', 'Player 1') # Keep names on reset
    session['player2_name'] = session.get('player2_name', 'Player 2')
    session['player3_name'] = session.get('player3_name', 'Player 3')
    session['player4_name'] = session.get('player4_name', 'Player 4')

    session['current_player'] = 1
    session['turn_scores'] = []  # List to hold scores for the current turn (max 3 darts)
    session['history'] = []      # List to store previous states for the 'undo' feature
    session['game_over'] = False
    session['winner'] = None
    session['turn_log'] = []     # A log of completed turns

    # Determine current player name and team for message
    player_name = session[f"player{session['current_player']}_name"]

    if game_mode == 'around_the_world':
        # In teams mode, targets are per-team
        session['team1_target'] = 1
        session['team2_target'] = 1
        session['win_on_double'] = False # Not applicable
        session['checkout_suggestions'] = []
        target_display = _get_target_display(session['team1_target'])
        session['message'] = f"{session['player1_name']} to throw for {target_display}."
    else: # 501, 301, etc.
        try:
            score = int(game_mode)
        except ValueError:
            score = 501 # Default to 501 if mode is invalid
        session['team1_score'] = score
        session['team2_score'] = score
        session['win_on_double'] = True # X01 games always require a double out
        session['checkout_suggestions'] = get_checkout_suggestions(session['team1_score'], 3)
        session['message'] = f"{player_name} to throw."

    # Save the initial state for the very first 'undo'
    _save_state_to_history()
    
def _save_state_to_history():
    """Helper function to save the current game state to the history list."""
    # We create a copy of the session to avoid reference issues
    current_state = session.copy()
    # We don'm_t need to save the history within the history itself
    current_state.pop('history', None) 
    
    history_list = session.get('history', [])
    history_list.append(current_state)
    
    # Keep history from growing too large (e.g., last 50 states)
    if len(history_list) > 50:
        history_list = history_list[-50:]
        
    session['history'] = history_list

def _next_player():
    """Helper function to switch to the next player and reset the turn."""
    # The 'is_bust_turn' flag indicates the turn was already logged by the bust logic.
    # We only log here if it's a normal, completed turn.
    if not session.get('is_bust_turn', False):
        if session.get('turn_scores'): # Only log if at least one dart was thrown
            previous_player_num = session['current_player']
            previous_player_name = session[f"player{previous_player_num}_name"]
            turn_scores_data = session.get('turn_scores', [])
            turn_reprs = " ".join(item['repr'] for item in turn_scores_data)
            turn_total = sum(item['score'] for item in turn_scores_data)
            session.get('turn_log', []).insert(0, f"{previous_player_name}: {turn_total} ({turn_reprs})")

    # --- Determine next player ---
    if session.get('teams_mode'):
        # Team order: 1 -> 2 -> 3 -> 4 -> 1
        session['current_player'] = (session['current_player'] % 4) + 1
    else:
        # Standard 2-player order: 1 -> 2 -> 1
        session['current_player'] = 2 if session['current_player'] == 1 else 1

    session['turn_scores'] = []

    # --- Update message and suggestions for the new player ---
    current_player_num = session['current_player']
    player_name = session[f"player{current_player_num}_name"]

    # Determine current team (Team 1 for players 1 & 3, Team 2 for players 2 & 4)
    current_team = 1 if current_player_num in [1, 3] else 2

    if session['game_mode'] == 'around_the_world':
        team_target_key = f"team{current_team}_target"
        team_target = session[team_target_key]
        target_display = _get_target_display(team_target)
        if not session.get('is_bust_turn'):
            session['message'] = f"{player_name} to throw for {target_display}."
        session['checkout_suggestions'] = []
    else:
        team_score_key = f"team{current_team}_score"
        team_score = session[team_score_key]
        session['checkout_suggestions'] = get_checkout_suggestions(team_score, 3)
        if not session.get('is_bust_turn'):
            session['message'] = f"{player_name} to throw."
            
    session['is_bust_turn'] = False # Reset bust flag for the new turn, after all message logic

# --- API Endpoints ---

@app.route('/api/state')
def get_state():
    """Get the current game state. Initializes a game if one isn't started."""
    if 'game_mode' not in session:
        _start_game('501')
    return jsonify(dict(session))

@app.route('/api/score', methods=['POST'])
def record_score():
    """
    Main endpoint to handle a thrown dart.
    This applies the Darts 501 rules (bust, win on double).
    """
    if session.get('game_over', False):
        return jsonify(dict(session))

    data = request.json
    base_score = int(data.get('base_score', 0))
    multiplier = int(data.get('multiplier', 1))
    score = base_score * multiplier

    throw_repr = get_throw_string(base_score, multiplier)
    throw_data = {'score': score, 'repr': throw_repr}

    # Save the current state *before* making changes, so 'undo' works
    _save_state_to_history()

    current_player_num = session['current_player']
    player_name = session[f"player{current_player_num}_name"]
    current_team = 1 if current_player_num in [1, 3] else 2

    # --- Around the World Logic ---
    if session.get('game_mode') == 'around_the_world':
        team_target_key = f"team{current_team}_target"
        current_target = session[team_target_key]

        session['turn_scores'].append(throw_data)

        if base_score == current_target:
            # Team hit their target
            next_target = current_target + 1
            if current_target == 20:
                next_target = 25 # Bull is next
            
            if current_target == 25: # Hit the final bull
                session['game_over'] = True
                session['winner'] = current_team
                session['message'] = f"GAME SHOT! {player_name} wins Around the World!"
                return jsonify(dict(session))

            # Advance the team's target
            session[team_target_key] = next_target
            target_display = _get_target_display(next_target)
            session['message'] = f"{player_name} hit {current_target}! Now on {target_display}."
        else:
            # Missed the target
            target_display = _get_target_display(current_target)
            session['message'] = f"{player_name} needs {target_display}."

        # Check if turn is over (3 darts thrown)
        if len(session['turn_scores']) == 3:
            _next_player()
        
        return jsonify(dict(session))


    # --- 501/X01 Logic ---
    if session.get('game_mode') == 'around_the_world':
        # This block should not be reached if the above block is correct, but as a safeguard:
        return jsonify(dict(session))

    team_score_key = f"team{current_team}_score"
    current_team_score = session[team_score_key]
    remaining_score = current_team_score - score

    is_bust = False

    # Check for bust conditions
    if remaining_score < 0: # Score goes below zero
        is_bust = True
    elif remaining_score == 1: # Cannot checkout from a score of 1
        is_bust = True
    elif session['win_on_double'] and remaining_score == 0 and multiplier != 2: # Must finish on a double
        is_bust = True # Must finish on a double

    if is_bust:
        # On a bust, the player's score reverts to what it was at the start of their turn.
        history = session.get('history', [])
        # The state before the current turn started is the one we want.
        # Since we save state *before* each throw, the start of the turn is
        # the state right before the first dart of this turn was recorded.
        # The number of darts thrown so far is len(session['turn_scores']).
        # The history list includes the current (partial) turn's states.
        # So we need to go back len(turn_scores) + 1 states in history.
        turn_start_index = max(0, len(history) - len(session['turn_scores']) - 1)
        turn_start_state = history[turn_start_index]
        
        # Add the busting throw to the list to be logged
        session['turn_scores'].append(throw_data) 
        
        # Log the bust turn immediately
        turn_reprs = " ".join(item['repr'] for item in session['turn_scores'])
        session.get('turn_log', []).insert(0, f"{player_name}: BUST ({turn_reprs})")

        # Revert score and set message
        session[team_score_key] = turn_start_state[team_score_key]
        session['message'] = f"{player_name} BUST! Score reset for turn."
        session['is_bust_turn'] = True # Flag this turn as a bust to prevent double-logging
        _next_player()
        return jsonify(dict(session))

    # Check for a win
    is_win = (remaining_score == 0 and (multiplier == 2)) # Double out is always required
    if is_win:
        session[team_score_key] = 0
        session['game_over'] = True
        session['winner'] = current_team
        team_name = f"Team {current_team}"
        session['message'] = f"GAME SHOT! {player_name} wins for {team_name}!"
        
        # Append the final throw and log the winning turn
        session['turn_scores'].append(throw_data)
        turn_total = sum(item['score'] for item in session['turn_scores'])
        turn_reprs = " ".join(item['repr'] for item in session['turn_scores'])
        session.get('turn_log', []).insert(0, f"{player_name}: {turn_total} ({turn_reprs})")

        return jsonify(dict(session))

    # Valid score (no bust, no win)
    session[team_score_key] = remaining_score
    
    session['turn_scores'].append(throw_data)
    darts_left_for_next_throw = 3 - len(session['turn_scores'])
    session['checkout_suggestions'] = get_checkout_suggestions(remaining_score, darts_left_for_next_throw)
    session['message'] = f"{player_name} scored {score}." # player_name is already defined

    # Check if turn is over (3 darts thrown)
    if len(session['turn_scores']) == 3:
        _next_player()
    
    return jsonify(dict(session))

@app.route('/api/undo', methods=['POST'])
def undo_score():
    """Reverts the game state to the previous state from history."""
    if session.get('game_over', False):
        return jsonify(dict(session))

    history = session.get('history', [])
    if len(history) > 1:
        # Remove the current state, leaving the previous state at the end
        history.pop()  
        last_state = history[-1] # Peek at the new last state
        # Update the session with the values from the last state
        session.clear()
        session.update(last_state)
        session['message'] = "Undo successful. Last throw reverted."
    elif len(history) == 1:
        # This is the initial state, can't undo past it
        session['message'] = "Cannot undo further."
    
    return jsonify(dict(session))

@app.route('/api/reset', methods=['POST'])
def reset_game():
    """Resets the game to a new mode (501, 401, etc.)."""
    game_mode = str(request.json.get('mode', '501'))
    if game_mode not in ['101', '201', '301', '401', '501', 'around_the_world']:
        game_mode = '501' # Default to 501 if an invalid mode is passed
    _start_game(game_mode)
    return jsonify(dict(session))

@app.route('/api/names', methods=['POST'])
def update_names():
    """Updates the player names in the session."""
    data = request.json
    name_map = {}
    new_names = {}

    for i in range(1, 5):
        player_key = f'player{i}_name'
        old_name = session.get(player_key, '')
        new_name = data.get(player_key, old_name).strip()
        if not new_name: # Ensure name isn't empty
            new_name = old_name or f"Player {i}"
        
        if old_name != new_name:
            name_map[old_name] = new_name
        
        new_names[player_key] = new_name

    # Update names in the current session
    session.update(new_names)

    # Update names in the turn log and history if there were changes
    if name_map:
        # Update turn log
        new_turn_log = []
        for log_item in session.get('turn_log', []):
            for old, new in name_map.items():
                log_item = log_item.replace(f"{old}:", f"{new}:")
            new_turn_log.append(log_item)
        session['turn_log'] = new_turn_log

    # Refresh the message bar with the potentially new name
    # This is a trick to regenerate the message without changing the player
    session['message'] = session['message'].replace(list(name_map.keys())[0], list(name_map.values())[0]) if name_map else session['message']

    return jsonify(dict(session))

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Updates game settings, like teams mode."""
    data = request.json
    if 'teams_mode' in data:
        session['teams_mode'] = bool(data['teams_mode'])
    # Reset the game with the new setting
    _start_game(session.get('game_mode', '501'))
    return jsonify(dict(session))

@app.route('/api/stats')
def get_stats():
    """Calculates and returns game statistics from the turn log."""
    if 'turn_log' not in session:
        return jsonify({'error': 'No game data available.'}), 404

    stats = {}
    player_names = []
    if session.get('teams_mode'):
        player_names = [session.get(f'player{i}_name') for i in range(1, 5)]
    else:
        player_names = [session.get(f'player{i}_name') for i in range(1, 3)]

    # Initialize stats dictionary for active players
    for name in player_names:
        if name: # Ensure name is not None
            stats[name] = {'total_score': 0, 'darts_thrown': 0, 'average': 0.0}

    for log_item in session['turn_log']:
        try:
            player_name, rest = log_item.split(':', 1)
            player_name = player_name.strip()

            if player_name not in stats:
                continue

            score_part, throws_part = rest.split('(', 1)
            score_part = score_part.strip()
            
            # Count darts thrown in the turn
            throws = throws_part.replace(')', '').strip().split()
            stats[player_name]['darts_thrown'] += len(throws)

            # Add score (0 for a bust)
            if score_part.upper() != 'BUST':
                stats[player_name]['total_score'] += int(score_part)
        except (ValueError, IndexError):
            continue # Skip malformed log entries

    for name, player_stats in stats.items():
        if player_stats['darts_thrown'] > 0:
            player_stats['average'] = (player_stats['total_score'] / player_stats['darts_thrown']) * 3
    return jsonify(stats)

# --- Frontend (HTML/CSS/JS) ---

# This is the main HTML template.
# It uses Tailwind CSS for styling and JavaScript for interactivity.
with open('templates/index.html') as f:
    HTML_TEMPLATE = f.read()
    
@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template_string(HTML_TEMPLATE)

# --- Run the App ---
if __name__ == '__main__':
    # We set debug=False for a cleaner console, but for development,
    # you might want to set debug=True to get auto-reloads.
    app.run(debug=True, host='0.0.0.0', port=5054)
