import streamlit as st
import pandas as pd

# Function to calculate the value of a hand
def calculate_hand(cards):
    total = sum([min(card, 10) for card in cards]) % 10
    return total

# Function to determine the winner
def determine_winner(player_total, banker_total):
    if player_total > banker_total:
        return "Player"
    elif banker_total > player_total:
        return "Banker"
    else:
        return "Tie"

# Streamlit app
st.title("Baccarat Simulator (Mobile-Optimized)")

# Add a game selector (G1, G2, G3, G4)
game = st.selectbox("Select Game", ["G1", "G2", "G3", "G4"])

# Initialize session state for cumulative wins and round number
if f'cumulative_wins_{game}' not in st.session_state:
    st.session_state[f'cumulative_wins_{game}'] = {"Player": 0, "Banker": 0, "Tie": 0}

if f'round_num_{game}' not in st.session_state:
    st.session_state[f'round_num_{game}'] = 1

if f'player_cards_{game}' not in st.session_state:
    st.session_state[f'player_cards_{game}'] = []

if f'banker_cards_{game}' not in st.session_state:
    st.session_state[f'banker_cards_{game}'] = []

if f'df_game_{game}' not in st.session_state:
    st.session_state[f'df_game_{game}'] = pd.DataFrame(columns=['round_num', 'player_cards', 'banker_cards', 'result', 'player_total', 'banker_total'])

# Available card values (0 to 9)
card_values = list(range(10))

# Horizontal row of numbers for card selection (mobile optimized: 3 numbers per row)
st.subheader(f"Game {game}: Enter Player's Cards (Round {st.session_state[f'round_num_{game}']})")

player_selected = None
if len(st.session_state[f'player_cards_{game}']) < 3:
    st.write("Click on a number to add a card for Player:")
    
    # Arrange buttons in a grid (3 numbers per row)
    for row in range(0, 10, 3):
        cols = st.columns(3)
        for i, col in enumerate(cols):
            if row + i < len(card_values):
                if col.button(f"{card_values[row + i]}", key=f"player_button_{row + i}_{game}", help="Click to add card"):
                    player_selected = card_values[row + i]

if player_selected is not None and len(st.session_state[f'player_cards_{game}']) < 3:
    st.session_state[f'player_cards_{game}'].append(player_selected)

# Allow the user to undo the last card selection for the player
if len(st.session_state[f'player_cards_{game}']) > 0 and st.button("Undo Player's Last Card"):
    st.session_state[f'player_cards_{game}'].pop()

# Display player's selected cards
st.write(f"Player's Hand: {st.session_state[f'player_cards_{game}']}")

# Repeat for the banker, but limit to 3 cards
st.subheader(f"Enter Banker's Cards (Round {st.session_state[f'round_num_{game}']})")

banker_selected = None
if len(st.session_state[f'banker_cards_{game}']) < 3:
    st.write("Click on a number to add a card for Banker:")

    # Arrange buttons in a grid (3 numbers per row)
    for row in range(0, 10, 3):
        cols = st.columns(3)
        for i, col in enumerate(cols):
            if row + i < len(card_values):
                if col.button(f"{card_values[row + i]}", key=f"banker_button_{row + i}_{game}", help="Click to add card"):
                    banker_selected = card_values[row + i]

if banker_selected is not None and len(st.session_state[f'banker_cards_{game}']) < 3:
    st.session_state[f'banker_cards_{game}'].append(banker_selected)

# Allow the user to undo the last card selection for the banker
if len(st.session_state[f'banker_cards_{game}']) > 0 and st.button("Undo Banker's Last Card"):
    st.session_state[f'banker_cards_{game}'].pop()

# Display banker's selected cards
st.write(f"Banker's Hand: {st.session_state[f'banker_cards_{game}']}")

