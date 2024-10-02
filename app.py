import streamlit as st
import pandas as pd

# Inject custom CSS to adjust button sizes and reduce spacing
st.markdown(
    """
    <style>
    /* Reduce padding and margins of buttons */
    .stButton button {
        height: 40px;
        width: 80px;
        margin: 1px;
        padding: 0px;
        font-size: 16px;
    }
    /* Center the main container */
    .main .block-container {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
        max-width: 100%;
    }
    </style>
    """, 
    unsafe_allow_html=True
)

# Streamlit app
st.title("Baccarat Simulator")

# Add a game selector (G1, G2, G3, G4, G5, G6)
game = st.selectbox("Select Game", ["G1", "G2", "G3", "G4", "G5", "G6"])

# Initialize session state for cumulative wins, round number, proportions, decisions, and profits
if f'cumulative_wins_{game}' not in st.session_state:
    st.session_state[f'cumulative_wins_{game}'] = {"Player": 0, "Banker": 0, "Tie": 0}

if f'round_num_{game}' not in st.session_state:
    st.session_state[f'round_num_{game}'] = 1

if f'proportions_{game}' not in st.session_state:
    st.session_state[f'proportions_{game}'] = {"proportion_1": 0, "proportion_2": 0, "proportion_3": 0, "proportion_4": 0}

if f'df_game_{game}' not in st.session_state:
    st.session_state[f'df_game_{game}'] = pd.DataFrame(columns=['round_num', 'result', 'next_rd_decision', 'profit'])

if f'profit_{game}' not in st.session_state:
    st.session_state[f'profit_{game}'] = 0


# Function to update results, calculate next round's decision, and profit
def update_result(winner):
    round_num = st.session_state[f'round_num_{game}']

    # Add result to game DataFrame
    new_row = pd.DataFrame({
        'round_num': [round_num],
        'result': [winner]
    })
    st.session_state[f'df_game_{game}'] = pd.concat([st.session_state[f'df_game_{game}'], new_row], ignore_index=True)

    # Update cumulative wins
    st.session_state[f'cumulative_wins_{game}'][winner] += 1

    # Proportions and next round decision logic
    df_game = st.session_state[f'df_game_{game}']
    total_rounds = len(df_game)
    count_1 = count_2 = count_3 = count_4 = 0
    prop_3_threshold_high = 0.32
    prop_4_threshold_high = 0.32
    min_below = 0.02
    last_non_tie = None
  

    # Initialize new columns if not present
    if 'new_column' not in df_game.columns:
        df_game['new_column'] = 0
        df_game['proportion_1'] = 0
        df_game['proportion_2'] = 0
        df_game['proportion_3'] = 0
        df_game['proportion_4'] = 0
        df_game['next_rd_decision'] = 'No Bet'
        df_game['profit'] = 0

        # Loop through each round of the game
    for i, row in df_game.iterrows():
        # Increment total_rounds only if the result is not a tie
        if row['result'] != 'Tie':
            total_rounds += 1

            # Initialize new_column based on the game logic
            df_game.at[i, 'new_column'] = None  # Ensure it's initialized
            if last_non_tie is not None:
                # Current round Player and last non-tie round Banker
                if row['result'] == 'Player' and df_game.at[last_non_tie, 'result'] == 'Banker':
                    df_game.at[i, 'new_column'] = 1
                # Current round Banker and last non-tie round Player
                elif row['result'] == 'Banker' and df_game.at[last_non_tie, 'result'] == 'Player':
                    df_game.at[i, 'new_column'] = 2
                # Current round Player and last non-tie round Player
                elif row['result'] == 'Player' and df_game.at[last_non_tie, 'result'] == 'Player':
                    df_game.at[i, 'new_column'] = 4
                # Current round Banker and last non-tie round Banker
                elif row['result'] == 'Banker' and df_game.at[last_non_tie, 'result'] == 'Banker':
                    df_game.at[i, 'new_column'] = 3

            # Update last_non_tie round index
            last_non_tie = i

        # If Tie, last_non_tie doesn't update
        if df_game.at[i, 'new_column'] is None:
            df_game.at[i, 'new_column'] = 0  # For ties, use 0 in new_column

        # Update counts based on new_column
        if df_game.at[i, 'new_column'] == 1:  # Player win after Banker
            count_1 += 1
        elif df_game.at[i, 'new_column'] == 2:  # Banker win after Player
            count_2 += 1
        elif df_game.at[i, 'new_column'] == 3:  # Banker win after Banker
            count_3 += 1
        elif df_game.at[i, 'new_column'] == 4:  # Player win after Player
            count_4 += 1

        # Only calculate proportions if total_rounds > 0
        if total_rounds > 0:
            # Calculate proportions
            df_game.at[i, 'proportion_1'] = float(count_1) / total_rounds
            df_game.at[i, 'proportion_2'] = float(count_2) / total_rounds
            df_game.at[i, 'proportion_3'] = float(count_3) / total_rounds
            df_game.at[i, 'proportion_4'] = float(count_4) / total_rounds

        prop_1 = df_game.at[i, 'proportion_1']
        prop_2 = df_game.at[i, 'proportion_2']
        prop_3 = df_game.at[i, 'proportion_3']
        prop_4 = df_game.at[i, 'proportion_4']

        # Determine next round's decision based on current proportions
        next_rd_decision = 'No Bet'
        if prop_4 < min(prop_1, prop_2, prop_3) - min_below and prop_3 > prop_3_threshold_high and row['round_num'] > 20:
            next_rd_decision = 'Banker'
        elif prop_4 > prop_4_threshold_high and prop_3 < min(prop_1, prop_2, prop_4) - min_below:
            next_rd_decision = 'Player'

        # New decision algorithm after round 20 if prop_1 and prop_2 are both below 0.23 and below prop_3 and prop_4
        if row['round_num'] > 20 and prop_1 < 0.23 and prop_2 < 0.23 and prop_1 < prop_3 and prop_2 < prop_3 and prop_1 < prop_4 and prop_2 < prop_4:
            # If Player wins, bet on Player next round
            if row['result'] == 'Player':
                next_rd_decision = 'Player'
            # If Banker wins, bet on Player next round
            elif row['result'] == 'Banker':
                next_rd_decision = 'Banker'
            # Tie handling: look at the last non-tie round
            elif row['result'] == 'Tie' and last_non_tie is not None:
                if df_game.at[last_non_tie, 'result'] == 'Player':
                    next_rd_decision = 'Player'
                elif df_game.at[last_non_tie, 'result'] == 'Banker':
                    next_rd_decision = 'Banker'

        df_game.at[i, 'next_rd_decision'] = next_rd_decision

    st.session_state[f'df_game_{game}'] = df_game

    # Store the updated proportions
    st.session_state[f'proportions_{game}'] = {
        "proportion_1": df_game['proportion_1'].iloc[-1],
        "proportion_2": df_game['proportion_2'].iloc[-1],
        "proportion_3": df_game['proportion_3'].iloc[-1],
        "proportion_4": df_game['proportion_4'].iloc[-1]
    }

    # Move to the next round
    st.session_state[f'round_num_{game}'] += 1

