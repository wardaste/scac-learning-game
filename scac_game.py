import streamlit as st
import sqlite3
import time
import random
from datetime import datetime
import pandas as pd

# Page config
st.set_page_config(
    page_title="SCAC Learning Game",
    page_icon="🚚",
    layout="wide"
)

# Database functions
def init_database():
    conn = sqlite3.connect('scac_game.db')
    c = conn.cursor()
    
    # SCAC data table
    c.execute('''CREATE TABLE IF NOT EXISTS scacs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  scac_code TEXT UNIQUE, 
                  carrier_name TEXT,
                  ship_mode TEXT,
                  details TEXT)''')
    
    # Player scores table
    c.execute('''CREATE TABLE IF NOT EXISTS scores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  player_name TEXT,
                  score INTEGER,
                  correct_answers INTEGER,
                  total_questions INTEGER,
                  timestamp DATETIME)''')
    
    # Insert DEMO data only (safe for public GitHub)
    # No sample data - start with empty database
    sample_data = []
    
    for data in sample_data:
        c.execute("INSERT OR IGNORE INTO scacs (scac_code, carrier_name, ship_mode, details) VALUES (?, ?, ?, ?)", data)    
    conn.commit()
    conn.close()

def get_all_scacs():
    conn = sqlite3.connect('scac_game.db')
    df = pd.read_sql_query("SELECT * FROM scacs", conn)
    conn.close()
    return df

def add_scac(scac_code, carrier_name, ship_mode, details):
    conn = sqlite3.connect('scac_game.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO scacs (scac_code, carrier_name, ship_mode, details) VALUES (?, ?, ?, ?)",
                 (scac_code, carrier_name, ship_mode, details))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_scac(scac_id):
    conn = sqlite3.connect('scac_game.db')
    c = conn.cursor()
    c.execute("DELETE FROM scacs WHERE id = ?", (scac_id,))
    conn.commit()
    conn.close()

def save_score(player_name, score, correct, total):
    conn = sqlite3.connect('scac_game.db')
    c = conn.cursor()
    c.execute("INSERT INTO scores (player_name, score, correct_answers, total_questions, timestamp) VALUES (?, ?, ?, ?, ?)",
             (player_name, score, correct, total, datetime.now()))
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = sqlite3.connect('scac_game.db')
    df = pd.read_sql_query("""
        SELECT player_name, MAX(score) as best_score, 
               MAX(correct_answers) as best_correct,
               COUNT(*) as games_played,
               MAX(timestamp) as last_played
        FROM scores 
        GROUP BY player_name 
        ORDER BY best_score DESC
    """, conn)
    conn.close()
    return df

# Game functions
def initialize_game_state():
    if 'game_active' not in st.session_state:
        st.session_state.game_active = False
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None
    if 'question_start_time' not in st.session_state:
        st.session_state.question_start_time = None
    if 'score' not in st.session_state:
        st.session_state.score = 0
    if 'correct_answers' not in st.session_state:
        st.session_state.correct_answers = 0
    if 'total_questions' not in st.session_state:
        st.session_state.total_questions = 0
    if 'used_questions' not in st.session_state:
        st.session_state.used_questions = []

def generate_question(scacs_df):
    available_scacs = scacs_df[~scacs_df['id'].isin(st.session_state.used_questions)]
    
    if len(available_scacs) == 0:
        return None
    
    correct_scac = available_scacs.sample(1).iloc[0]
    question_types = [
        "carrier_from_scac",
        "scac_from_carrier", 
        "ship_mode_from_scac",
        "multiple_choice_carrier"
    ]
    
    question_type = random.choice(question_types)
    
    if question_type == "carrier_from_scac":
        return {
            'type': 'text',
            'question': f"What is the carrier name for SCAC code: {correct_scac['scac_code']}?",
            'correct_answer': correct_scac['carrier_name'].lower(),
            'scac_id': correct_scac['id'],
            'hint': f"Ship Mode: {correct_scac['ship_mode']}"
        }
    
    elif question_type == "scac_from_carrier":
        return {
            'type': 'text',
            'question': f"What is the SCAC code for: {correct_scac['carrier_name']}?",
            'correct_answer': correct_scac['scac_code'].upper(),
            'scac_id': correct_scac['id'],
            'hint': f"Ship Mode: {correct_scac['ship_mode']}"
        }
    
    elif question_type == "ship_mode_from_scac":
        return {
            'type': 'text',
            'question': f"What is the ship mode for {correct_scac['scac_code']} ({correct_scac['carrier_name']})?",
            'correct_answer': correct_scac['ship_mode'].lower(),
            'scac_id': correct_scac['id'],
            'hint': "Think about the type of transportation service"
        }
    
    elif question_type == "multiple_choice_carrier":
        # Get 3 wrong answers
        wrong_answers = scacs_df[scacs_df['id'] != correct_scac['id']]['carrier_name'].tolist()
        if len(wrong_answers) >= 3:
            wrong_answers = random.sample(wrong_answers, 3)
        
        choices = [correct_scac['carrier_name']] + wrong_answers
        random.shuffle(choices)
        
        return {
            'type': 'multiple_choice',
            'question': f"Which carrier has the SCAC code: {correct_scac['scac_code']}?",
            'choices': choices,
            'correct_answer': correct_scac['carrier_name'],
            'scac_id': correct_scac['id'],
            'hint': f"Ship Mode: {correct_scac['ship_mode']}"
        }

