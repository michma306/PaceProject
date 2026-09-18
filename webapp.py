import warnings
warnings.filterwarnings("ignore", message=".*Accessing `__path__` from.*")
from transformers.utils import logging
logging.set_verbosity_error()

import streamlit as st
from input_module import run_input_module
from analysis_module import run_analysis_module
from output_module import run_output_module, generate_ai_explanation_with_llm


def main():
    st.set_page_config(page_title="PaceSyncAI", layout="wide")
    st.title("PaceSyncAI")
    st.write("AI-powered duplicate work detection and collaboration opportunity finder")

    #set up all dataframe buckets for use

    if "work_item_df" not in st.session_state:
        st.session_state.work_item_df = None

    if "pairwise_results_df" not in st.session_state:
        st.session_state.pairwise_results_df = None

    if "final_results_df" not in st.session_state:
        st.session_state.final_results_df = None

    #set up the input UX

    st.subheader("Step 1: Upload Work Files from the Folder Selected")

    uploaded_files = st.file_uploader(
        "Upload a folder",
        accept_multiple_files="directory",
        type=["txt", "docx"]
    )

    #run input module
    if st.button("Run Input Module"):
        if not uploaded_files:
            st.warning("Please upload files first.")
        else:
            with st.spinner("Running Input Module now......"):
                st.session_state.work_item_df = run_input_module(uploaded_files)

            st.success(f"Input Module completed. Uploaded {len(uploaded_files)} files.")

    #print the result
    if st.session_state.work_item_df is not None:
        st.write("Structured work-item dataframe:")
        st.dataframe(st.session_state.work_item_df)

        # choose rows where the file was not extracted properly
        failed_rows = st.session_state.work_item_df[st.session_state.work_item_df["extraction_status"] == "Failed"]

        if not failed_rows.empty:
            st.warning("Some files failed extraction. Please enter missing information manually.")

            # for failed rows, ask for manual inputs
            for row_index, row in failed_rows.iterrows():
                with st.form(key=f"manual_form_{row_index}"):
                    st.subheader(f"Manual input for: {row['source_filename']}")

                    manual_description = st.text_area("Standardized description")
                    manual_business_function = st.text_input("Business function")
                    manual_deliverable_type = st.text_input("Deliverable type")
                    manual_time_period = st.text_input("Time period")
                    manual_stakeholder = st.text_input("Stakeholder")

                    submitted = st.form_submit_button("Save Manual Input")

                    # save the manual inputs into dataframe
                    if submitted:
                        st.session_state.work_item_df.at[row_index, "standardized_description"] = manual_description
                        st.session_state.work_item_df.at[row_index, "business_function"] = manual_business_function
                        st.session_state.work_item_df.at[row_index, "deliverable_type"] = manual_deliverable_type
                        st.session_state.work_item_df.at[row_index, "time_period"] = manual_time_period
                        st.session_state.work_item_df.at[row_index, "stakeholder"] = manual_stakeholder
                        st.session_state.work_item_df.at[row_index, "extraction_status"] = "Manual"

                        st.success("Manual input saved.")
                        st.rerun()

    # set up the analysis engine
    st.subheader("Analysis Settings")
    semantic_threshold = st.slider("Semantic Similarity Threshold", 0.0, 1.0, 0.70)
    duplication_threshold = st.slider("Duplication Risk Score Threshold", 0, 100, 85)
    collaboration_threshold = st.slider("Collaboration Opportunity Threshold", 0, 100, 65)

    st.subheader("Step 2: Analysis Module")
    if st.button("Run Analysis Module"):
        if st.session_state.work_item_df is None:
            st.warning("Please run the Input Module first.")
        else:
            with st.spinner("Running Analysis Module now....."):
                st.session_state.pairwise_results_df = run_analysis_module(
                    st.session_state.work_item_df,
                    semantic_threshold=semantic_threshold,
                    duplication_threshold=duplication_threshold,
                    collaboration_threshold=collaboration_threshold
                )
            st.success("Analysis Module completed.")

    if st.session_state.pairwise_results_df is not None:
        st.write("Pairwise analysis results:")
        st.dataframe(st.session_state.pairwise_results_df)


    #Set up the output phase
    st.subheader("Step 3: Output Module")

    # error handling and running output processing.
    if st.button("Run Output Module"):
        if st.session_state.work_item_df is None:
            st.warning("Please run the Input Module first.")
        elif st.session_state.pairwise_results_df is None:
            st.warning("Please run the Analysis Module first.")
        else:
            st.session_state.final_results_df = run_output_module(
                st.session_state.work_item_df,
                st.session_state.pairwise_results_df
            )
            st.success("Output Module completed.")

    # display results and details in dataframe.     
    if st.session_state.final_results_df is not None:
        st.write("Final ranked results:")

        display_columns = [
            "pair_id",
            "file_1",
            "file_2",
            "pacesync_score",
            "classification",
            "recommended_action"
        ]

        st.dataframe(st.session_state.final_results_df[display_columns])

        # display details of a certain selected pair
        st.subheader("Result Details")
        selected_pair = st.selectbox(
            "Select Pair ID",
            st.session_state.final_results_df["pair_id"]
        )
        selected_row = st.session_state.final_results_df[st.session_state.final_results_df["pair_id"] == selected_pair]
        st.write("Detailed result:")
        st.dataframe(selected_row)
        
        # user may click to ask for AI explanations
        if st.button("Click for AI Explanation"):
            row = selected_row.iloc[0]
            explanation = generate_ai_explanation_with_llm(row)
            st.info(explanation)            

        # user may click to download the entire CSV
        st.download_button(
            label="Download Final Results as CSV",
            data=st.session_state.final_results_df.to_csv(index=False),
            file_name="pacesync_results.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
