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

# Streamlit app title in Chinese
st.title("百家乐模拟器")

# Add a game selector (G1, G2, G3, G4, G5, G6) - translated to Chinese
game = st.selectbox("选择游戏", ["G1", "G2", "G3", "G4", "G5", "G6"])

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
    stopping_threshold = 0.24
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
    for i, row in df_game.iterrows():
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

        if df_game.at[i, 'new_column'] == 1:
            count_1 += 1
        elif df_game.at[i, 'new_column'] == 2:
            count_2 += 1
        elif df_game.at[i, 'new_column'] == 3:
            count_3 += 1
        elif df_game.at[i, 'new_column'] == 4:
            count_4 += 1

        # Update proportions
        df_game.at[i, 'proportion_1'] = count_1 / total_rounds
        df_game.at[i, 'proportion_2'] = count_2 / total_rounds
        df_game.at[i, 'proportion_3'] = count_3 / total_rounds
        df_game.at[i, 'proportion_4'] = count_4 / total_rounds

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

        df_game.at[i, 'next_rd_decision'] = next_rd_decision

    # Now calculate the profit for this round based on the previous round's next_rd_decision
    if total_rounds > 1:  # If we're beyond the first round
        previous_round = df_game.iloc[-2]  # Use previous round's decision
        profit = calculate_profit(winner, previous_round['next_rd_decision'], profit)
        df_game.at[total_rounds-1, 'profit'] = profit

    # Update the session state with accumulated profit
    st.session_state[f'profit_{game}'] = profit
    st.session_state[f'df_game_{game}'] = df_game

    # Store the updated proportions
    st.session_state[f'proportions_{game}'] = {
        "proportion_1": df_game['proportion_1'].iloc[-1],
        "proportion_2": df_game['proportion_2'].iloc[-1],
        "proportion_3': df_game['proportion_3'].iloc[-1],
        "proportion_4": df_game['proportion_4'].iloc[-1]
    }

    # Immediately move to the next round
    st.session_state[f'round_num_{game}'] = len(st.session_state[f'df_game_{game}']) + 1

# Add a button to undo the last round
def undo_last_round():
    if len(st.session_state[f'df_game_{game}']) > 0:
        # Remove the last round
        st.session_state[f'df_game_{game}'] = st.session_state[f'df_game_{game}'].iloc[:-1]

        # Adjust cumulative wins and profit based on the removed round
        last_round = st.session_state[f'df_game_{game}'].iloc[-1] if len(st.session_state[f'df_game_{game}']) > 0 else None

        # Decrement cumulative wins if necessary
        if last_round is not None:
            st.session_state[f'cumulative_wins_{game}'][last_round['result']] -= 1

            # Recalculate the profit based on the last round's decision
            if len(st.session_state[f'df_game_{game}']) > 1:
                previous_round = st.session_state[f'df_game_{game}'].iloc[-2]
                st.session_state[f'profit_{game}'] = calculate_profit(
                    last_round['result'], previous_round['next_rd_decision'], st.session_state[f'profit_{game}']
                )
            else:
                st.session_state[f'profit_{game}'] = 0  # Reset profit if it's the first round

        # Correctly decrement the round number
        st.session_state[f'round_num_{game}'] = len(st.session_state[f'df_game_{game}']) + 1

# Buttons for each round (Banker, Player, Tie) - translated to Chinese
st.subheader(f"游戏 {game}: 谁赢得了第 {st.session_state[f'round_num_{game}']} 轮?")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("庄家"):
        update_result("Banker")

with col2:
    if st.button("闲家"):
        update_result("Player")

with col3:
    if st.button("平局"):
        update_result("Tie")

# Button to undo the last round (translated to Chinese)
if st.button("撤销上一轮"):
    undo_last_round()

# Display cumulative wins and proportions in one line - translated to Chinese
proportions = st.session_state[f'proportions_{game}']
st.subheader(f"累计胜利和比例 - 游戏 {game}")
st.write(f"**闲家:** {st.session_state[f'cumulative_wins_{game}']['Player']} | "
         f"**庄家:** {st.session_state[f'cumulative_wins_{game}']['Banker']} | "
         f"**平局:** {st.session_state[f'cumulative_wins_{game}']['Tie']} | "
         f"**比例1:** {proportions['proportion_1']:.2f} | "
         f"**比例2:** {proportions['proportion_2']:.2f} | "
         f"**比例3:** {proportions['proportion_3']:.2f} | "
         f"**比例4:** {proportions['proportion_4']:.2f}")

# Display current betting decisions and profits, with most recent one at the top - translated to Chinese
if f'df_game_{game}' in st.session_state:
    df_game = st.session_state[f'df_game_{game}']
    if len(df_game) > 0:
        st.subheader(f"投注决策和利润 - 游戏 {game}")
        st.write(df_game[['round_num', 'result', 'next_rd_decision', 'profit']].iloc[::-1].reset_index(drop=True))

# Button to reset the game (back to round 1) - translated to Chinese
if st.button("重置游戏"):
    st.session_state[f'cumulative_wins_{game}'] = {"Player": 0, "Banker": 0, "Tie": 0}
    st.session_state[f'round_num_{game}'] = 1
    st.session_state[f'proportions_{game}'] = {"proportion_1": 0, "proportion_2": 0, "proportion_3": 0, "proportion_4": 0}
    st.session_state[f'df_game_{game}'] = pd.DataFrame(columns=['round_num', 'result', 'next_rd_decision', 'profit'])
    st.session_state[f'profit_{game}'] = 0
    st.write(f"**游戏 {game} 成功重置！**")
