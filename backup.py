import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Simple Finance App", page_icon="💰", layout="wide")

category_file = "categories.json"
# any action on the page(e.g uploading a file) refereshes the entire page
# need to explicitly store data in session 
if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": [],
    }

if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

def save_categories():
    with open("categories.json", "w") as f:
        json.dump(st.session_state.categories, f) 

def categorize_transactions(df):
    df["Category"] = "Uncategorized"

    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue

        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        for idx, row in df.iterrows(): # iterate over each row
            details = row["Details"].lower()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category 

    return df
            
def load_transactions(file):
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns] 
        df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y") # date, name of month, year
    
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

def main():
    st.title("Simple Finance Dashboard")

    uploaded_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])

    if uploaded_file is not None:
        df = load_transactions(uploaded_file)

        if df is not None:
            debits_df = df[df["Debit/Credit"] == "Debit"].copy()
            credits_df = df[df["Debit/Credit"] == "Credit"].copy()

            st.session_state.debits_df = debits_df.copy()

            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payments (Credits)"])
            with tab1:
                new_category = st.text_input("New Category Name")
                add_button = st.button("Add Category")

                if add_button and new_category:
                    if new_category not in st.session_state.categories: #add category
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()


                #st.write(debits_df)
                st.subheader("Your Expenses")
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2fAED"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )

                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        if row["Category"] == st.session_state.debits_df.at[idx,"Category"]:
                            continue
                         
                        details = row["Details"]
                        st.session_state.debits_df.at[idx,"Category"] = new_category
                        add_keyword_to_category(new_category, details)

                st.subheader("Expense Sumamry")
                category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index() 
                category_totals = category_totals.sort_values(by="Amount", ascending=False) # sort in descending order

                st.dataframe(
                    category_totals,
                             column_config={
                                 "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED")
                             },
                    use_container_width=True,
                    hide_index=True
                )

                fig = px.pie(
                    category_totals, 
                    values="Amount",
                    names="Category",
                    title="Expenses by Category",
                )

                test = px.bar(
                    category_totals,
                    x="Category",
                    y="Amount",
                    title="Expenses by Category - Bar Chart",
                )
                st.plotly_chart(fig, use_container_width=True)
                st.plotly_chart(test, use_container_width=True)

            with tab2:
                st.subheader("Payment Summary")
                total_payments = credits_df["Amount"].sum()
                st.metric("Total Payments",f"{total_payments:,.2f} AED")
                st.write(credits_df)


main()