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
    try:
        c = conn.cursor()
        
        # Ensure table exists first
        c.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                Player TEXT,
                score INTEGER,
                correct_answers INTEGER,
                total_questions INTEGER,
                timestamp TEXT
            )
        """)
        
        c.execute("INSERT INTO scores (Player, score, correct_answers, total_questions, timestamp) VALUES (?, ?, ?, ?, ?)",
                 (player_name, score, correct, total, datetime.now().isoformat()))
        conn.commit()
        return True
    except Exception as e:
        print(f"Save score error: {e}")
        return False
    finally:
        conn.close()

def get_leaderboard():
    conn = sqlite3.connect('scac_game.db')
    try:
        # First check if the scores table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scores';")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            # Create the scores table if it doesn't exist - WITH total_questions column
            cursor.execute("""
                CREATE TABLE scores (
                    Player TEXT,
                    score INTEGER,
                    correct_answers INTEGER,
                    total_questions INTEGER,
                    timestamp TEXT
                )
            """)
            conn.commit()
            # Return empty DataFrame
            return pd.DataFrame(columns=['Player', 'best_score', 'best_correct', 'games_played', 'last_played'])
        
        # Table exists, try to read data
        df = pd.read_sql_query("""
            SELECT Player, MAX(score) as best_score, 
                   MAX(correct_answers) as best_correct,
                   COUNT(*) as games_played,
                   MAX(timestamp) as last_played
            FROM scores 
            GROUP BY Player 
            ORDER BY best_score DESC
        """, conn)
        
        return df
        
    except Exception as e:
        print(f"Database error: {e}")  # For debugging
        # Return empty DataFrame as fallback
        return pd.DataFrame(columns=['Player', 'best_score', 'best_correct', 'games_played', 'last_played'])
    
    finally:
        conn.close()

def delete_leaderboard_user(player_name):
    conn = sqlite3.connect('scac_game.db')
    c = conn.cursor()
    c.execute("DELETE FROM scores WHERE Player = ?", (player_name,))
    conn.commit()
    conn.close()

def get_enhanced_leaderboard():
    conn = sqlite3.connect('scac_game.db')
    try:
        # First ensure the table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scores';")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            # Create the scores table if it doesn't exist
            cursor.execute("""
                CREATE TABLE scores (
                    Player TEXT,
                    score INTEGER,
                    correct_answers INTEGER,
                    total_questions INTEGER,
                    timestamp TEXT
                )
            """)
            conn.commit()
            conn.close()
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=['Player', 'best_score', 'best_correct', 'games_played', 'accuracy_pct', 'last_played', 'time_in_lead'])
        
        df = pd.read_sql_query("""
            SELECT Player, 
                   MAX(score) as best_score, 
                   MAX(correct_answers) as best_correct,
                   COUNT(*) as games_played,
                   ROUND(AVG(CAST(correct_answers AS FLOAT) / total_questions * 100), 1) as accuracy_pct,
                   MAX(timestamp) as last_played
            FROM scores 
            GROUP BY Player 
            ORDER BY best_score DESC
        """, conn)
        conn.close()
        
        # Add time in lead for top player
        if len(df) > 0:
            df['time_in_lead'] = ''
            top_player = df.iloc[0]['Player']
            
            # Get when this player first achieved the top score
            try:
                conn = sqlite3.connect('scac_game.db')
                first_top_score = pd.read_sql_query("""
                    SELECT MIN(timestamp) as first_top
                    FROM scores 
                    WHERE Player = ? AND score = (
                        SELECT MAX(score) FROM scores WHERE Player = ?
                    )
                """, conn, params=[top_player, top_player])
                conn.close()
                
                if not first_top_score.empty and first_top_score.iloc[0]['first_top']:
                    from datetime import datetime
                    first_top_time = datetime.fromisoformat(first_top_score.iloc[0]['first_top'])
                    time_diff = datetime.now() - first_top_time
                    days = time_diff.days
                    hours = time_diff.seconds // 3600
                    
                    if days > 0:
                        df.loc[0, 'time_in_lead'] = f"{days}d {hours}h"
                    else:
                        df.loc[0, 'time_in_lead'] = f"{hours}h"
            except:
                # If time calculation fails, just leave it empty
                pass
        else:
            # If no data, add the time_in_lead column
            df['time_in_lead'] = ''
        
        return df
        
    except Exception as e:
        print(f"Enhanced leaderboard error: {e}")
        conn.close()
        # Return empty DataFrame as fallback
        return pd.DataFrame(columns=['Player', 'best_score', 'best_correct', 'games_played', 'accuracy_pct', 'last_played', 'time_in_lead'])

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
    available_scacs = scacs_df    
    # Separate SCACs with meaningful details for bonus questions
    scacs_with_details = available_scacs[
        (available_scacs['details'].notna()) & 
        (available_scacs['details'].str.strip() != '') & 
        (available_scacs['details'] != 'No additional details provided')
    ]
    
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
    
    # First select a SCAC, then decide question type based on ship mode
    correct_scac = available_scacs.sample(1).iloc[0]
    ship_mode = correct_scac['ship_mode'].strip()

    # Determine if this should be a bonus question based on ship mode
    if ship_mode == "TL Imports" or ship_mode == "SP (Small Parcel)" or ship_mode == "IM (intermodal)":
        # Always bonus for TL Imports, SP, and IM (intermodal)
        is_bonus = True
    else:
        # All other ship modes: lower chance (15% instead of 30%)
        has_details = (pd.notna(correct_scac['details']) and 
                      correct_scac['details'].strip() != '' and 
                      correct_scac['details'] != 'No additional details provided')
        is_bonus = has_details and random.random() < 0.15

    # Select question type based on bonus status
    if is_bonus:
        question_type = random.choice(bonus_question_types)
    else:
        question_type = random.choice(regular_question_types)
    
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
        # Check for similar carrier names
        similar_carriers = get_similar_carriers(correct_scac['carrier_name'], scacs_df)
        
        if len(similar_carriers) > 0:
            # Similar carriers found - use "select all that apply" format
            cleaned_name = clean_carrier_name(correct_scac['carrier_name'])
            
            # Get all ship modes for similar carriers (including the correct one)
            all_similar = similar_carriers + [correct_scac]
            all_ship_modes = [carrier['ship_mode'] for carrier in all_similar]
            correct_ship_modes = list(set(all_ship_modes))  # Remove duplicates
            
            # Get some wrong ship modes from other carriers
            other_ship_modes = scacs_df[~scacs_df['carrier_name'].str.contains(cleaned_name.split()[0], case=False, na=False)]['ship_mode'].unique().tolist()
            wrong_ship_modes = random.sample(other_ship_modes, min(2, len(other_ship_modes)))
            
            # Combine all options
            all_options = correct_ship_modes + wrong_ship_modes
            random.shuffle(all_options)
            
            return {
                'type': 'multi_select',
                'is_bonus': False,
                'question': f"What are ALL the ship modes that {cleaned_name} handles? (Select all that apply)",
                'choices': all_options,
                'correct_answers': correct_ship_modes,  # Multiple correct answers
                'scac_id': correct_scac['id'],
                'hint': f"Think about all the different services {cleaned_name} might offer"
            }
        else:
            # No similar carriers - use regular single answer format
            display_name = correct_scac['carrier_name']
            if has_parenthetical_text(display_name):
                display_name = clean_carrier_name(display_name)
            
            return {
                'type': 'text',
                'is_bonus': False,
                'question': f"What is the ship mode for {correct_scac['scac_code']} ({display_name})?",
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
    elif question_type == "bonus_multiple_choice":
        # Check if this SCAC has meaningful details
        has_meaningful_details = (pd.notna(correct_scac['details']) and 
                                correct_scac['details'].strip() != '' and 
                                correct_scac['details'] != 'No additional details provided')
        
        if has_meaningful_details:
            # Check for duplicate details before using details-based question
            current_details = correct_scac['details'].strip().lower()
            duplicate_details = scacs_df[
                (scacs_df['id'] != correct_scac['id']) & 
                (scacs_df['details'].str.strip().str.lower() == current_details)
            ]
            
            if len(duplicate_details) > 0:
                # Details are not unique, fall back to ship mode question
                question_text = f"🌟 BONUS: Which carrier has the SCAC code {correct_scac['scac_code']} ?"
                # Add warning in hint
                hint_text = f"SCAC: {correct_scac['scac_code']}, Ship Mode: {correct_scac['ship_mode']} (Note: Multiple carriers have similar details)"
            else:
                # Details are unique, use details-based question
                details_clue = correct_scac['details'][:200] + "..." if len(correct_scac['details']) > 200 else correct_scac['details']
                question_text = f"🌟 BONUS: Which carrier is associated with this service/detail: '{details_clue}'?"
                hint_text = f"SCAC: {correct_scac['scac_code']}, Ship Mode: {correct_scac['ship_mode']}"
        else:
            # Use ship mode-based question for TL Imports/SP without details
            question_text = f"🌟 BONUS: Which carrier has the SCAC code {correct_scac['scac_code']}?"
            hint_text = f"SCAC: {correct_scac['scac_code']}, Ship Mode: {correct_scac['ship_mode']}"
        
        # Get wrong answers - avoid carriers with same details
        if has_meaningful_details:
            # Exclude carriers with identical details from wrong answers
            current_details = correct_scac['details'].strip().lower()
            other_carriers = scacs_df[
                (scacs_df['id'] != correct_scac['id']) & 
                (scacs_df['details'].str.strip().str.lower() != current_details)
            ]['carrier_name'].tolist()
            
            # If not enough unique carriers, fall back to all others
            if len(other_carriers) < 3:
                other_carriers = scacs_df[scacs_df['id'] != correct_scac['id']]['carrier_name'].tolist()
        else:
            other_carriers = scacs_df[scacs_df['id'] != correct_scac['id']]['carrier_name'].tolist()
        
        wrong_answers = random.sample(other_carriers, min(3, len(other_carriers)))
        
        choices = [correct_scac['carrier_name']] + wrong_answers
        random.shuffle(choices)
        
        return {
            'type': 'multiple_choice',
            'is_bonus': True,
            'question': question_text,
            'choices': choices,
            'correct_answer': correct_scac['carrier_name'],
            'scac_id': correct_scac['id'],
            'hint': hint_text
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
        
        # player_name name input
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
        
        # Check SCACs with details for bonus questions
        scacs_with_details = scacs_df[
            (scacs_df['details'].notna()) & 
            (scacs_df['details'].str.strip() != '') & 
            (scacs_df['details'] != 'No additional details provided')
        ]
    
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
                
                elif question['type'] == 'multi_select':
                   with st.form(key=f"ms_form_{st.session_state.total_questions}"):
                        st.write("**Select ALL correct answers:**")
                        selected_answers = []

                        # Remove duplicates for display while preserving original for scoring
                        unique_choices = list(dict.fromkeys(question['choices']))

        
                        for i, choice in enumerate(unique_choices):
                            if st.checkbox(choice, key=f"ms_{choice}_{i}_{st.session_state.total_questions}"):
                                selected_answers.append(choice)
        
                        col_a, col_b = st.columns([1, 1])
                        with col_a:
                            submitted = st.form_submit_button("Submit Answers (Press Enter)")
                        with col_b:
                            hint_clicked = st.form_submit_button("Show Hint")
        
                        if submitted:
                            process_answer(selected_answers, scacs_df)
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
                        # Handle different question types for wrong answers
                        question_type = getattr(st.session_state, 'last_question_type', 'text')
                        
                        if question_type == 'multi_select':
                            # Show detailed multi-select results
                            user_answers = getattr(st.session_state, 'last_user_answer', [])
                            correct_answers = getattr(st.session_state, 'last_correct_answer', [])
                            
                            st.error(f"❌ Wrong! {st.session_state.last_points} points")
                            
                            # Show what they got right/wrong
                            st.write("**Answer Breakdown:**")
                            
                            user_set = set(user_answers) if isinstance(user_answers, list) else set()
                            correct_set = set(correct_answers) if isinstance(correct_answers, list) else set()
                            
                            # Show correctly selected
                            correctly_selected = user_set.intersection(correct_set)
                            if correctly_selected:
                                st.write("✅ **Correctly selected:** " + ", ".join(sorted(correctly_selected)))
                            
                            # Show incorrectly selected
                            incorrectly_selected = user_set - correct_set
                            if incorrectly_selected:
                                st.write("❌ **Incorrectly selected:** " + ", ".join(sorted(incorrectly_selected)))
                            
                            # Show missed answers
                            missed_answers = correct_set - user_set
                            if missed_answers:
                                st.write("⚠️ **Missed correct answers:** " + ", ".join(sorted(missed_answers)))
                            
                            st.write(f"**All correct answers:** {', '.join(sorted(correct_answers))}")
                            
                        else:
                            # Regular single answer display
                            user_answer_display = getattr(st.session_state, 'last_user_answer', 'No answer')
                            if isinstance(user_answer_display, list):
                                user_answer_display = ", ".join(user_answer_display)
                            elif str(user_answer_display).strip() == "":
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
        
        # For text questions, check multiple validation methods
        if len(user_input) == 0:
            is_correct = False
        elif user_input == correct_answer:
            # Exact match
            is_correct = True
        else:
            # Try multiple validation approaches
            is_correct = False
            
            # Method 1: Remove spaces, hyphens, and check similarity
            user_clean = user_input.replace(' ', '').replace('-', '').replace('_', '')
            correct_clean = correct_answer.replace(' ', '').replace('-', '').replace('_', '')
            
            if user_clean == correct_clean:
                is_correct = True
            elif len(user_clean) >= 3 and user_clean in correct_clean:
                is_correct = True
            elif len(correct_clean) >= 3 and correct_clean in user_clean:
                is_correct = True
            
            # Method 2: Check if user input matches significant parts
            if not is_correct and len(user_input) >= 3:
                if user_input in correct_answer or correct_answer in user_input:
                    is_correct = True
            
            # Method 3: Word-based matching with enhanced logic
            if not is_correct:
                user_words = set(user_input.split())
                correct_words = set(correct_answer.split())
                
                # Remove common words that don't matter
                common_words = {'the', 'and', 'or', 'of', 'in', 'to', 'a', 'an', 'is', 'are', 'was', 'were', 'inc', 'llc', 'corp', 'company', 'co'}
                user_words_clean = user_words - common_words
                correct_words_clean = correct_words - common_words
                
                # Check for partial word matches (handles "tforce" vs "t-force")
                for user_word in user_words_clean:
                    for correct_word in correct_words_clean:
                        # Remove hyphens and spaces for comparison
                        user_word_clean = user_word.replace('-', '').replace('_', '')
                        correct_word_clean = correct_word.replace('-', '').replace('_', '')
                        
                        if user_word_clean == correct_word_clean:
                            is_correct = True
                            break
                        elif len(user_word_clean) >= 4 and user_word_clean in correct_word_clean:
                            is_correct = True
                            break
                        elif len(correct_word_clean) >= 4 and correct_word_clean in user_word_clean:
                            is_correct = True
                            break
                    if is_correct:
                        break
                
                # If still not correct, check overall word overlap
                if not is_correct and len(correct_words_clean) > 0:
                    overlap = len(user_words_clean.intersection(correct_words_clean))
                    is_correct = overlap >= len(correct_words_clean) * 0.6  # Increased threshold
            
            # Method 4: Fuzzy string matching for close matches
            if not is_correct:
                import difflib
                similarity = difflib.SequenceMatcher(None, user_input, correct_answer).ratio()
                if similarity >= 0.8:  # 80% similarity threshold
                    is_correct = True
                
            
    elif question['type'] == 'multi_select':
        # Handle multiple correct answers
        correct_answers = set(question['correct_answers'])
        user_answers = set(user_answer) if isinstance(user_answer, list) else set()
        
        # Check if user selected exactly the right answers
        is_correct = user_answers == correct_answers
        
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
    st.session_state.last_question_type = question['type']  # Store question type
    
    # Store correct answer(s) - handle both single and multiple answers
    if question['type'] == 'multi_select':
        st.session_state.last_correct_answer = question['correct_answers']  # List for multi-select
    else:
        st.session_state.last_correct_answer = question['correct_answer']  # Single answer
    
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
    
    leaderboard = get_enhanced_leaderboard()
    if len(leaderboard) > 0:
        st.dataframe(
            leaderboard,
            column_config={
                "Player": "Player",
                "best_score": "Best Score",
                "best_correct": "Best Correct",
                "games_played": "Games Played",
                "accuracy_pct": "Accuracy %",
                "time_in_lead": "Time in Lead",
                "last_played": "Last Played"
            },
            hide_index=True
        )
    else:
        st.info("No scores yet. Play some games to see the leaderboard!")

def get_similar_carriers(carrier_name, scacs_df, similarity_threshold=0.95):
    """Find carriers with similar names"""
    import difflib
    
    similar_carriers = []
    for _, row in scacs_df.iterrows():
        if row['carrier_name'] != carrier_name:
            # Calculate similarity ratio
            similarity = difflib.SequenceMatcher(None, carrier_name.lower(), row['carrier_name'].lower()).ratio()
            if similarity >= similarity_threshold:
                similar_carriers.append(row)
    
    return similar_carriers

def clean_carrier_name(carrier_name):
    """Remove text in parentheses from carrier name"""
    import re
    # Remove anything in parentheses and extra spaces
    cleaned = re.sub(r'\([^)]*\)', '', carrier_name).strip()
    # Remove extra spaces
    cleaned = ' '.join(cleaned.split())
    return cleaned

def has_parenthetical_text(carrier_name):
    """Check if carrier name contains parentheses"""
    return '(' in carrier_name and ')' in carrier_name

def admin_page():
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        st.header("🔒 Admin Access")
        st.info("Please enter your admin credentials to access the admin panel.")
        
        with st.form("admin_login"):
            username = st.text_input("Username:")
            password = st.text_input("Password:", type="password")
            login_button = st.form_submit_button("Login")

            if login_button:
                # Define your admin credentials here
                ADMIN_USERNAME = "WePayDFM"
                ADMIN_PASSWORD = "XXXXXXXXXXXX"

                if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    st.success("Login successful! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please try again.")
                    if username != ADMIN_USERNAME:
                        st.error(f"Username mismatch. Expected: '{ADMIN_USERNAME}', Got: '{username}'")
                    if password != ADMIN_PASSWORD:
                        st.error("Password mismatch.")
        ADMIN_USERNAME = "WePayDFM"
        ADMIN_PASSWORD = "XXXXXXXXXXXX"
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            st.session_state.admin_authenticated = True
            st.success("Login successful! Redirecting...")
            st.rerun()
        else:
            st.error("Invalid username or password. Please try again.")
        return
    
    # Add logout option
    if st.button("🚪 Logout", key="admin_logout"):
        st.session_state.admin_authenticated = False
        st.rerun()

    st.header("⚙️ Admin Panel")
    
    # Add admin notice
    st.info("🔒 **Admin Instructions:** Add and manage your SCAC data here. The data will only exist in the app, not in the public code.")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Add New SCAC", "View All SCACs", "Edit SCAC", "Manage Data", "Debug Queries", "Import/Export"])

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
    
        # Create two columns for SCAC and Leaderboard management
        col1, col2 = st.columns(2)
    
        with col1:
            st.write("### SCAC Management")
            scacs_df = get_all_scacs()
            if len(scacs_df) > 0:
                st.write("**Delete Individual SCACs:**")
                for _, row in scacs_df.iterrows():
                    scac_col1, scac_col2 = st.columns([3, 1])
                    with scac_col1:
                        st.write(f"{row['scac_code']} - {row['carrier_name']}")
                    with scac_col2:
                        if st.button("Delete", key=f"del_scac_{row['id']}"):
                            delete_scac(row['id'])
                            st.rerun()
            else:
                st.info("No SCACs in database to delete.")
        
        with col2:
            st.write("### Leaderboard Management")
            leaderboard_df = get_leaderboard()
            if len(leaderboard_df) > 0:
                st.write("**Delete Individual Users:**")
                for _, row in leaderboard_df.iterrows():
                    user_col1, user_col2 = st.columns([3, 1])
                    with user_col1:
                        st.write(f"{row['Player']} - Score: {row['best_score']}")
                    with user_col2:
                        if st.button("Delete", key=f"del_user_{row['Player']}"):
                            delete_leaderboard_user(row['Player'])
                            st.rerun()
            else:
                st.info("No users in leaderboard to delete.")

    with tab5:
        st.subheader("Debug Queries")
        st.info("Run custom queries to debug issues.")
    
        st.write("**Database Tables:**")
        conn = sqlite3.connect('scac_game.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(scores)")
        columns = cursor.fetchall()
        conn.close()
        st.write("Scores table columns:", columns)
    
        query_code = st.text_area("Enter your query:", 
                             placeholder="Example: scacs_df[scacs_df['carrier_name'].str.contains('RXO', case=False, na=False)][['carrier_name', 'ship_mode']]",
                             height=100)

        if st.button("Run Query"):
            if query_code.strip():
                try:
                    scacs_df = get_all_scacs()
                    result = eval(query_code)
                    st.write("**Query Result:**")
                    st.write(result)
                except Exception as e:
                    st.error(f"Query error: {str(e)}")
            else:
                st.warning("Please enter a query to run.")

    with tab6:
        st.subheader("Import/Export Data")
        st.info("💾 Backup and restore your SCAC database and leaderboard data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("### SCAC Database")
            
            # Export SCAC data
            if st.button("📤 Export SCAC Data to CSV"):
                scacs_df = get_all_scacs()
                if len(scacs_df) > 0:
                    csv = scacs_df.to_csv(index=False)
                    st.download_button(
                        label="Download SCAC Data",
                        data=csv,
                        file_name="scac_data.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No SCAC data to export")
            
            # Import SCAC data
            st.write("**Import SCAC Data:**")
            uploaded_scac_file = st.file_uploader("Choose SCAC CSV file", type="csv", key="scac_upload")
            if uploaded_scac_file is not None:
                if st.button("Import SCAC Data", type="primary"):
                    try:
                        import_df = pd.read_csv(uploaded_scac_file)
                        success_count = import_scac_data(import_df)
                        st.success(f"Successfully imported {success_count} SCAC records!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error importing SCAC data: {str(e)}")
        
        with col2:
            st.write("### Leaderboard Data")
            
            # Export leaderboard data
            if st.button("📤 Export Leaderboard to CSV"):
                scores_df = get_all_scores()
                if len(scores_df) > 0:
                    csv = scores_df.to_csv(index=False)
                    st.download_button(
                        label="Download Leaderboard Data",
                        data=csv,
                        file_name="leaderboard_data.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No leaderboard data to export")
            
            # Import leaderboard data
            st.write("**Import Leaderboard Data:**")
            uploaded_scores_file = st.file_uploader("Choose Leaderboard CSV file", type="csv", key="scores_upload")
            if uploaded_scores_file is not None:
                if st.button("Import Leaderboard Data", type="primary"):
                    try:
                        import_df = pd.read_csv(uploaded_scores_file)
                        success_count = import_scores_data(import_df)
                        st.success(f"Successfully imported {success_count} score records!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error importing leaderboard data: {str(e)}")

def get_all_scores():
    conn = sqlite3.connect('scac_game.db')
    df = pd.read_sql_query("SELECT * FROM scores", conn)
    conn.close()
    return df

def import_scac_data(import_df):
    conn = sqlite3.connect('scac_game.db')
    c = conn.cursor()
    success_count = 0
    error_count = 0
    error_messages = []
    
    for i, row in import_df.iterrows():
        try:
            # Check if all required columns exist
            if all(col in row.index for col in ['scac_code', 'carrier_name', 'ship_mode']):
                details = row.get('details', 'No additional details provided')
                c.execute("INSERT OR REPLACE INTO scacs (scac_code, carrier_name, ship_mode, details) VALUES (?, ?, ?, ?)",
                         (row['scac_code'], row['carrier_name'], row['ship_mode'], details))
                success_count += 1
            else:
                missing = [col for col in ['scac_code', 'carrier_name', 'ship_mode'] if col not in row.index]
                error_messages.append(f"Row {i}: Missing columns: {missing}")
                error_count += 1
        except Exception as e:
            error_messages.append(f"Row {i}: Error: {str(e)}")
            error_count += 1
    
    conn.commit()
    conn.close()
    
    if error_count > 0:
        st.error(f"Encountered {error_count} errors during import")
        for msg in error_messages[:10]:  # Show first 10 errors
            st.write(msg)
        if len(error_messages) > 10:
            st.write(f"...and {len(error_messages) - 10} more errors")
    
    return success_count

def import_scores_data(import_df):
    conn = sqlite3.connect('scac_game.db')
    c = conn.cursor()
    success_count = 0
    
    for _, row in import_df.iterrows():
        try:
            c.execute("INSERT INTO scores (Player, score, correct_answers, total_questions, timestamp) VALUES (?, ?, ?, ?, ?)",
                     (row['Player'], row['score'], row['correct_answers'], row['total_questions'], row['timestamp']))
            success_count += 1
        except Exception as e:
            continue  # Skip problematic rows
    
    conn.commit()
    conn.close()
    return success_count

if __name__ == "__main__":
    main()
