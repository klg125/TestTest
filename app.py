
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
    
def data_processing(df_game):
    def calculate_rsi(series, window=14):
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        roll_up = up.rolling(window).mean()
        roll_down = down.rolling(window).mean()
        rs = roll_up / roll_down
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    df_game['rsi_p3'] = df_game['proportion_3'].transform(lambda x: calculate_rsi(x, window=10))
    df_game['rsi_p4'] = df_game['proportion_4'].transform(lambda x: calculate_rsi(x, window=10))

    df_game = calculate_support_resistance(df_game)

    return df_game


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

if f'initial_bankroll_{game}' not in st.session_state:
    st.session_state[f'initial_bankroll_{game}'] = 5000

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

    # Initialize necessary variables for the bounce strategy
    df_game = st.session_state[f'df_game_{game}']
    total_rounds = len(df_game)
    consecutive_wins = 0
    consecutive_losses = 0
    wins_total = 0
    bounce_active = False
    last_non_tie = None
    previous_decision = None
    profit = st.session_state[f'profit_{game}']
    B = 5000
    T_B = B * 0.2
    base_bet_size = (1/20 * T_B)  # Initial fixed bet size for each round
    next_bet_size = base_bet_size
    win_threshold, loss_threshold, slope_offset, rsi_max, multiplier = 0.35, 0.4, 4, 60, 2.2
    B_high = B + (win_threshold * T_B)
    B_low = B - (loss_threshold * T_B)

     # Additional parameters for slope-based strategies
    slope_2_offset = 4
    slope_active = False  

    # Initialize new columns if not present
    if 'new_column' not in df_game.columns:
        df_game['new_column'] = 0
        df_game['proportion_1'] = 0
        df_game['proportion_2'] = 0
        df_game['proportion_3'] = 0
        df_game['proportion_4'] = 0
        df_game['next_rd_decision'] = 'No Bet'
        df_game['profit'] = 0
        df_game['Cumulative Wins/Losses'] = 0  # New column for cumulative wins and losses

    # Track counts for new column
    non_tie_rounds = 0  # This will count non-tie rounds only

    count_1 = count_2 = count_3 = count_4 = 0

    prev_proportion_1, prev_proportion_2, prev_proportion_3, prev_proportion_4 = 0, 0, 0, 0

    # --- 1. Basic Proportion Calculation (Before data_processing) ---
    for i, row in df_game.iterrows():
        # Calculate cumulative wins and losses based on non-tie rounds
        if i > 0:
            if row['result'] == 'Player':
                df_game.at[i, 'Cumulative Wins/Losses'] = df_game.at[i-1, 'Cumulative Wins/Losses'] + 1
            elif row['result'] == 'Banker':
                df_game.at[i, 'Cumulative Wins/Losses'] = df_game.at[i-1, 'Cumulative Wins/Losses'] - 1
            else:
                df_game.at[i, 'Cumulative Wins/Losses'] = df_game.at[i-1, 'Cumulative Wins/Losses']
        else:
            # Initialize the first round cumulative wins/losses
            if row['result'] == 'Player':
                df_game.at[i, 'Cumulative Wins/Losses'] = 1
            elif row['result'] == 'Banker':
                df_game.at[i, 'Cumulative Wins/Losses'] = -1
            else:
                df_game.at[i, 'Cumulative Wins/Losses'] = 0

    
        if row['result'] != 'Tie':
            non_tie_rounds += 1  # Increment non-tie rounds only
    
            if last_non_tie is not None:
                # Assign a new value to `new_column` based on consecutive patterns of Player/Banker wins
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
    
                # Store the current proportions as the last valid proportions
                prev_proportion_1 = df_game.at[i, 'proportion_1']
                prev_proportion_2 = df_game.at[i, 'proportion_2']
                prev_proportion_3 = df_game.at[i, 'proportion_3']
                prev_proportion_4 = df_game.at[i, 'proportion_4']
    
        else:
            # If the result is a tie, carry over the previous non-tie proportions
            df_game.at[i, 'proportion_1'] = prev_proportion_1
            df_game.at[i, 'proportion_2'] = prev_proportion_2
            df_game.at[i, 'proportion_3'] = prev_proportion_3
            df_game.at[i, 'proportion_4'] = prev_proportion_4

    # --- 2. Apply data_processing (So RSI, slope, etc. are available) ---
    df_game = data_processing(df_game)

    df_game['slope_p3'] = calculate_slope(df_game['proportion_3'], offset=2)
    df_game['slope_p4'] = calculate_slope(df_game['proportion_4'], offset=2)

    df_game['slope_p3_5'] = calculate_slope(df_game['proportion_3'], offset=5)
    df_game['slope_p4_5'] = calculate_slope(df_game['proportion_4'], offset=5)

   
    # --- 1. Apply Bounce Betting Strategy ---
    for i, row in df_game.iterrows():
        result = df_game.at[i, 'result']
        rsi_p3 = df_game.at[i, 'rsi_p3']
        rsi_p4 = df_game.at[i, 'rsi_p4']
        current_support = df_game.at[i, 'support']
        current_resistance = df_game.at[i, 'resistance']
        cumulative_wins_losses = df_game.at[i, 'Cumulative Wins/Losses']

        next_bet = 'No Bet'

        # Player bounce strategy
        if not bounce_active and i >= 20:
            if (0 <= cumulative_wins_losses - current_support <= 2):
                if (df_game['rsi_p4'].iloc[i-1] <= df_game['rsi_p3'].iloc[i-1] or
                    df_game['rsi_p4'].iloc[i-2] <= df_game['rsi_p3'].iloc[i-2] or
                    df_game['rsi_p4'].iloc[i-3] <= df_game['rsi_p3'].iloc[i-3]) and df_game['slope_p4_5'].iloc[i] > 0 and df_game['slope_p3_5'].iloc[i] < 0:
                    next_bet = 'Player'
                    bounce_active = True

        # Banker bounce strategy
        elif not bounce_active and i >= 20:
            if (0 <= current_resistance - cumulative_wins_losses <= 2):
                if (df_game['rsi_p3'].iloc[i-1] <= df_game['rsi_p4'].iloc[i-1] or
                    df_game['rsi_p3'].iloc[i-2] <= df_game['rsi_p4'].iloc[i-2] or
                    df_game['rsi_p3'].iloc[i-3] <= df_game['rsi_p4'].iloc[i-3]) and df_game['slope_p3_5'].iloc[i] > 0 and df_game['slope_p4_5'].iloc[i] < 0:
                    next_bet = 'Banker'
                    bounce_active = True

        # Continue bounce betting
        if bounce_active:
            if previous_decision == 'Player':
                next_bet = 'Player'
            elif previous_decision == 'Banker':
                next_bet = 'Banker'
            

        # --- 2. Apply Slope-Based Betting Strategy ---

        
        if next_bet == 'No Bet':  # Only apply if bounce strategy did not trigger
             # Cross Resistance strategy: p4 upward slope, p3 downward slope for at least 2 rounds
            if not slope_active and i >= 20 and df_game['slope_p4'].iloc[i] > 0 and df_game['slope_p3'].iloc[i] < 0 and df_game['slope_p4_5'].iloc[i] > 0 and df_game['slope_p3_5'].iloc[i] < 0:
                if rsi_p4 - 1 > rsi_p3:
                    cumulative_wins_losses_ago = df_game.at[i - 4, 'Cumulative Wins/Losses']
                    cumulative_wins_losses_now = df_game.at[i, 'Cumulative Wins/Losses']

                    if cumulative_wins_losses_now - current_resistance >= 3 and cumulative_wins_losses_now - cumulative_wins_losses_ago >= 3:
                        next_bet = 'Player'
                        slope_active = True  # Activate slope-based betting

            # Cross Support strategy: p3 upward slope, p4 downward slope for at least 2 rounds
            elif not slope_active and i >= 20 and df_game['slope_p3'].iloc[i] > 0 and df_game['slope_p4'].iloc[i] < 0 and df_game['slope_p3_5'].iloc[i] > 0 and df_game['slope_p4_5'].iloc[i] < 0:
                if rsi_p3 - 1 > rsi_p4:
                    cumulative_wins_losses_ago = df_game.at[i - 4, 'Cumulative Wins/Losses']
                    cumulative_wins_losses_now = df_game.at[i, 'Cumulative Wins/Losses']
                    if cumulative_wins_losses_now <= current_support - 3 and cumulative_wins_losses_now - cumulative_wins_losses_ago <= -3:
                        next_bet = 'Banker'
                        slope_active = True  # Activate slope-based betting
            
            # Continue betting based on slope conditions
            if slope_active:
                if previous_decision == 'Player':
                    next_bet = 'Player'
                elif previous_decision == 'Banker':
                    next_bet = 'Banker'

     
        if previous_decision == 'Player':
            if result == 'Player':
                consecutive_losses = 0
                wins_total += 1
                  # Double the bet size with each consecutive win, capping at 3 consecutive wins
                if consecutive_wins == 0:
                    bet_size = base_bet_size 
                if consecutive_wins == 1:
                    bet_size = base_bet_size * multiplier
                elif consecutive_wins == 2:
                    bet_size = base_bet_size * (multiplier ** 2)
                elif consecutive_wins >= 3:
                    bet_size = base_bet_size *  (multiplier ** 3)
                consecutive_wins += 1
                B += bet_size  # Win: Update bankroll
                next_bet_size = bet_size * multiplier
            elif result == 'Banker':
                B -= next_bet_size  # Loss: Deduct from bankroll
                consecutive_losses += 1
                consecutive_wins = 0  # Reset consecutive wins after a loss
                wins_total -= 1
                next_bet_size = base_bet_size
                bet_size = base_bet_size  # Reset to base bet size after a loss
            

        elif previous_decision == 'Banker':
            if result == 'Banker':
                
                consecutive_losses = 0
                wins_total += 1
                # Double the bet size with each consecutive win, capping at 3 consecutive wins
                if consecutive_wins == 0:
                    bet_size = base_bet_size
              
                elif consecutive_wins == 1:
                    bet_size = base_bet_size * (multiplier ** 1)
                elif consecutive_wins == 2:
                    bet_size = base_bet_size *  (multiplier ** 2)
                elif consecutive_wins >= 3:
                    bet_size = base_bet_size *  (multiplier ** 3)
                consecutive_wins += 1
                B += 0.95 * bet_size  # Banker win returns 0.95 due to commission
                next_bet_size = bet_size * multiplier

                
            elif result == 'Player':
                B -= next_bet_size  # Loss: Deduct from bankroll
                consecutive_losses += 1
                consecutive_wins = 0  # Reset consecutive wins after a loss
                wins_total -= 1
                next_bet_size = base_bet_size
                bet_size = base_bet_size  # Reset to base bet size after a loss
        # Stopping conditions for bounce strategy
        if bounce_active and (rsi_p4 <= rsi_p3 and next_bet == 'Player') or cumulative_wins_losses >= current_resistance or wins_total >= 3 or consecutive_losses >= 2 or B >= B_high or B <= B_low:
            bounce_active = False
            next_bet_size = base_bet_size

        if bounce_active and (rsi_p3 <= rsi_p4 and next_bet == 'Banker') or cumulative_wins_losses <= current_support or wins_total >= 3 or consecutive_losses >= 2 or B >= B_high or B <= B_low:
            bounce_active = False
            next_bet_size = base_bet_size

    
        if slope_active:
            if next_bet == 'Player' and rsi_p3 >= rsi_p4:
                slope_active = False  # Deactivate slope-based betting
                next_bet = 'No Bet'
            elif next_bet == 'Banker' and rsi_p3 <= rsi_p4:
                slope_active = False  # Deactivate slope-based betting
                next_bet = 'No Bet'
            elif wins_total >= 3 or consecutive_losses >= 2 or B >= B_high or B <= B_low:
                slope_active = False  # Stop betting based on other conditions
                next_bet = 'No Bet'


        # Store the next round decision and update previous decision
        df_game.at[i, 'next_rd_decision'] = next_bet
        previous_decision = next_bet
        
    # --- 4. Update bankroll and session state ---
    
    df_game.at[total_rounds - 1, 'profit'] = B
    st.session_state[f'df_game_{game}'] = df_game
    st.session_state[f'profit_{game}'] = B
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


# Button to reset the game
if st.button("Reset Game"):
    st.session_state[f'cumulative_wins_{game}'] = {"Player": 0, "Banker": 0, "Tie": 0}
    st.session_state[f'round_num_{game}'] = 1
    st.session_state[f'proportions_{game}'] = {"proportion_1": 0, "proportion_2": 0, "proportion_3": 0, "proportion_4": 0}
    st.session_state[f'df_game_{game}'] = pd.DataFrame(columns=['round_num', 'result', 'next_rd_decision', 'profit'])
    st.session_state[f'profit_{game}'] = 0
    st.write(f"**Game {game} reset successfully!**")
    
# Display current betting decisions and profits
if f'df_game_{game}' in st.session_state:
    df_game = st.session_state[f'df_game_{game}']
    if len(df_game) > 0:
        st.subheader(f"Betting Decisions and Profits for {game}")
        st.write(df_game[['round_num', 'result', 'next_rd_decision', 'profit', 'rsi_p3', 'rsi_p4', 'support', 'resistance', 'Cumulative Wins/Losses', ]].iloc[::-1].reset_index(drop=True))

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

