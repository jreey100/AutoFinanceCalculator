import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os

st.set_page_config(page_title="Simple Finance App", page_icon="💰", layout="wide")

category_file = "categories.json"
budget_file = "budgets.json"

if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": [],
    }

if "budgets" not in st.session_state:
    st.session_state.budgets = {}

if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

if os.path.exists(budget_file):
    with open(budget_file, "r") as f:
        st.session_state.budgets = json.load(f)

for cat in st.session_state.categories.keys():
    st.session_state.budgets.setdefault(cat, 0.0)


def save_categories():
    with open(category_file, "w") as f:
        json.dump(st.session_state.categories, f) 


def save_budgets():
    with open(budget_file, "w") as f:
        json.dump(st.session_state.budgets, f)


def categorize_transactions(df):
    df["Category"] = "Uncategorized"

    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue

        lowered_keywords = [keyword.lower().strip() for keyword in keywords]
        for idx, row in df.iterrows():  # iterate over each row
            details = row["Details"].lower()
            if details in lowered_keywords:
                df.at[idx, "Category"] = category 

    return df
            

def load_transactions(file):
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns] 
        df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y")  # date, name of month, year
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
                    if new_category not in st.session_state.categories:  # add category
                        st.session_state.categories[new_category] = []
                        # also initialize a budget entry for this new category
                        st.session_state.budgets.setdefault(new_category, 0.0)
                        save_categories()
                        save_budgets()
                        st.rerun()


                st.subheader("Category Budgets")

                cols = st.columns(3)
                for i, cat in enumerate(st.session_state.categories.keys()):
                    with cols[i % 3]:
                        current_value = float(st.session_state.budgets.get(cat, 0.0))
                        st.session_state.budgets[cat] = st.number_input(
                            f"{cat} budget",
                            min_value=0.0,
                            step=10.0,
                            value=current_value,
                            key=f"budget_{cat}",
                        )

                if st.button("Save Budgets"):
                    save_budgets()
                    st.success("Budgets saved to budgets.json")


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
                        new_category_val = row["Category"]
                        if row["Category"] == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                         
                        details = row["Details"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category_val
                        add_keyword_to_category(new_category_val, details)

                st.subheader("Expense Summary")
                category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index() 
                category_totals = category_totals.sort_values(by="Amount", ascending=False)  # sort in descending order

                # add budget information
                category_totals["Budget"] = category_totals["Category"].map(
                    lambda c: st.session_state.budgets.get(c, 0.0)
                )
                category_totals["Remaining"] = category_totals["Budget"] - category_totals["Amount"]
                category_totals["% Used"] = category_totals.apply(
                    lambda r: round((r["Amount"] / r["Budget"]) * 100, 1) if r["Budget"] > 0 else 0.0,
                    axis=1,
                )

                st.dataframe(
                    category_totals,
                    column_config={
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED"),
                        "Budget": st.column_config.NumberColumn("Budget", format="%.2f AED"),
                        "Remaining": st.column_config.NumberColumn("Remaining", format="%.2f AED"),
                        "% Used": st.column_config.NumberColumn("% Used", format="%.1f %%"),
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
                st.metric("Total Payments", f"{total_payments:,.2f} AED")
                st.write(credits_df)


main()
