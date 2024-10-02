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

# Add a game selector (G1, G2, G3, G4)
game = st.selectbox("Select Game", ["G1", "G2", "G3", "G4"])

# Initialize session state for cumulative wins and round number
if f'cumulative_wins_{game}' not in st.session_state:
    st.session_state[f'cumulative_wins_{game}'] = {"Player": 0, "Banker": 0, "Tie": 0}

if f'round_num_{game}' not in st.session_state:
    st.session_state[f'round_num_{game}'] = 1

if f'df_game_{game}' not in st.session_state:
    st.session_state[f'df_game_{game}'] = pd.DataFrame(columns=['round_num', 'result'])

# Function to update results and calculate proportions and betting decision
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

    # Proportions and betting decision logic
    df_game = st.session_state[f'df_game_{game}']
    total_rounds = len(df_game)
    count_1 = count_2 = count_3 = count_4 = 0
    prop_3_threshold_high = 0.32
    prop_4_threshold_high = 0.32
    stopping_threshold = 0.24
    min_below = 0.02
    last_non_tie = None

    # Initialize new columns if not present
    if 'new_column' not in df_game.columns:
        df_game['new_column'] = 0
        df_game['proportion_1'] = 0
        df_game['proportion_2'] = 0
        df_game['proportion_3'] = 0
        df_game['proportion_4'] = 0
        df_game['decision'] = 'No Bet'

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

        df_game.at[i, 'proportion_1'] = count_1 / total_rounds
        df_game.at[i, 'proportion_2'] = count_2 / total_rounds
        df_game.at[i, 'proportion_3'] = count_3 / total_rounds
        df_game.at[i, 'proportion_4'] = count_4 / total_rounds

        prop_1 = df_game.at[i, 'proportion_1']
        prop_2 = df_game.at[i, 'proportion_2']
        prop_3 = df_game.at[i, 'proportion_3']
        prop_4 = df_game.at[i, 'proportion_4']

        decision = 'No Bet'
        if prop_4 < min(prop_1, prop_2, prop_3) - min_below and prop_3 > prop_3_threshold_high and row['round_num'] > 20:
            decision = 'Banker'
        elif prop_4 > prop_4_threshold_high and prop_3 < min(prop_1, prop_2, prop_4) - min_below:
            decision = 'Player'

        df_game.at[i, 'decision'] = decision

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

# Display cumulative wins in one line
st.subheader(f"Cumulative Wins for {game}")
st.write(f"**Player:** {st.session_state[f'cumulative_wins_{game}']['Player']} | "
         f"**Banker:** {st.session_state[f'cumulative_wins_{game}']['Banker']} | "
         f"**Tie:** {st.session_state[f'cumulative_wins_{game}']['Tie']}")

# Display current betting decisions, with most recent one at the top (stacked layout)
if f'df_game_{game}' in st.session_state:
    df_game = st.session_state[f'df_game_{game}']
    if len(df_game) > 0:
        st.subheader(f"Betting Decisions for {game}")
        st.write(df_game[['round_num', 'decision']].iloc[::-1].reset_index(drop=True))

# Button to reset the game (back to round 1 for the selected game)
if st.button("Reset Game"):
    st.session_state[f'cumulative_wins_{game}'] = {"Player": 0, "Banker": 0, "Tie": 0}
    st.session_state[f'round_num_{game}'] = 1
    st.session_state[f'df_game_{game}'] = pd.DataFrame(columns=['round_num', 'result'])
    st.write(f"**Game {game} reset successfully!**")
