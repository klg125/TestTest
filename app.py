import streamlit as st
import pandas as pd
import numpy as np


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

# Function to calculate RSI
def calculate_rsi(series, window=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.rolling(window).mean()
    roll_down = down.rolling(window).mean()
    rs = roll_up / roll_down
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Function to calculate support and resistance
def calculate_support_resistance(df):
    cumulative_wins_losses = df['Cumulative Wins/Losses'].values
    support = np.full(len(cumulative_wins_losses), np.nan)
    resistance = np.full(len(cumulative_wins_losses), np.nan)

    last_low = np.inf
    last_high = -np.inf
    low_verified = False
    high_verified = False
    current_support = np.nan
    current_resistance = np.nan

    for i in range(2, len(cumulative_wins_losses)):  # Start at index 2 for verification condition
        # Check for new low and verify it
        if cumulative_wins_losses[i] < last_low:
            last_low = cumulative_wins_losses[i]
            low_verified = False  # Reset verification on new low
        elif not low_verified and cumulative_wins_losses[i] > last_low:  # Verification occurs after the low is crossed from above
            low_verified = True
        
        # If low is verified, set the support; otherwise, retain the previous support
        if low_verified:
            current_support = last_low
        support[i] = current_support  # Keep the old support if no new low is verified

        # Check for new high and verify it
        if cumulative_wins_losses[i] > last_high:
            last_high = cumulative_wins_losses[i]
            high_verified = False  # Reset verification on new high
        elif not high_verified and cumulative_wins_losses[i] < last_high:  # Verification occurs after the high is crossed from below
            high_verified = True

        # If high is verified, set the resistance; otherwise, retain the previous resistance
        if high_verified:
            current_resistance = last_high
        resistance[i] = current_resistance  # Keep the old resistance if no new high is verified

    df['support'] = support
    df['resistance'] = resistance
    return df


# Function to calculate slope over 2 rounds
def calculate_slope(series, offset=2):
    return (series - series.shift(offset)) / offset

# Main data processing function
def data_processing(df_game):
    # Apply RSI calculation
    df_game['rsi_p1'] = calculate_rsi(df_game['proportion_1'], window=10)
    df_game['rsi_p2'] = calculate_rsi(df_game['proportion_2'], window=10)
    df_game['rsi_p3'] = calculate_rsi(df_game['proportion_3'], window=10)
    df_game['rsi_p4'] = calculate_rsi(df_game['proportion_4'], window=10)

    # Apply support and resistance calculation
    df_game = calculate_support_resistance(df_game)

    df_game['slope_rsi_p3'] = calculate_slope(df_game['rsi_p3'], window=5)
    df_game['slope_rsi_p4'] = calculate_slope(df_game['rsi_p4'], window=5)

    return df_game

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

# Function to calculate profit based on the previous round's decision and the current result
def calculate_profit(result, decision, current_profit):
    if decision == 'Banker':
        if result == 'Banker':
            current_profit += 0.95  # Banker win with commission
        elif result == 'Player':
            current_profit -= 1  # Loss on Banker bet
    elif decision == 'Player':
        if result == 'Player':
            current_profit += 1  # Win on Player bet
        elif result == 'Banker':
            current_profit -= 1  # Loss on Player bet
    return current_profit

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
    profit = st.session_state[f'profit_{game}']

    # Initialize new columns if not present
    if 'new_column' not in df_game.columns:
        df_game['new_column'] = 0
        df_game['proportion_1'] = 0
        df_game['proportion_2'] = 0
        df_game['proportion_3'] = 0
        df_game['proportion_4'] = 0
        df_game['next_rd_decision'] = 'No Bet'
        df_game['profit'] = 0

    # Track counts for new column
    non_tie_rounds = 0  # This will count non-tie rounds only
    for i, row in df_game.iterrows():
        if row['result'] != 'Tie':
            non_tie_rounds += 1  # Increment non-tie rounds only

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

            # Update counts based on new_column
            if df_game.at[i, 'new_column'] == 1:
                count_1 += 1
            elif df_game.at[i, 'new_column'] == 2:
                count_2 += 1
            elif df_game.at[i, 'new_column'] == 3:
                count_3 += 1
            elif df_game.at[i, 'new_column'] == 4:
                count_4 += 1

        # Calculate proportions based on non-tie rounds
        if non_tie_rounds > 1:
            df_game.at[i, 'proportion_1'] = count_1 / (non_tie_rounds - 1)
            df_game.at[i, 'proportion_2'] = count_2 / (non_tie_rounds - 1)
            df_game.at[i, 'proportion_3'] = count_3 / (non_tie_rounds - 1)
            df_game.at[i, 'proportion_4'] = count_4 / (non_tie_rounds - 1)

        prop_1 = df_game.at[i, 'proportion_1']
        prop_2 = df_game.at[i, 'proportion_2']
        prop_3 = df_game.at[i, 'proportion_3']
        prop_4 = df_game.at[i, 'proportion_4']

        # Determine next round's decision based on current proportions
        next_rd_decision = 'No Bet'
        if prop_4 < min(prop_1, prop_2, prop_3) - min_below and prop_3 > prop_3_threshold_high and row['round_num'] > 5:
            next_rd_decision = 'Banker'
        elif prop_4 > prop_4_threshold_high and prop_3 < min(prop_1, prop_2, prop_4) - min_below and row['round_num'] > 5:
            next_rd_decision = 'Player'

        # New decision algorithm after round 20 if prop_1 and prop_2 are both below 0.23 and below prop_3 and prop_4
        if row['round_num'] > 20 and prop_1 < 0.23 and prop_2 < 0.23 and prop_1 < prop_3 and prop_2 < prop_3 and prop_1 < prop_4 and prop_2 < prop_4:
            # If Player wins, bet on Player next round
            if row['result'] == 'Player':
                next_rd_decision = 'Player'
            # If Banker wins, bet on Banker next round
            elif row['result'] == 'Banker':
                next_rd_decision = 'Banker'
            # Tie handling: look at the last non-tie round
            elif row['result'] == 'Tie' and last_non_tie is not None:
                if df_game.at[last_non_tie, 'result'] == 'Player':
                    next_rd_decision = 'Player'
                elif df_game.at[last_non_tie, 'result'] == 'Banker':
                    next_rd_decision = 'Banker'

        df_game.at[i, 'next_rd_decision'] = next_rd_decision

    # Now calculate the profit for this round based on the previous round's next_rd_decision
    if total_rounds > 1:  # If we're beyond the first round
        previous_round = df_game.iloc[-2]  # Use previous round's decision
        profit = calculate_profit(winner, previous_round['next_rd_decision'], profit)
        df_game.at[total_rounds-1, 'profit'] = profit
    else:
        df_game.at[total_rounds-1, 'profit'] = profit

    # Update the session state with accumulated profit
    st.session_state[f'profit_{game}'] = profit
    st.session_state[f'df_game_{game}'] = df_game

    # Store the updated proportions
    st.session_state[f'proportions_{game}'] = {
        "proportion_1": df_game['proportion_1'].iloc[-1],
        "proportion_2": df_game['proportion_2'].iloc[-1],
        "proportion_3": df_game['proportion_3'].iloc[-1],
        "proportion_4": df_game['proportion_4'].iloc[-1]
    }

    # Process the data to calculate RSI, slopes, support, and resistance
    df_game['game_number'] = game  # Add game_number column for processing
    df_game['Cumulative Wins/Losses'] = df_game['profit']  # Use profit as cumulative wins/losses
    df_game = data_processing(df_game)

    # Update the session state with the processed dataframe
    st.session_state[f'df_game_{game}'] = df_game

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

# Display cumulative wins and proportions
proportions = st.session_state[f'proportions_{game}']
st.subheader(f"Cumulative Wins and Proportions for {game}")
st.write(f"**Player:** {st.session_state[f'cumulative_wins_{game}']['Player']} | "
         f"**Banker:** {st.session_state[f'cumulative_wins_{game}']['Banker']} | "
         f"**Tie:** {st.session_state[f'cumulative_wins_{game}']['Tie']} | "
         f"**P1:** {proportions['proportion_1']:.2f} | "
         f"**P2:** {proportions['proportion_2']:.2f} | "
         f"**P3:** {proportions['proportion_3']:.2f} | "
         f"**P4:** {proportions['proportion_4']:.2f}")

# Display current betting decisions and profits
if f'df_game_{game}' in st.session_state:
    df_game = st.session_state[f'df_game_{game}']
    if len(df_game) > 0:
        st.subheader(f"Betting Decisions and Profits for {game}")
        st.write(df_game[['round_num', 'result', 'next_rd_decision', 'profit']].iloc[::-1].reset_index(drop=True))

        # Display RSI, slopes, support, and resistance
        st.subheader(f"RSI, Slopes, Support, and Resistance for {game}")
        display_df = df_game[['round_num', 'rsi_p3', 'rsi_p4',
                                'slope_rsi_p3', 'slope_rsi_p4',
                              'support', 'resistance']].copy()
        st.write(display_df.iloc[::-1].reset_index(drop=True))

# Button to reset the game
if st.button("Reset Game"):
    st.session_state[f'cumulative_wins_{game}'] = {"Player": 0, "Banker": 0, "Tie": 0}
    st.session_state[f'round_num_{game}'] = 1
    st.session_state[f'proportions_{game}'] = {"proportion_1": 0, "proportion_2": 0, "proportion_3": 0, "proportion_4": 0}
    st.session_state[f'df_game_{game}'] = pd.DataFrame(columns=['round_num', 'result', 'next_rd_decision', 'profit'])
    st.session_state[f'profit_{game}'] = 0
    st.write(f"**Game {game} reset successfully!**")
