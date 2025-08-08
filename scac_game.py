def display_sand_timer(elapsed_time):
    # Calculate percentage of time remaining (60 seconds total)
    time_remaining = max(0, 60 - elapsed_time)
    percentage_remaining = time_remaining / 60
    
    # Color changes as time runs out
    if percentage_remaining > 0.5:
        color = "normal"  # Green
    elif percentage_remaining > 0.2:
        color = "off"     # Orange-ish
    else:
        color = "off"     # Red-ish
    
    # Use Streamlit's built-in components
    st.write("⏳")  # Hourglass emoji
    
    # Progress bar for time remaining
    st.write("Time Remaining:")
    st.progress(percentage_remaining)
    
    # Time display
    if time_remaining > 20:
        st.success(f"⏰ {time_remaining:.0f} seconds left")
    elif time_remaining > 5:
        st.warning(f"⏰ {time_remaining:.0f} seconds left")
    else:
        st.error(f"⏰ {time_remaining:.0f} seconds left")
