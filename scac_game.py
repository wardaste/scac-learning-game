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

def update_scac(scac_id, scac_code, carrier_name, ship_mode, details):
    conn = sqlite3.connect('scac_game.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE scacs SET scac_code = ?, carrier_name = ?, ship_mode = ?, details = ? WHERE id = ?",
                 (scac_code, carrier_name, ship_mode, details, scac_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
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
    # DEBUG: Print what we're working with
    print(f"DEBUG generate_question: Total SCACs: {len(scacs_df)}")
    print(f"DEBUG generate_question: Used questions: {st.session_state.used_questions}")
    
    available_scacs = scacs_df[~scacs_df['id'].isin(st.session_state.used_questions)]
    print(f"DEBUG generate_question: Available SCACs: {len(available_scacs)}")
    
    if len(available_scacs) == 0:
        print("DEBUG generate_question: No available SCACs - returning None")
        return None
    
    # Separate SCACs with meaningful details for bonus questions
    scacs_with_details = available_scacs[
        (available_scacs['details'].notna()) & 
        (available_scacs['details'].str.strip() != '') & 
        (available_scacs['details'] != 'No additional details provided')
    ]
    print(f"DEBUG generate_question: SCACs with details: {len(scacs_with_details)}")
    
    # Rest of your function...
    available_scacs = scacs_df[~scacs_df['id'].isin(st.session_state.used_questions)]
    
    if len(available_scacs) == 0:
        return None
    
    # Separate SCACs with meaningful details for bonus questions
    scacs_with_details = available_scacs[
        (available_scacs['details'].notna()) & 
        (available_scacs['details'].str.strip() != '') & 
        (available_scacs['details'] != 'No additional details provided')
    ]
    
    # Regular question types
    regular_question_types = [
        "carrier_from_scac",
        "scac_from_carrier", 
        "ship_mode_from_scac",
        "multiple_choice_carrier"
    ]
    
    # Bonus question types (only if we have SCACs with details)
    bonus_question_types = [
        "bonus_multiple_choice"
    ]
    
    # Decide if this should be a bonus question (30% chance if details available)
    is_bonus = False #len(scacs_with_details) > 0 and random.random() < 0.3
    
    if is_bonus:
        question_type = random.choice(bonus_question_types)
        correct_scac = scacs_with_details.sample(1).iloc[0]
    else:
        question_type = random.choice(regular_question_types)
        correct_scac = available_scacs.sample(1).iloc[0]
    
    # Regular questions (existing code)
    if question_type == "carrier_from_scac":
        return {
            'type': 'text',
            'is_bonus': False,
            'question': f"What is the carrier name for SCAC code: {correct_scac['scac_code']}?",
            'correct_answer': correct_scac['carrier_name'].lower(),
            'scac_id': correct_scac['id'],
            'hint': f"Ship Mode: {correct_scac['ship_mode']}"
        }
    
    elif question_type == "scac_from_carrier":
        return {
            'type': 'text',
            'is_bonus': False,
            'question': f"What is the SCAC code for: {correct_scac['carrier_name']}?",
            'correct_answer': correct_scac['scac_code'].upper(),
            'scac_id': correct_scac['id'],
            'hint': f"Ship Mode: {correct_scac['ship_mode']}"
        }
    
    elif question_type == "ship_mode_from_scac":
        return {
            'type': 'text',
            'is_bonus': False,
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
            'is_bonus': False,
            'question': f"Which carrier has the SCAC code: {correct_scac['scac_code']}?",
            'choices': choices,
            'correct_answer': correct_scac['carrier_name'],
            'scac_id': correct_scac['id'],
            'hint': f"Ship Mode: {correct_scac['ship_mode']}"
        }
    
    # BONUS QUESTIONS (multiple choice only)
    elif question_type in ["details_from_scac", "scac_from_details", "multiple_choice_details"]:
        # Get other SCACs with details for wrong answers
        other_scacs_with_details = scacs_with_details[scacs_with_details['id'] != correct_scac['id']]
        
        if len(other_scacs_with_details) >= 3:
            wrong_scacs = other_scacs_with_details.sample(3)
            wrong_answers = wrong_scacs['carrier_name'].tolist()
        else:
            # Fall back to any other carriers if not enough with details
            other_carriers = scacs_df[scacs_df['id'] != correct_scac['id']]['carrier_name'].tolist()
            wrong_answers = random.sample(other_carriers, min(3, len(other_carriers)))
        
        choices = [correct_scac['carrier_name']] + wrong_answers
        random.shuffle(choices)
        
        # Create a details clue (truncate if too long)
        details_clue = correct_scac['details'][:200] + "..." if len(correct_scac['details']) > 200 else correct_scac['details']
        
        return {
            'type': 'multiple_choice',
            'is_bonus': True,
            'question': f"🌟 BONUS: Which carrier is associated with this service/detail: '{details_clue}'?",
            'choices': choices,
            'correct_answer': correct_scac['carrier_name'],
            'scac_id': correct_scac['id'],
            'hint': f"SCAC: {correct_scac['scac_code']}, Ship Mode: {correct_scac['ship_mode']}"
        }

def calculate_score(time_taken, is_correct, is_bonus=False):
    if is_correct:
        # Base score calculation
        base_score = max(10, 100 - (time_taken * 1.5))
        
        # Double points for bonus questions
        if is_bonus:
            return int(base_score * 2)
        else:
            return int(base_score)
    else:
        # No penalty for bonus questions, regular penalty for others
        if is_bonus:
            return 0  # No penalty for wrong bonus answers
        else:
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
                # Reset everything for new game
                st.session_state.game_active = True
                st.session_state.score = 0
                st.session_state.correct_answers = 0
                st.session_state.total_questions = 0
                st.session_state.used_questions = []
                st.session_state.answer_submitted = False
                
                # Generate first question
                st.session_state.current_question = generate_question(scacs_df)
                st.session_state.question_start_time = time.time()
                
                # Debug: Check if question was generated
                if st.session_state.current_question is None:
                    st.error("DEBUG: Failed to generate first question!")
                else:
                    st.success("DEBUG: First question generated successfully!")
                
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
                # Reset the used questions list for new game
                st.session_state.used_questions = []
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
        # DEBUG INFO (temporary - remove later)
        st.write("=== DEBUG INFO ===")
        st.write(f"Game active: {st.session_state.game_active}")
        st.write(f"Current question exists: {st.session_state.current_question is not None}")
        st.write(f"Total SCACs in database: {len(scacs_df)}")
        st.write(f"Used questions: {len(st.session_state.used_questions)}")
        st.write(f"Used question IDs: {st.session_state.used_questions}")
        
        # Check SCACs with details for bonus questions
        scacs_with_details = scacs_df[
            (scacs_df['details'].notna()) & 
            (scacs_df['details'].str.strip() != '') & 
            (scacs_df['details'] != 'No additional details provided')
        ]
        st.write(f"SCACs with details for bonus: {len(scacs_with_details)}")
        st.write("=== END DEBUG ===")        
        with col1:
            # Display question
            question = st.session_state.current_question
            
            # Add bonus indicator
            if question.get('is_bonus', False):
                st.markdown("### 🌟 BONUS QUESTION 🌟")
                st.info("💰 Double points if correct, no penalty if wrong!")
            
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
                st.write(f"DEBUG: Before generating new question, used_questions: {st.session_state.used_questions}")
                
                # Reset for next question
                st.session_state.current_question = generate_question(scacs_df)
                
                st.write(f"DEBUG: After generate_question, current_question is None: {st.session_state.current_question is None}")
                
                if st.session_state.current_question:
                    st.session_state.question_start_time = time.time()
                    st.session_state.answer_submitted = False
                    # Clear the last answer info
                    if hasattr(st.session_state, 'last_answer_correct'):
                        delattr(st.session_state, 'last_answer_correct')
                    if hasattr(st.session_state, 'last_scac_info'):
                        delattr(st.session_state, 'last_scac_info')
                else:
                    st.error("DEBUG: Failed to generate next question!")
                
                st.rerun()

def process_answer(user_answer, scacs_df):
    question = st.session_state.current_question
    time_taken = time.time() - st.session_state.question_start_time
    
    # Store the answer time for display
    st.session_state.last_answer_time = time_taken
    
    # Check if answer is correct
    if question['type'] == 'text':
        user_input = user_answer.lower().strip()
        correct_answer = question['correct_answer'].lower().strip()
        
        # For text questions, check if user answer contains key parts or vice versa
        if len(user_input) == 0:
            is_correct = False
        elif user_input == correct_answer:
            # Exact match
            is_correct = True
        elif len(user_input) >= 3 and user_input in correct_answer:
            # User answer is contained in correct answer
            is_correct = True
        elif len(correct_answer) >= 3 and correct_answer in user_input:
            # Correct answer is contained in user answer
            is_correct = True
        else:
            # Check for partial word matches
            user_words = set(user_input.split())
            correct_words = set(correct_answer.split())
            
            # Remove common words that don't matter
            common_words = {'the', 'and', 'or', 'of', 'in', 'to', 'a', 'an', 'is', 'are', 'was', 'were'}
            user_words = user_words - common_words
            correct_words = correct_words - common_words
            
            # If user got at least 50% of the important words right
            if len(correct_words) > 0:
                overlap = len(user_words.intersection(correct_words))
                is_correct = overlap >= len(correct_words) * 0.5
            else:
                is_correct = False
                
    else:  # multiple choice
        is_correct = user_answer == question['correct_answer']
    
    # Calculate score (check if it's a bonus question)
    is_bonus = question.get('is_bonus', False)
    points = calculate_score(time_taken, is_correct, is_bonus)
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
    st.info("🔒 **Admin Instructions:** Add and manage your SCAC data here. The data will only exist in the app, not in the public code.")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Add New SCAC", "View All SCACs", "Edit SCAC", "Manage Data"])
    
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
        st.subheader("Edit SCAC")
        scacs_df = get_all_scacs()
        
        if len(scacs_df) > 0:
            # Create a selectbox with SCAC codes and carrier names
            scac_options = {}
            for _, row in scacs_df.iterrows():
                display_name = f"{row['scac_code']} - {row['carrier_name']}"
                scac_options[display_name] = row['id']
            
            selected_display = st.selectbox("Select SCAC to edit:", list(scac_options.keys()))
            
            if selected_display:
                selected_id = scac_options[selected_display]
                selected_row = scacs_df[scacs_df['id'] == selected_id].iloc[0]
                
                # Edit form
                with st.form("edit_scac"):
                    st.write(f"**Editing:** {selected_display}")
                    
                    edit_scac_code = st.text_input("SCAC Code", value=selected_row['scac_code'])
                    edit_carrier_name = st.text_input("Carrier Name", value=selected_row['carrier_name'])
                    edit_ship_mode = st.text_input("Ship Mode", value=selected_row['ship_mode'])
                    edit_details = st.text_area("Details (optional)", value=selected_row['details'], height=100)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Update SCAC", type="primary"):
                            if all([edit_scac_code, edit_carrier_name, edit_ship_mode]):
                                details_to_save = edit_details if edit_details.strip() else "No additional details provided"
                                
                                if update_scac(selected_id, edit_scac_code.upper(), edit_carrier_name, edit_ship_mode, details_to_save):
                                    st.success("SCAC updated successfully!")
                                    st.rerun()
                                else:
                                    st.error("Error updating SCAC. SCAC code might already exist.")
                            else:
                                st.error("Please fill in SCAC Code, Carrier Name, and Ship Mode.")
                    
                    with col2:
                        if st.form_submit_button("Cancel", type="secondary"):
                            st.info("Edit cancelled.")
        else:
            st.info("No SCACs available to edit. Add some SCACs first.")
    
    with tab4:
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
        else:
            st.info("No SCACs in database to delete.")



if __name__ == "__main__":
    main()
