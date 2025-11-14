import os
from flask import Flask, render_template_string, jsonify, request, session

# Initialize the Flask app
app = Flask(__name__)
# A secret key is required for Flask to use 'session'
# We use os.urandom for a secure, random key each time the app starts
app.secret_key = os.urandom(24)

# --- App Logic ---

# A dictionary of common checkouts for scores 170 and under.
CHECKOUTS = {
    170: ["T20, T20, Bull"], 167: ["T20, T19, Bull"], 164: ["T20, T18, Bull"], 161: ["T20, T17, Bull"],
    160: ["T20, T20, D20"], 158: ["T20, T20, D19"], 157: ["T20, T19, D20"], 156: ["T20, T20, D18"],
    155: ["T20, T19, D19"], 154: ["T20, T18, D20"], 153: ["T20, T19, D18"], 152: ["T20, T20, D16"],
    151: ["T20, T17, D20"], 150: ["T20, T18, D18"], 149: ["T20, T19, D16"], 148: ["T20, T16, D20"],
    147: ["T20, T17, D18"], 146: ["T20, T18, D16"], 145: ["T20, T15, D20"], 144: ["T20, T20, D12"],
    143: ["T20, T17, D16"], 142: ["T20, T14, D20"], 141: ["T20, T19, D12"], 140: ["T20, T20, D10"],
    139: ["T19, T14, D20"], 138: ["T20, T18, D12"], 137: ["T19, T16, D16"], 136: ["T20, T20, D8"],
    135: ["T20, T17, D12"], 134: ["T20, T14, D16"], 133: ["T20, T19, D8"], 132: ["T20, T16, D12"],
    131: ["T20, T13, D16"], 130: ["T20, T20, D5"], 129: ["T19, T16, D12"], 128: ["T18, T14, D16"],
    127: ["T20, T17, D8"], 126: ["T19, T19, D6"], 125: ["Bull, T15, D20"], 124: ["T20, S14, D20"],
    123: ["T19, S16, D20"], 122: ["T18, S20, D14"], 121: ["T20, S11, D20"], 120: ["T20, S20, D20"],
    119: ["T19, S12, D20"], 118: ["T20, S18, D20"], 117: ["T20, S17, D20"], 116: ["T20, S16, D20"],
    115: ["T20, S15, D20"], 114: ["T20, S14, D16"], 113: ["T19, S16, D16"], 112: ["T20, S12, D16"],
    111: ["T20, S11, D16"], 110: ["T20, S10, D20"], 109: ["T19, S12, D16"], 108: ["T20, S16, D16"],
    107: ["T19, S10, D20"], 106: ["T20, S6, D20"], 105: ["T20, S5, D20"], 104: ["T18, S18, D16"],
    103: ["T19, S6, D20"], 102: ["T20, S2, D20"], 101: ["T17, S10, D20"], 100: ["T20, D20"],
    99: ["T19, S10, D16"], 98: ["T20, D19"], 97: ["T19, D20"], 96: ["T20, D18"], 95: ["T19, D19"],
    94: ["T18, D20"], 93: ["T19, D18"], 92: ["T20, D16"], 91: ["T17, D20"], 90: ["T20, D15"],
    89: ["T19, D16"], 88: ["T20, D14"], 87: ["T17, D18"], 86: ["T18, D16"], 85: ["T15, D20"],
    84: ["T20, D12"], 83: ["T17, D16"], 82: ["T14, D20"], 81: ["T19, D12"], 80: ["T20, D10"],
    80: ["T16, D16"], 79: ["T13, D20"], 78: ["T18, D12"], 77: ["T19, D10"], 76: ["T20, D8"],
    75: ["T17, D12"], 74: ["T14, D16"], 73: ["T19, D8"], 72: ["T16, D12"], 71: ["T13, D16"],
    70: ["T10, D20"], 69: ["T19, D6"], 68: ["T20, D4"], 67: ["T17, D8"], 66: ["T10, D18"],
    65: ["T19, D4"], 64: ["T16, D8"], 63: ["T13, D12"], 62: ["T10, D16"], 61: ["T15, D8"],
    60: ["S20, D20"], 59: ["S19, D20"], 58: ["S18, D20"], 57: ["S17, D20"], 56: ["S16, D20"],
    55: ["S15, D20"], 54: ["S14, D20"], 53: ["S13, D20"], 52: ["S12, D20"], 51: ["S11, D20"],
    50: ["S10, D20"], 49: ["S9, D20"], 48: ["S8, D20"], 47: ["S7, D20"], 46: ["S6, D20"],
    45: ["S5, D20"], 44: ["S4, D20"], 43: ["S3, D20"], 42: ["S2, D20"], 41: ["S1, D20"],
    40: ["D20"], 39: ["S7, D16"], 38: ["D19"], 37: ["S5, D16"], 36: ["D18"], 35: ["S3, D16"],
    34: ["D17"], 33: ["S1, D16"], 32: ["D16"], 31: ["S15, D8"], 30: ["D15"], 29: ["S13, D8"],
    28: ["D14"], 27: ["S19, D4"], 26: ["D13"], 25: ["S17, D4"], 24: ["D12"], 23: ["S7, D8"],
    22: ["D11"], 21: ["S5, D8"], 20: ["D10"], 19: ["S3, D8"], 18: ["D9"], 17: ["S1, D8"],
    16: ["D8"], 15: ["S7, D4"], 14: ["D7"], 13: ["S5, D4"], 12: ["D6"], 11: ["S3, D4"],
    10: ["D5"], 9: ["S1, D4"], 8: ["D4"], 7: ["S3, D2"], 6: ["D3"], 5: ["S1, D2"], 4: ["D2"], 3: ["S1, D1"], 2: ["D1"]
}