def calculate_score(time_taken, is_correct):
    if is_correct:
        # Max 100 points, decreasing with time (60 second max)
        # Ensure we always get positive points for correct answers
        time_bonus = max(10, 100 - (time_taken * 1.5))  # Slower decrease over 60 seconds
        return int(time_bonus)
    else:
        # Penalty increases with speed (faster wrong answers = bigger penalty)
        penalty = min(50, max(10, 50 - (time_taken * 1)))
        return -int(penalty)

def display_sand_timer(elapsed_time):
    # Calculate time remaining
    time_remaining = max(0, 60 - elapsed_time)
    
    # Simple display
    st.write("⏳ Timer")
    st.write(f"**{time_remaining:.0f} seconds left**")
    
    # Progress bar (remaining time)
    progress = time_remaining / 60
    st.progress(progress)
    
    # Color-coded message
    if time_remaining > 30:
        st.success("Plenty of time!")
    elif time_remaining > 10:
        st.warning("Time running out!")
    elif time_remaining > 0:
        st.error("Hurry up!")
    else:
        st.error("Time's up!")

# Main app
def main():
    init_database()
    initialize_game_state()
    
    st.title("🚚 SCAC Learning Game")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page:", ["Play Game", "Leaderboard", "Admin Panel"])
    
    if page == "Play Game":
        play_game_page()
    elif page == "Leaderboard":
        leaderboard_page()
    elif page == "Admin Panel":
        admin_page()

