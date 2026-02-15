import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Set Page Config
st.set_page_config(page_title="Shamnas Retirement Planner", layout="wide")
# --- HIDE STREAMLIT STYLE ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)
--

st.title("🛡️Shamna's Comprehensive Retirement Sustainability Planner")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Timeline & Inflation")
current_age = st.sidebar.slider("Current Age", 35, 55, 41)
retirement_age = st.sidebar.slider("Retirement Age", 50, 70, 60)
inflation_rate = st.sidebar.slider("Annual Inflation (%)", 4.0, 9.0, 6.0) / 100

st.sidebar.header("2. Existing Wealth & Assets")
current_portfolio = st.sidebar.number_input("Current MF Portfolio (₹)", value=3300000)
other_assets = st.sidebar.number_input("Other Assets (kannur home,etc) (₹)", value=2000000)

st.sidebar.header("3. Future Contributions")
monthly_sip = st.sidebar.number_input("Monthly SIP (₹)", value=100000)
pre_ret_return = st.sidebar.slider("Expected MF Return (%)", 8.0, 16.0, 12.0) / 100
post_ret_return = st.sidebar.slider("Post-Retirement Return (%)", 4.0, 9.0, 7.0) / 100

st.sidebar.header("4. Expenses")
current_monthly_exp = st.sidebar.number_input("Current Monthly Lifestyle Expense (₹)", value=100000)
one_time_exp = st.sidebar.number_input("One-time Major Outflows (Edu/Misc) (₹)", value=6480000)

# --- CALCULATIONS ---
years_to_ret = retirement_age - current_age
months_to_ret = years_to_ret * 12
monthly_rate_pre = pre_ret_return / 12

# Accumulation Data
acc_ages = np.arange(current_age, retirement_age + 1)
lump_vals, sip_vals, epf_vals, asset_vals = [], [], [], []

for y in range(len(acc_ages)):
    m = y * 12
    # Lumpsum part of MF
    lump_vals.append((current_portfolio * (1 + pre_ret_return)**y) / 1e7)
    # SIP part of MF
    sip = monthly_sip * (((1 + monthly_rate_pre)**m - 1) / monthly_rate_pre) * (1 + monthly_rate_pre) if m > 0 else 0
    sip_vals.append(sip / 1e7)
    # EPF (approx 8.1% growth)
    epf = (6000 * 12 * ((1 + 0.081)**y - 1) / 0.081) if y > 0 else 0
    epf_vals.append(epf / 1e7)
    # Other Assets (Assumed static or slow growth, here static as per your sheet)
    asset_vals.append(other_assets / 1e7)

total_at_ret = (lump_vals[-1] + sip_vals[-1] + epf_vals[-1] + asset_vals[-1]) * 1e7
corpus_after_one_time = total_at_ret - one_time_exp

# Withdrawal Simulation
exp_at_ret_monthly = current_monthly_exp * (1 + inflation_rate)**years_to_ret
dep_ages, dep_values = [], []
temp_corpus = corpus_after_one_time
temp_exp = exp_at_ret_monthly
age = retirement_age
monthly_rate_post = post_ret_return / 12
monthly_inflation = (1 + inflation_rate)**(1/12) - 1

while temp_corpus > 0 and age < 100:
    for m in range(12):
        temp_corpus = (temp_corpus * (1 + monthly_rate_post)) - temp_exp
        temp_exp = temp_exp * (1 + monthly_inflation)
        if temp_corpus <= 0: break
    age += 1
    dep_ages.append(age)
    dep_values.append(max(0, temp_corpus / 1e7))

# --- DASHBOARD UI ---
col1, col2, col3 = st.columns(3)
col1.metric("Net Worth at Retirement", f"₹{total_at_ret/1e7:.2f} Cr")
col2.metric("Post-Expense Corpus", f"₹{corpus_after_one_time/1e7:.2f} Cr")
col3.metric("Survival Age", f"{age if temp_corpus <= 0 else '100+'}")

# --- CLEAN CHART ---
fig = go.Figure()

# Phase 1: Stacked Growth
fig.add_trace(go.Scatter(x=acc_ages, y=asset_vals, stackgroup='one', name='Fixed Assets', line=dict(width=0)))
fig.add_trace(go.Scatter(x=acc_ages, y=epf_vals, stackgroup='one', name='EPF', line=dict(width=0)))
fig.add_trace(go.Scatter(x=acc_ages, y=lump_vals, stackgroup='one', name='Existing MF Growth', line=dict(width=0)))
fig.add_trace(go.Scatter(x=acc_ages, y=sip_vals, stackgroup='one', name='Future SIPs', line=dict(width=0)))

# Phase 2: Simple Depletion Line
fig.add_trace(go.Scatter(x=dep_ages, y=dep_values, name='Retirement Drawdown', line=dict(color='red', width=3, dash='dot')))

fig.add_vline(x=retirement_age, line_width=2, line_dash="dash", line_color="black")
fig.update_layout(
    title="Wealth accumulation vs. Retirement Withdrawal (Adjusted for Inflation)",
    xaxis_title="Age", yaxis_title="Crores (INR)",
    hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig, use_container_width=True)

st.write(f"### 📝 Strategy Note")
st.write(f"- Your **Other Assets** (₹1.32 Cr) provide a significant initial cushion.")
st.write(f"- By age {retirement_age}, inflation turns your ₹{current_monthly_exp/1000:.0f}k lifestyle into a ₹{exp_at_ret_monthly/1000:.0f}k requirement.")