# Buttons for each round (Banker, Player, Tie)
st.subheader(f"Game {game}: Who Won Round {st.session_state[f'round_num_{game}']}?")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Banker"):
        update_result("Banker")

with col2:
    if st.button("Player"):
        update_result("Player")

with col3:
    if st.button("Tie"):
        update_result("Tie")

# Display cumulative wins and proportions in one line
proportions = st.session_state[f'proportions_{game}']
st.subheader(f"Cumulative Wins and Proportions for {game}")
st.write(f"**Player:** {st.session_state[f'cumulative_wins_{game}']['Player']} | "
         f"**Banker:** {st.session_state[f'cumulative_wins_{game}']['Banker']} | "
         f"**Tie:** {st.session_state[f'cumulative_wins_{game}']['Tie']} | "
         f"**P1:** {proportions['proportion_1']:.2f} | "
         f"**P2:** {proportions['proportion_2']:.2f} | "
         f"**P3:** {proportions['proportion_3']:.2f} | "
         f"**P4:** {proportions['proportion_4']:.2f}")

# Display current betting decisions, with most recent one at the top (stacked layout)
if f'df_game_{game}' in st.session_state:
    df_game = st.session_state[f'df_game_{game}']
    if len(df_game) > 0:
        st.subheader(f"Betting Decisions and Profits for {game}")
        st.write(df_game[['round_num', 'result', 'next_rd_decision']].iloc[::-1].reset_index(drop=True))

# Button to reset the game (back to round 1 for the selected game)
if st.button("Reset Game"):
    st.session_state[f'cumulative_wins_{game}'] = {"Player": 0, "Banker": 0, "Tie": 0}
    st.session_state[f'round_num_{game}'] = 1
    st.session_state[f'proportions_{game}'] = {"proportion_1": 0, "proportion_2": 0, "proportion_3": 0, "proportion_4": 0}
    st.session_state[f'df_game_{game}'] = pd.DataFrame(columns=['round_num', 'result', 'next_rd_decision', 'profit'])
    st.write(f"**Game {game} reset successfully!**")