# Enforce that both player and banker must have at least 2 cards before calculating the result
if len(st.session_state[f'player_cards_{game}']) >= 2 and len(st.session_state[f'banker_cards_{game}']) >= 2:
    player_total = calculate_hand(st.session_state[f'player_cards_{game}'])
    banker_total = calculate_hand(st.session_state[f'banker_cards_{game}'])

    # Display totals
    st.write(f"Player's Total: {player_total}")
    st.write(f"Banker's Total: {banker_total}")

    # Determine winner when the user clicks "Confirm"
    if st.button("Confirm"):
        winner = determine_winner(player_total, banker_total)
        st.write(f"Round {st.session_state[f'round_num_{game}']}: {winner} wins!")

        # Create a new row as a DataFrame
        new_row = pd.DataFrame({
            'round_num': [st.session_state[f'round_num_{game}']],
            'player_cards': [st.session_state[f'player_cards_{game}']],
            'banker_cards': [st.session_state[f'banker_cards_{game}']],
            'result': [winner],
            'player_total': [player_total],
            'banker_total': [banker_total]
        })

        # Concatenate the new row with the existing game DataFrame
        st.session_state[f'df_game_{game}'] = pd.concat([st.session_state[f'df_game_{game}'], new_row], ignore_index=True)

        # Update cumulative wins for the selected game
        st.session_state[f'cumulative_wins_{game}'][winner] += 1

        # Calculate proportions and betting decisions for all rounds
        df_game = st.session_state[f'df_game_{game}']
        count_1 = count_2 = count_3 = count_4 = 0
        total_rounds = 0
        last_non_tie = None
        prop_3_threshold_high = 0.32
        prop_4_threshold_high = 0.32
        stopping_threshold = 0.24
        min_below = 0.02
        
        for i, row in df_game.iterrows():
            total_rounds += 1
            
            df_game.at[i, 'new_column'] = None
            if row['result'] != 'Tie':
                if last_non_tie is not None:
                    if row['result'] == 'Player' and df_game.at[last_non_tie, 'result'] == 'Banker':
                        df_game.at[i, 'new_column'] = 1
                    elif row['result'] == 'Banker' and df_game.at[last_non_tie, 'result'] == 'Player':
                        df_game.at[i, 'new_column'] = 2
                    elif row['result'] == 'Player' and df_game.at[last_non_tie, 'result'] == 'Player':
                        df_game.at[i, 'new_column'] = 4
                    elif row['result'] == 'Banker' and df_game.at[last_non_tie, 'result'] == 'Banker':
                        df_game.at[i, 'new_column'] = 3

                last_non_tie = i

            if df_game.at[i, 'new_column'] is None:
                df_game.at[i, 'new_column'] = 0  # For ties, use 0 in new_column
            
            if df_game.at[i, 'new_column'] == 1:
                count_1 += 1
            elif df_game.at[i, 'new_column'] == 2:
                count_2 += 1
            elif df_game.at[i, 'new_column'] == 3:
                count_3 += 1
            elif df_game.at[i, 'new_column'] == 4:
                count_4 += 1

            df_game.at[i, 'proportion_1'] = count_1 / total_rounds
            df_game.at[i, 'proportion_2'] = count_2 / total_rounds
            df_game.at[i, 'proportion_3'] = count_3 / total_rounds
            df_game.at[i, 'proportion_4'] = count_4 / total_rounds

            prop_1 = df_game.at[i, 'proportion_1']
            prop_2 = df_game.at[i, 'proportion_2']
            prop_3 = df_game.at[i, 'proportion_3']
            prop_4 = df_game.at[i, 'proportion_4']

            decision = 'No Bet'

            if (prop_4 < min(prop_1, prop_2, prop_3) - min_below and prop_3 > prop_3_threshold_high and row['round_num'] > 20):
                decision = 'Banker'
            elif (prop_4 > prop_4_threshold_high and prop_3 < min(prop_1, prop_2, prop_4) - min_below):
                decision = 'Player'

            df_game.at[i, 'decision'] = decision

        # Store the updated game DataFrame
        st.session_state[f'df_game_{game}'] = df_game

        # Move to the next round and reset cards
        st.session_state[f'round_num_{game}'] += 1
        st.session_state[f'player_cards_{game}'] = []
        st.session_state[f'banker_cards_{game}'] = []

# Display cumulative wins for the current game
st.subheader(f"Cumulative Wins for {game}")
st.write(f"Player: {st.session_state[f'cumulative_wins_{game}']['Player']}")
st.write(f"Banker: {st.session_state[f'cumulative_wins_{game}']['Banker']}")
st.write(f"Tie: {st.session_state[f'cumulative_wins_{game}']['Tie']}")

# Display current betting decisions, with most recent one at the top (stacked layout)
if f'df_game_{game}' in st.session_state:
    df_game = st.session_state[f'df_game_{game}']
    if len(df_game) > 0:
        st.subheader(f"Betting Decisions for {game}")
        # Reverse the DataFrame to show most recent decision first
        st.write(df_game[['round_num', 'decision']].iloc[::-1])

# Button to reset the game (back to round 1 for the selected game)
if st.button("Reset Game"):
    st.session_state[f'cumulative_wins_{game}'] = {"Player": 0, "Banker": 0, "Tie": 0}
    st.session_state[f'round_num_{game}'] = 1
    st.session_state[f'player_cards_{game}'] = []
    st.session_state[f'banker_cards_{game}'] = []
    st.session_state[f'df_game_{game}'] = pd.DataFrame(columns=['round_num', 'player_cards', 'banker_cards', 'result', 'player_total', 'banker_total'])
    st.write(f"Game {game} reset successfully!")