def get_checkout_suggestions(score, darts_left=3):
    """Returns a list of checkout suggestions for a given score and number of darts remaining."""
    if 1 < score <= 170:
        all_suggestions = CHECKOUTS.get(score, [])
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
    
    # Keep history from growing too large (e.g., last 20 states)
    if len(history_list) > 20:
        history_list = history_list[-20:]
        
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
    session['is_bust_turn'] = False # Reset bust flag for the new turn

    # --- Update message and suggestions for the new player ---
    current_player_num = session['current_player']
    player_name = session[f"player{current_player_num}_name"]

    # Determine current team (Team 1 for players 1 & 3, Team 2 for players 2 & 4)
    current_team = 1 if current_player_num in [1, 3] else 2

    if session['game_mode'] == 'around_the_world':
        team_target_key = f"team{current_team}_target"
        team_target = session[team_target_key]
        target_display = _get_target_display(team_target)
        session['message'] = f"{player_name} to throw for {target_display}."
        session['checkout_suggestions'] = []
    else:
        team_score_key = f"team{current_team}_score"
        team_score = session[team_score_key]
        session['checkout_suggestions'] = get_checkout_suggestions(team_score, 3)
        session['message'] = f"{player_name} to throw."

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
        # Find the last state where it was the other player's turn, or the very first state.
        # This marks the beginning of the current player's turn.
        turn_start_state = history[0] # Default to the beginning of the game
        for state in reversed(history):
            if state['current_player'] != current_player_num:
                turn_start_state = state
                break
        
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
    session['player1_name'] = data.get('player1_name', 'T1 Player 1').strip() or 'T1 Player 1'
    session['player2_name'] = data.get('player2_name', 'T2 Player 1').strip() or 'T2 Player 1'
    session['player3_name'] = data.get('player3_name', 'T1 Player 2').strip() or 'T1 Player 2'
    session['player4_name'] = data.get('player4_name', 'T2 Player 2').strip() or 'T2 Player 2'
    # Refresh the message bar with the new name if it's their turn
    _next_player() # This is a bit of a hack, but it correctly sets the message
    _next_player() # Call it twice to get back to the original player
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

    p1_name = session.get('player1_name', 'Player 1')
    p2_name = session.get('player2_name', 'Player 2')
    p3_name = session.get('player3_name', 'Player 3')
    p4_name = session.get('player4_name', 'Player 4')

    stats = {
        p1_name: {'total_score': 0, 'darts_thrown': 0, 'average': 0.0},
        p2_name: {'total_score': 0, 'darts_thrown': 0, 'average': 0.0}
    }
    if session.get('teams_mode'):
        stats[p3_name] = {'total_score': 0, 'darts_thrown': 0, 'average': 0.0}
        stats[p4_name] = {'total_score': 0, 'darts_thrown': 0, 'average': 0.0}
    else: # In 2-player mode, we might have old names in the log, so map them.
        stats[p3_name] = stats[p1_name]
        stats[p4_name] = stats[p2_name]

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
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Darts Scorer</title>
    <!-- Load Tailwind CSS from CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* Custom styles for a better look */
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(to bottom right, #1f2937, #111827);
            touch-action: manipulation; /* Disable double-tap to zoom on mobile */
        }
        /* Custom styles for the toggle switch */
        .toggle-checkbox:checked { @apply bg-green-500; right: 0; border-color: #10B981; }
        .toggle-checkbox:checked + .toggle-label { @apply bg-green-500; }
        .toggle-checkbox {
            @apply absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer;
        }
        .toggle-label {
            @apply block overflow-hidden h-5 rounded-full bg-gray-600 cursor-pointer;
        }

        /* --- Glassmorphism UI Overhaul --- */
        .glass-panel {
            @apply bg-black/20 backdrop-blur-xl border border-white/10 rounded-xl shadow-lg;
        }

        .score-btn, .ctrl-btn, .multi-btn { /* New Button Base Style */
            @apply w-full h-14 flex items-center justify-center rounded-lg font-bold text-lg text-white;
            @apply border border-black/20 shadow-lg;
            @apply transition-all duration-150 active:scale-95;
        }
        .score-btn {
            @apply bg-gradient-to-b from-gray-700 to-gray-800 hover:from-gray-600;
        }
        .ctrl-btn {
            @apply bg-gradient-to-b from-rose-700 to-rose-800 hover:from-rose-600;
        }
        .multi-btn {
            @apply bg-gradient-to-b from-indigo-700 to-indigo-800 hover:from-indigo-600;
        }
        .multi-btn.active {
            @apply from-sky-400 to-sky-500 text-black border-sky-300 ring-2 ring-white;
        }
        .player-name-input.active {
            @apply text-amber-300;
        }
        .player-name-input:not(.active) {
            @apply text-gray-400;
        }
        .player-board {
            @apply w-1/2 p-4 text-center transition-all glass-panel;
        }
        .player-board.active {
            @apply border-amber-400/80;
        }
        .player-board.inactive {
            @apply border-white/10;
        }

        /* --- Dropdown Style --- */
        select option {
            background: #1f2937; /* bg-gray-800 */
        }

        /* --- Stats Modal --- */
        .modal-overlay {
            @apply fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4;
            @apply transition-opacity duration-300;
        }
        .modal-content {
            @apply glass-panel p-6 rounded-2xl w-full max-w-md;
            @apply transform transition-transform duration-300 scale-95;
        }
        .modal-overlay:not(.hidden) .modal-content {
            @apply scale-100;
        }
    </style>
</head>
<body class="bg-gray-900 text-white min-h-screen p-4">

    <div class="container mx-auto max-w-lg">
        
        <!-- Header & New Game -->
        <header class="flex justify-between items-center mb-4">
            <h1 class="text-4xl font-bold">Darts Scorer</h1>
            <div class="flex items-center space-x-4">
                <div id="teams_mode_container" class="flex items-center space-x-2">
                     <span class="text-sm font-semibold text-gray-300">Teams Mode</span>
                     <div class="relative inline-block w-10 align-middle select-none transition duration-200 ease-in">
                         <input type="checkbox" name="teams_mode_toggle" id="teams_mode_toggle" class="toggle-checkbox border-gray-400"/>
                         <label for="teams_mode_toggle" class="toggle-label"></label>
                     </div>
                </div>

                <div class="relative">
                    <select id="gameModeSelect" class="h-12 px-2 rounded-lg font-semibold glass-panel text-black outline-none focus:ring-2 focus:ring-sky-400 appearance-none">
                        <option value="around_the_world">Around the World</option>
                        <option value="501">501</option>
                        <option value="401">401</option>
                        <option value="301">301</option>
                        <option value="201">201</option>
                        <option value="101">101</option>
                    </select>
                    <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-400">
                        <svg class="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
                    </div>
                </div>
                <button id="statsBtn" class="w-28 h-12 ctrl-btn">Stats</button>
                <button id="newGameBtn" class="w-32 h-12 flex items-center justify-center rounded-lg font-bold text-lg text-white
                                             bg-green-500/50 border border-green-400/60 shadow-md
                                             transition-all duration-150 hover:bg-green-500/60 hover:shadow-lg hover:shadow-green-400/30
                                             active:scale-95 active:bg-green-500/70">
                    New Game
                </button>
            </div>
        </header>

        <!-- Scoreboard -->
        <div class="flex space-x-4 mb-4">
            <div id="team1_board" class="player-board inactive">
                <h2 class="text-lg font-bold mb-2">Team 1</h2>
                <input id="p1_name_input" type="text" value="Player 1" class="player-name-input w-full bg-transparent text-center text-base font-semibold p-1 rounded-md outline-none transition-colors focus:bg-white/10 focus:ring-1 focus:ring-amber-400">
                <input id="p3_name_input" type="text" value="Player 3" class="player-name-input w-full bg-transparent text-center text-base font-semibold p-1 rounded-md outline-none transition-colors focus:bg-white/10 focus:ring-1 focus:ring-amber-400">
                <div id="team1_score" class="text-7xl font-bold mt-2">501</div>
            </div>
            <div id="team2_board" class="player-board inactive">
                <h2 class="text-lg font-bold mb-2">Team 2</h2>
                <input id="p2_name_input" type="text" value="Player 2" class="player-name-input w-full bg-transparent text-center text-base font-semibold p-1 rounded-md outline-none transition-colors focus:bg-white/10 focus:ring-1 focus:ring-amber-400">
                <input id="p4_name_input" type="text" value="Player 4" class="player-name-input w-full bg-transparent text-center text-base font-semibold p-1 rounded-md outline-none transition-colors focus:bg-white/10 focus:ring-1 focus:ring-amber-400">
                <div id="team2_score" class="text-7xl font-bold mt-2">501</div>
            </div>
        </div>

        <!-- Message Bar -->
        <div id="message_bar" class="text-center text-lg font-medium p-3 mb-4 h-12 flex items-center justify-center glass-panel">
            Loading...
        </div>

        <!-- Current Turn Display -->
        <div class="mb-4">
            <h3 class="text-sm font-semibold text-gray-400">Current Turn:</h3>
            <div id="current_turn_display" class="flex items-center space-x-2 h-8 text-xl font-mono">
                <!-- Scores like [100] [60] [20] will appear here -->
            </div>
        </div>

        <!-- Checkout Suggestions -->
        <div id="checkout_container" class="mb-4 hidden">
            <h3 class="text-sm font-semibold text-gray-400">Checkout:</h3>
            <div id="checkout_suggestions" class="flex items-center space-x-4 h-8 text-lg font-mono text-amber-300 flex-wrap">
                <!-- Suggestions like T20, T20, Bull will appear here -->
            </div>
        </div>

        <!-- Multiplier Buttons -->
        <div class="grid grid-cols-2 gap-2 mb-2">
            <button id="btn_double" class="multi-btn" data-multiplier="2">DOUBLE (D)</button>
            <button id="btn_triple" class="multi-btn" data-multiplier="3">TRIPLE (T)</button>
        </div>

        <!-- Score Input Buttons -->
        <div class="grid grid-cols-7 gap-2">
            <!-- Programmatically generated buttons will be better -->
            <!-- We'll keep it simple for now -->
            <button class="score-btn" data-score="20">20</button>
            <button class="score-btn" data-score="19">19</button>
            <button class="score-btn" data-score="18">18</button>
            <button class="score-btn" data-score="17">17</button>
            <button class="score-btn" data-score="16">16</button>
            <button class="score-btn" data-score="15">15</button>
            <button class="score-btn" data-score="14">14</button>
            <button class="score-btn" data-score="13">13</button>
            <button class="score-btn" data-score="12">12</button>
            <button class="score-btn" data-score="11">11</button>
            <button class="score-btn" data-score="10">10</button>
            <button class="score-btn" data-score="9">9</button>
            <button class="score-btn" data-score="8">8</button>
            <button class="score-btn" data-score="7">7</button>
            <button class="score-btn" data-score="6">6</button>
            <button class="score-btn" data-score="5">5</button>
            <button class="score-btn" data-score="4">4</button>
            <button class="score-btn" data-score="3">3</button>
            <button class="score-btn" data-score="2">2</button>
            <button class="score-btn" data-score="1">1</button>
            <button class="score-btn" data-score="25">OUTER BULL (25)</button>
            <button id="btn_bull" class="score-btn">DBL BULL (50)</button>
            <button class="score-btn" data-score="0">MISS (0)</button>
            <button id="btn_undo" class="ctrl-btn col-span-4">UNDO THROW</button>
        </div>

        <!-- Turn History -->
        <div class="mt-6">
            <h3 class="text-lg font-semibold text-gray-300 border-b border-white/10 pb-2 mb-3">Turn History</h3>
            <div id="turn_history_log" class="text-gray-300 font-mono text-sm space-y-2 max-h-48 overflow-y-auto p-2">
                <!-- History items will be injected here -->
            </div>
        </div>

    </div>

    <!-- Stats Modal -->
    <div id="statsModal" class="modal-overlay hidden">
        <div class="modal-content">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-2xl font-bold">Game Statistics</h2>
                <button id="closeStatsBtn" class="text-2xl font-bold text-gray-400 hover:text-white">&times;</button>
            </div>
            <div id="statsContent" class="space-y-4">
                <!-- Stats will be injected here -->
                <div class="text-center p-4">Loading stats...</div>
            </div>
        </div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', () => {
            let currentMultiplier = 1;
            let activeMultiplierButton = null;
            let isGameRunning = true;

            const team1Board = document.getElementById('team1_board');
            const team1Score = document.getElementById('team1_score');
            const team2Board = document.getElementById('team2_board');
            const team2Score = document.getElementById('team2_score');

            const p1NameInput = document.getElementById('p1_name_input');
            const p2NameInput = document.getElementById('p2_name_input');
            const p3NameInput = document.getElementById('p3_name_input');
            const p4NameInput = document.getElementById('p4_name_input');

            const messageBar = document.getElementById('message_bar');
            const turnDisplay = document.getElementById('current_turn_display');
            const checkoutContainer = document.getElementById('checkout_container');
            const checkoutSuggestions = document.getElementById('checkout_suggestions');
            const turnHistoryLog = document.getElementById('turn_history_log');
            
            const btnDouble = document.getElementById('btn_double');
            const btnTriple = document.getElementById('btn_triple');
            const btnUndo = document.getElementById('btn_undo');
            const btnBull = document.getElementById('btn_bull');
            const btnNewGame = document.getElementById('newGameBtn');
            const gameModeSelect = document.getElementById('gameModeSelect');
            const statsBtn = document.getElementById('statsBtn');
            const statsModal = document.getElementById('statsModal');
            const closeStatsBtn = document.getElementById('closeStatsBtn');
            const teamsModeToggle = document.getElementById('teams_mode_toggle');

            // Function to update the entire UI from a state object
            function updateUI(state) {
                team1Score.textContent = state.team1_score;
                team2Score.textContent = state.team2_score;
                p1NameInput.value = state.player1_name;
                p2NameInput.value = state.player2_name;
                p3NameInput.value = state.player3_name;
                p4NameInput.value = state.player4_name;
                messageBar.textContent = state.message; 
                teamsModeToggle.checked = state.teams_mode;

                // Show/hide player name inputs based on teams mode
                p3NameInput.classList.toggle('hidden', !state.teams_mode);
                p4NameInput.classList.toggle('hidden', !state.teams_mode);

                // Show/hide UI elements based on game mode
                if (state.game_mode === 'around_the_world') {
                    checkoutContainer.classList.add('hidden');
                    // Update score display to show target number
                    const t1Target = state.team1_target > 20 ? 'Bull' : state.team1_target;
                    const t2Target = state.team2_target > 20 ? 'Bull' : state.team2_target;
                    team1Score.textContent = t1Target;
                    team2Score.textContent = t2Target;
                    team1Score.classList.remove('text-7xl'); team1Score.classList.add('text-5xl');
                    team2Score.classList.remove('text-7xl'); team2Score.classList.add('text-5xl');
                } else { // 501, 301, etc.
                    team1Score.classList.add('text-7xl'); team1Score.classList.remove('text-5xl');
                    team2Score.classList.add('text-7xl'); team2Score.classList.remove('text-5xl');
                }

                // Clear all active states first
                [team1Board, team2Board, p1NameInput, p2NameInput, p3NameInput, p4NameInput].forEach(el => {
                    el.classList.remove('active', 'inactive');
                });

                // Update active player highlight
                const currentPlayerNum = state.current_player;
                const activePlayerInput = document.getElementById(`p${currentPlayerNum}_name_input`);
                if (activePlayerInput) {
                    activePlayerInput.classList.add('active');
                }

                // Highlight active team board
                if ([1, 3].includes(currentPlayerNum)) { // Team 1
                    team1Board.classList.add('active');
                    team2Board.classList.add('inactive');
                } else { // Team 2
                    team2Board.classList.add('active');
                    team1Board.classList.add('inactive');
                }

                // Update current turn display
                turnDisplay.innerHTML = '';
                state.turn_scores.forEach(throw_data => {
                    const scoreEl = document.createElement('span');
                    scoreEl.className = 'font-semibold';
                    scoreEl.textContent = `[${throw_data.repr}]`;
                    turnDisplay.appendChild(scoreEl);
                });

                // Update checkout suggestions
                if (state.game_mode !== 'around_the_world' && Array.isArray(state.checkout_suggestions) && state.checkout_suggestions.length > 0) {
                    checkoutSuggestions.innerHTML = '';
                    state.checkout_suggestions.forEach(suggestion => {
                        const suggestionEl = document.createElement('span');
                        suggestionEl.className = 'font-semibold bg-black/20 px-2 py-1 rounded';
                        suggestionEl.textContent = suggestion;
                        checkoutSuggestions.appendChild(suggestionEl);
                    });
                    checkoutContainer.classList.remove('hidden');
                } else {
                    checkoutContainer.classList.add('hidden');
                }

                // Update turn history
                turnHistoryLog.innerHTML = '';
                if (state.turn_log && state.turn_log.length > 0) {
                    state.turn_log.forEach(log_item => {
                        const logEl = document.createElement('div');
                        logEl.textContent = log_item;
                        turnHistoryLog.appendChild(logEl);
                    });
                }

                // Handle game over
                isGameRunning = !state.game_over;
                if (state.game_over) {
                    messageBar.classList.add('bg-green-500/50', 'text-2xl', 'font-bold');
                    team1Board.classList.remove('active', 'inactive');
                    team2Board.classList.remove('active', 'inactive');
                    team1Board.classList.remove('border-green-400/80'); // Clear old winner
                    team2Board.classList.remove('border-green-400/80'); // Clear old winner
                    [p1NameInput, p2NameInput, p3NameInput, p4NameInput].forEach(el => el.classList.remove('active'));

                    if (state.winner === 1) {
                        team1Board.classList.add('border-green-400/80');
                    } else if (state.winner === 2) { // Winner is a team number
                        team2Board.classList.add('border-green-400/80');
                    }
                } else {
                    messageBar.classList.remove('bg-green-500/50', 'text-2xl', 'font-bold');
                }
            }

            // Reset multiplier button visual state
            function resetMultiplier() {
                currentMultiplier = 1;
                if (activeMultiplierButton) {
                    activeMultiplierButton.classList.remove('active');
                    activeMultiplierButton = null;
                }
            }

            // Handle clicking a score button (0-20, 25)
            async function handleScoreClick(baseScore, multiplierOverride = null) {
                if (!isGameRunning) return;

                const payload = {
                    base_score: baseScore,
                    multiplier: multiplierOverride || currentMultiplier
                };

                try {
                    const response = await fetch('/api/score', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const state = await response.json();
                    updateUI(state);
                } catch (err) {
                    messageBar.textContent = "Error connecting to server.";
                }

                resetMultiplier();
            }

            // Handle clicking Double or Triple
            function handleMultiplierClick(multiplier, button) {
                if (!isGameRunning) return;

                if (activeMultiplierButton === button) {
                    // Clicked the same button, so deselect it
                    resetMultiplier();
                } else {
                    // Deselect old button, select new one
                    resetMultiplier();
                    currentMultiplier = multiplier;
                    activeMultiplierButton = button;
                    button.classList.add('active');
                }
            }

            // Handle Undo
            btnUndo.addEventListener('click', async () => {
                if (sessionStorage.getItem('reloading')) return; // Prevent double clicks
                sessionStorage.setItem('reloading', 'true');

                try {
                    const response = await fetch('/api/undo', { method: 'POST' });
                    const state = await response.json();
                    updateUI(state);
                } catch (err) {
                    messageBar.textContent = "Error connecting to server.";
                }
                resetMultiplier();
                sessionStorage.removeItem('reloading');
            });

            // Handle New Game
            btnNewGame.addEventListener('click', async () => {
                if (sessionStorage.getItem('reloading')) return;
                sessionStorage.setItem('reloading', 'true');
                
                const mode = gameModeSelect.value;
                try {
                    const response = await fetch('/api/reset', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mode: mode })
                    });
                    const state = await response.json();
                    updateUI(state);
                } catch (err) {
                    messageBar.textContent = "Error connecting to server.";
                }
                resetMultiplier();
                sessionStorage.removeItem('reloading');
            });

            // --- Stats Modal Logic ---
            statsBtn.addEventListener('click', async () => {
                statsModal.classList.remove('hidden');
                document.getElementById('statsContent').innerHTML = '<div class="text-center p-4">Loading stats...</div>';
                
                try {
                    const response = await fetch('/api/stats');
                    if (!response.ok) throw new Error('Failed to load stats');
                    const stats = await response.json();
                    
                    const statsContent = document.getElementById('statsContent');
                    statsContent.innerHTML = ''; // Clear loading message

                    Object.entries(stats).forEach(([playerName, data]) => {
                        const playerStatEl = document.createElement('div');
                        playerStatEl.className = 'p-4 bg-black/20 rounded-lg';
                        playerStatEl.innerHTML = `
                            <h3 class="text-xl font-semibold text-amber-300">${playerName}</h3>
                            <div class="grid grid-cols-2 gap-2 mt-2 text-lg">
                                <div>
                                    <div class="text-sm text-gray-400">3-Dart Avg</div>
                                    <div class="font-bold text-2xl">${data.average.toFixed(2)}</div>
                                </div>
                                <div>
                                    <div class="text-sm text-gray-400">Darts Thrown</div>
                                    <div class="font-bold text-2xl">${data.darts_thrown}</div>
                                </div>
                            </div>
                        `;
                        statsContent.appendChild(playerStatEl);
                    });

                } catch (err) {
                    document.getElementById('statsContent').textContent = 'Could not load statistics.';
                }
            });

            closeStatsBtn.addEventListener('click', () => {
                statsModal.classList.add('hidden');
            });


            // Handle Name Changes
            async function handleNameChange() {
                // Only send names relevant to the current mode
                const payload = {
                    player1_name: p1NameInput.value,
                    player2_name: p2NameInput.value,
                    player3_name: p3NameInput.value,
                    player4_name: p4NameInput.value,
                };
                try {
                    const response = await fetch('/api/names', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const state = await response.json();
                    updateUI(state); // Update UI with fresh state from server
                } catch (err) {
                    messageBar.textContent = "Error updating names.";
                }
            }
            [p1NameInput, p2NameInput, p3NameInput, p4NameInput].forEach(input => {
                input.addEventListener('blur', handleNameChange);
            });

            // Attach listeners to all score buttons
            document.querySelectorAll('.score-btn').forEach(btn => {
                btn.addEventListener('click', () => handleScoreClick(btn.dataset.score));
            });

            // Attach listeners to multiplier buttons
            btnDouble.addEventListener('click', () => handleMultiplierClick(2, btnDouble));
            btnTriple.addEventListener('click', () => handleMultiplierClick(3, btnTriple));

            // Special handler for Double Bull
            btnBull.addEventListener('click', () => handleScoreClick(25, 2)); // baseScore 25, multiplier 2

            // Handle Teams Mode Toggle
            teamsModeToggle.addEventListener('change', async () => {
                const payload = {
                    teams_mode: teamsModeToggle.checked
                };
                try {
                    const response = await fetch('/api/settings', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const state = await response.json();
                    updateUI(state);
                } catch (err) {
                    messageBar.textContent = "Error updating settings.";
                }
            });

            // Initial state load
            async function initializeApp() {
                try {
                    const response = await fetch('/api/state');
                    const state = await response.json();
                    gameModeSelect.value = state.game_mode;
                    updateUI(state);
                } catch (err) {
                    messageBar.textContent = "Error connecting to server.";
                }
            }
            
            initializeApp();
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template_string(HTML_TEMPLATE)

# --- Run the App ---
if __name__ == '__main__':
    # We set debug=False for a cleaner console, but for development,
    # you might want to set debug=True to get auto-reloads.
    app.run(debug=True, host='0.0.0.0', port=5054)