def play_game_page():
    scacs_df = get_all_scacs()
    if len(scacs_df) == 0:
        st.error("No SCAC data available. Please add some data in the Admin Panel first.")
        return
    
    # Only show header and name input when game is not active
    if not st.session_state.game_active:
        st.header("🚚 Flash Card Game")
        st.write("Test your knowledge of SCACs, carriers, and ship modes!")
        
        # Player name input
        if 'player_name' not in st.session_state:
            st.session_state.player_name = ""
        
        player_name = st.text_input("Enter your name:", value=st.session_state.player_name)
        st.session_state.player_name = player_name
    
    if not st.session_state.game_active:
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🎮 Start Game", disabled=not player_name):
                st.session_state.game_active = True
                st.session_state.score = 0
                st.session_state.correct_answers = 0
                st.session_state.total_questions = 0
                st.session_state.used_questions = []
                st.session_state.current_question = generate_question(scacs_df)
                st.session_state.question_start_time = time.time()
                st.session_state.answer_submitted = False  # New state variable
                st.rerun()
        
        with col2:
            st.info("Enter your name and click 'Start Game' to begin!")
    
    else:
        # Game is active
        if st.session_state.current_question is None:
            # Game over
            st.success("🎉 Game Complete!")
            st.write(f"**Final Score:** {st.session_state.score}")
            st.write(f"**Correct Answers:** {st.session_state.correct_answers}/{st.session_state.total_questions}")
            
            if st.button("Save Score & Play Again"):
                save_score(st.session_state.player_name, st.session_state.score, 
                          st.session_state.correct_answers, st.session_state.total_questions)
                st.session_state.game_active = False
                st.rerun()
            return
        
        # Compact stats box in upper right corner
        col1, col2 = st.columns([3, 1])
        
        with col2:
            # Get timer info
            if st.session_state.question_start_time and not getattr(st.session_state, 'answer_submitted', False):
                elapsed = time.time() - st.session_state.question_start_time
                time_remaining = max(0, 60 - elapsed)
                timer_display = f"{time_remaining:.0f}s left"
                
                # Auto-submit if time runs out
                if elapsed >= 60:
                    st.error("⏰ Time's up!")
                    process_answer("", scacs_df)
                    st.rerun()
            else:
                timer_display = f"{getattr(st.session_state, 'last_answer_time', 0):.1f}s"
            
            # Compact stats box
            st.markdown(f"""
            <div style="background: #1e1e1e;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
                text-align: center;
                color: #ffffff;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
                <div style="font-weight: bold; margin-bottom: 5px;">👤 {st.session_state.player_name}</div>
                <div>🏆 Score: {st.session_state.score}</div>
                <div>✅ Correct: {st.session_state.correct_answers}</div>
                <div>📊 Total: {st.session_state.total_questions}</div>
                <div>⏰ {timer_display}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col1:
            # Display question
            question = st.session_state.current_question
            st.subheader(question['question'])
            
            # Initialize answer_submitted if it doesn't exist
            if 'answer_submitted' not in st.session_state:
                st.session_state.answer_submitted = False
            
            # Show answer input only if answer hasn't been submitted yet
            if not st.session_state.answer_submitted:
                # Answer input based on question type
                if question['type'] == 'text':
                    with st.form(key=f"answer_form_{st.session_state.total_questions}"):
                        answer = st.text_input("Your answer:", key=f"answer_{st.session_state.total_questions}")
                        
                        col_a, col_b = st.columns([1, 1])
                        with col_a:
                            submitted = st.form_submit_button("Submit Answer (or Press Enter)")
                        with col_b:
                            hint_clicked = st.form_submit_button("Show Hint")
                        
                        if submitted and answer.strip():
                            process_answer(answer, scacs_df)
                            st.rerun()
                        elif hint_clicked:
                            st.info(f"💡 Hint: {question['hint']}")
                
                elif question['type'] == 'multiple_choice':
                    with st.form(key=f"mc_form_{st.session_state.total_questions}"):
                        answer = st.radio("Choose your answer:", question['choices'], key=f"mc_{st.session_state.total_questions}")
                        
                        col_a, col_b = st.columns([1, 1])
                        with col_a:
                            submitted = st.form_submit_button("Submit Answer (Press Enter)")
                        with col_b:
                            hint_clicked = st.form_submit_button("Show Hint")
                        
                        if submitted:
                            process_answer(answer, scacs_df)
                            st.rerun()
                        elif hint_clicked:
                            st.info(f"💡 Hint: {question['hint']}")
            
            else:
                # Answer has been submitted, show results

                # Display the result with visual indicators
                if hasattr(st.session_state, 'last_answer_correct'):
                    if st.session_state.last_answer_correct:
                        st.success(f"✅ Correct! +{st.session_state.last_points} points (answered in {st.session_state.last_answer_time:.1f}s)")
                    else:
                        user_answer_display = getattr(st.session_state, 'last_user_answer', 'No answer')
                        if user_answer_display.strip() == "":
                            user_answer_display = "No answer (time expired)"
                        st.error(f"❌ Wrong! {st.session_state.last_points} points (correct answer: {st.session_state.last_correct_answer}, your answer: {user_answer_display})")
                
                # Show SCAC details
                if hasattr(st.session_state, 'last_scac_info'):
                    with st.expander("📋 SCAC Details"):
                        scac_info = st.session_state.last_scac_info
                        st.write(f"**SCAC:** {scac_info['scac_code']}")
                        st.write(f"**Carrier:** {scac_info['carrier_name']}")
                        st.write(f"**Ship Mode:** {scac_info['ship_mode']}")
                        st.write(f"**Details:** {scac_info['details']}")
                
                # Next question button
                st.write("")  # Add some space
                if st.button("Next Question ➡️", use_container_width=True):
                    # Reset for next question
                    st.session_state.current_question = generate_question(scacs_df)
                    if st.session_state.current_question:
                        st.session_state.question_start_time = time.time()
                        st.session_state.answer_submitted = False
                        # Clear the last answer info
                        if hasattr(st.session_state, 'last_answer_correct'):
                            delattr(st.session_state, 'last_answer_correct')
                        if hasattr(st.session_state, 'last_scac_info'):
                            delattr(st.session_state, 'last_scac_info')
                    st.rerun()

def process_answer(user_answer, scacs_df):
    question = st.session_state.current_question
    time_taken = time.time() - st.session_state.question_start_time
    
    # Store the answer time for display
    st.session_state.last_answer_time = time_taken
    
    # Check if answer is correct
    if question['type'] == 'text':
        is_correct = user_answer.lower().strip() == question['correct_answer'].lower().strip()
    else:  # multiple choice
        is_correct = user_answer == question['correct_answer']
    
    # Calculate score
    points = calculate_score(time_taken, is_correct)
    st.session_state.score += points
    st.session_state.total_questions += 1
    
    # Store results for display
    st.session_state.last_answer_correct = is_correct
    st.session_state.last_points = points
    st.session_state.last_correct_answer = question['correct_answer']
    st.session_state.last_user_answer = user_answer  # Store what user actually answered
    
    # Store SCAC info for display
    scac_info = scacs_df[scacs_df['id'] == question['scac_id']].iloc[0]
    st.session_state.last_scac_info = {
        'scac_code': scac_info['scac_code'],
        'carrier_name': scac_info['carrier_name'],
        'ship_mode': scac_info['ship_mode'],
        'details': scac_info['details']
    }
    
    if is_correct:
        st.session_state.correct_answers += 1
    
    # Mark this question as used and set answer as submitted
    st.session_state.used_questions.append(question['scac_id'])
    st.session_state.answer_submitted = True

def leaderboard_page():
    st.header("🏆 Leaderboard")
    
    leaderboard = get_leaderboard()
    if len(leaderboard) > 0:
        st.dataframe(
            leaderboard,
            column_config={
                "player_name": "Player",
                "best_score": "Best Score",
                "best_correct": "Best Correct",
                "games_played": "Games Played",
                "last_played": "Last Played"
            },
            hide_index=True
        )
    else:
        st.info("No scores yet. Play some games to see the leaderboard!")

def admin_page():
    st.header("⚙️ Admin Panel")
    
    # Add admin notice
    st.info("🔒 **Admin Instructions:** After deployment, delete the demo data and add your real SCAC information here. The real data will only exist in the app, not in the public code.")
    
    tab1, tab2, tab3 = st.tabs(["Add New SCAC", "View All SCACs", "Manage Data"])
    
    with tab1:
        st.subheader("Add New SCAC")
        
        # Use session state to control form clearing
        if 'form_key' not in st.session_state:
            st.session_state.form_key = 0
        
        with st.form(key=f"add_scac_{st.session_state.form_key}"):
            scac_code = st.text_input("SCAC Code")
            carrier_name = st.text_input("Carrier Name")
            ship_mode = st.text_input("Ship Mode")
            details = st.text_area("Details (optional)", height=100, help="Additional information about this carrier")
            
            if st.form_submit_button("Add SCAC"):
                # Only require the first 3 fields (details is optional)
                if all([scac_code, carrier_name, ship_mode]):
                    # Use empty string if details is not provided
                    details_to_save = details if details.strip() else "No additional details provided"
                    
                    if add_scac(scac_code.upper(), carrier_name, ship_mode, details_to_save):
                        st.success("SCAC added successfully!")
                        # Increment form key to clear the form
                        st.session_state.form_key += 1
                        st.rerun()
                    else:
                        st.error("SCAC code already exists!")
                else:
                    st.error("Please fill in SCAC Code, Carrier Name, and Ship Mode. Details are optional.")
    
    with tab2:
        st.subheader("All SCACs")
        scacs_df = get_all_scacs()
        if len(scacs_df) > 0:
            st.dataframe(scacs_df, hide_index=True)
        else:
            st.info("No SCACs in database yet.")
    
    with tab3:
        st.subheader("Manage Data")
        st.warning("⚠️ Use with caution - these actions cannot be undone!")
        
        scacs_df = get_all_scacs()
        if len(scacs_df) > 0:
            st.write("**Delete Individual SCACs:**")
            for _, row in scacs_df.iterrows():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{row['scac_code']} - {row['carrier_name']}")
                with col2:
                    if st.button("Delete", key=f"del_{row['id']}"):
                        delete_scac(row['id'])
                        st.rerun()



if __name__ == "__main__":
    main()
