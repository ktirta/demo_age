import streamlit as st
import pandas as pd
from PIL import Image
import re
import os
from urllib.parse import urlencode
st.set_page_config(layout="wide")

# Load pair data
pairs_df = pd.read_csv("pairs.csv")
# Rename columns
pairs_df.rename(columns={'img_test_i': 'img_path_i', 'img_valid_j': 'img_path_j'}, inplace=True)
unique_i_images = pairs_df['img_path_i'].unique()

# Extract true age from image filename
def extract_age(img_path):
    match = re.search(r'/(\d+)_', img_path)
    return int(match.group(1)) if match else None

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = ""
if 'step' not in st.session_state:
    st.session_state.step = -1  # Start at -1 to ask for ID
    st.session_state.results = {}

st.title("Age Estimation and Pairwise Comparison App")
# Inject JS to scroll to top on page load
st.markdown("""
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            setTimeout(function() {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }, 100);  // small delay to ensure page is rendered
        });
    </script>
""", unsafe_allow_html=True)


# Step -1: Ask for user ID
if st.session_state.step == -1:
    st.subheader("Enter Your User ID")
    with st.form("user_id_form"):
        user_id = st.text_input("User ID:")
        submitted = st.form_submit_button("Start")
        if submitted and user_id:
            st.session_state.user_id = user_id
            st.session_state.step = 0
            st.rerun()

# Age Estimation and Comparison
elif st.session_state.step < len(unique_i_images):
    # Initialize session state per-image storage
    if 'age_inputs' not in st.session_state:
        st.session_state.age_inputs = {}
    if 'radio_choices' not in st.session_state:
        st.session_state.radio_choices = {}

    current_img_i = unique_i_images[st.session_state.step]
    age_i = extract_age(current_img_i)
    comparisons = pairs_df[pairs_df['img_path_i'] == current_img_i]
    image_i = Image.open(current_img_i)
    radio_key_prefix = f"step_{st.session_state.step}_"

    # --- Top navigation buttons ---
    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        if st.button("Back ") and st.session_state.step > 0:
            st.session_state.step -= 1
            st.rerun()
    with col_next:
        if st.button("Next "):
            # Save age and radio answers
            estimated_age = st.session_state.get(f"slider_{current_img_i}", 25)
            older_than = []
            younger_than = []

            for _, row in comparisons.iterrows():
                img_j = row['img_path_j']
                age_j = extract_age(img_j)
                radio_val = st.session_state.radio_choices.get(img_j, None)
                if radio_val == f"I":
                    older_than.append(age_j)
                elif radio_val == f"J":
                    younger_than.append(age_j)

            st.session_state.results[current_img_i] = {
                "img_path_i": current_img_i,
                "true_age": age_i,
                "estimated_age": estimated_age,
                "user_predict_this_img_to_be_older_than": older_than,
                "user_predict_this_img_to_be_younger_than": younger_than,
            }

            # Clear current radio inputs
            for _, row in comparisons.iterrows():
                img_j = row['img_path_j']
                if img_j in st.session_state.radio_choices:
                    del st.session_state.radio_choices[img_j]

            st.session_state.step += 1
            st.rerun()
    # Show slider and store value in session state
    st.header("1. Age Estimation")
    st.image(image_i, caption="Image I", width=200)
    default_slider_val = st.session_state.age_inputs.get(current_img_i, 25)
    slider_val = st.slider("Estimate this person's age:", 0, 100, default_slider_val, key=f"slider_{current_img_i}")
    st.session_state.age_inputs[current_img_i] = slider_val


    # Age estimation
    st.header("2. Who Looks Older?")
    comparison_rows = [comparisons.iloc[i:i+4] for i in range(0, len(comparisons), 4)]  # 4 pairs per row
    older_than = []
    younger_than = []
    for row_index, row_group in enumerate(comparison_rows):
        pair_cols = st.columns(4)  # Four image pairs per row

        for idx, (_, row) in enumerate(row_group.iterrows()):
            img_j = row['img_path_j']
            age_j = extract_age(img_j)
            image_j = Image.open(img_j)

            with pair_cols[idx]:
                # Side-by-side images: I and J
                col_i, col_j = st.columns(2)
                with col_i:
                    st.image(image_i, caption="Image I", width=150)
                with col_j:
                    st.image(image_j, caption="Image J", width=150)

                # Radio button with unique key
                choice = st.radio(
                    "Who looks older?",
                    [f"I", f"J"],
                    index=0 if img_j not in st.session_state.radio_choices
                        else [f"I", f"J"].index(st.session_state.radio_choices[img_j]),
                    key=f"radio_{st.session_state.step}_{img_j}",
                    horizontal=True
                )

                if choice.startswith("I"):
                    older_than.append(age_j)
                else:
                    younger_than.append(age_j)

                st.session_state.radio_choices[img_j] = choice

        # Add spacing between rows
        if row_index < len(comparison_rows) - 1:
            st.markdown("<br>")
            st.markdown("---")
            st.markdown("<br>")

    col_prev, col_next = st.columns([1, 1])
    with col_prev:
        if st.button("Back") and st.session_state.step > 0:
            st.session_state.step -= 1
            # Optionally remove previous result to allow re-editing
            prev_img = unique_i_images[st.session_state.step]
            st.session_state.results.pop(prev_img, None)
            st.rerun()

    with col_next:
        if st.button("Next"):
            estimated_age = st.session_state.get(f"slider_{current_img_i}", 25)
            st.session_state.results[current_img_i] = {
                "img_path_i": current_img_i,
                "true_age": age_i,
                "estimated_age": estimated_age,
                "user_predict_this_img_to_be_older_than": older_than,
                "user_predict_this_img_to_be_younger_than": younger_than,
            }
            st.session_state.step += 1
        st.rerun()

# Completion
else:
    st.success("Thank you! All images processed.")

    results_df = pd.DataFrame(st.session_state.results.values())
    st.dataframe(results_df)

    filename = f"./results/results_{st.session_state.user_id}.csv"
    results_df.to_csv(filename, index=False)

    st.download_button(
        label="Download Your Results",
        data=results_df.to_csv(index=False),
        file_name=filename,
        mime="text/csv"
    )
