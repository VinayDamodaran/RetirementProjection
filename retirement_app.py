import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Set Page Config
st.set_page_config(page_title="Retirement Planner", layout="wide")

st.title("💸 Sham's Retirement & SIP Projector")
st.markdown("Adjust the sliders on the left to see how your corpus grows over time.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Initial Settings")
current_age = st.sidebar.slider("Current Age", 30, 55, 41)
retirement_age = st.sidebar.slider("Target Retirement Age", 45, 70, 60)

st.sidebar.header("Investment Inputs")
current_portfolio = st.sidebar.number_input("Current MF Portfolio (₹)", value=3300000, step=100000)
monthly_sip = st.sidebar.slider("Monthly SIP Amount (₹)", 10000, 500000, 100000, step=5000)
expected_return = st.sidebar.slider("Expected MF Return (%)", 5.0, 18.0, 12.0, 0.5) / 100

st.sidebar.header("EPF Settings")
epf_monthly = st.sidebar.number_input("Monthly EPF Contribution (₹)", value=6000)
epf_rate = st.sidebar.slider("EPF Interest Rate (%)", 5.0, 9.0, 8.1, 0.1) / 100

st.sidebar.header("One-time Expenses")
edu_exp = st.sidebar.number_input("Saashu Education (₹)", value=4000000)
patti_exp = st.sidebar.number_input("Patti Kutti (₹)", value=480000)
misc_exp = st.sidebar.number_input("Misc/Unforeseen (₹)", value=2000000)

# --- CALCULATIONS ---
years = retirement_age - current_age
months = years * 12
monthly_rate = expected_return / 12

# 1. MF Lumpsum Growth
fv_lumpsum = current_portfolio * (1 + expected_return)**years

# 2. SIP Growth (FV of Annuity Due)
if months > 0:
    fv_sip = monthly_sip * (((1 + monthly_rate)**months - 1) / monthly_rate) * (1 + monthly_rate)
else:
    fv_sip = 0

# 3. EPF Growth (Simple compound for approximation)
epf_fv = epf_monthly * 12 * ((1 + epf_rate)**years - 1) / epf_rate

total_corpus = fv_lumpsum + fv_sip + epf_fv
total_expenses = edu_exp + patti_exp + misc_exp
net_remaining = total_corpus - total_expenses

# --- DASHBOARD LAYOUT ---
col1, col2, col3 = st.columns(3)
col1.metric("Total Corpus", f"₹{total_corpus/1e7:.2f} Cr")
col2.metric("Total Expenses", f"₹{total_expenses/1e5:.1f} L")
col3.metric("Net Balance", f"₹{net_remaining/1e7:.2f} Cr", delta_color="normal")

# --- PROJECTION CHART ---
ages = np.arange(current_age, retirement_age + 1)
mf_growth = []
for y in range(len(ages)):
    m = y * 12
    lump = current_portfolio * (1 + expected_return)**y
    sip = monthly_sip * (((1 + monthly_rate)**m - 1) / monthly_rate) * (1 + monthly_rate) if m > 0 else 0
    mf_growth.append((lump + sip) / 1e7)

fig = go.Figure()
fig.add_trace(go.Scatter(x=ages, y=mf_growth, fill='tozeroy', name='MF Corpus (Cr)', line=dict(color='#1f77b4')))
fig.update_layout(title="Wealth Accumulation Over Time", xaxis_title="Age", yaxis_title="Crores (INR)", hovermode="x")
st.plotly_chart(fig, use_container_width=True)

# --- BREAKDOWN PIE ---
st.subheader("Asset Breakdown at Retirement")
c1, c2 = st.columns(2)

with c1:
    labels = ['MF (Lumpsum)', 'MF (SIP)', 'EPF']
    values = [fv_lumpsum, fv_sip, epf_fv]
    fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.3)])
    fig_pie.update_layout(title="Corpus Composition")
    st.plotly_chart(fig_pie)

with c2:
    st.write("### Summary Table")
    summary_data = {
        "Component": ["MF Portfolio", "EPF Account", "Total Corpus", "Planned Expenses", "Net Remaining"],
        "Value (INR)": [
            f"₹{(fv_lumpsum + fv_sip)/1e7:.2f} Cr",
            f"₹{epf_fv/1e5:.2f} L",
            f"₹{total_corpus/1e7:.2f} Cr",
            f"₹{total_expenses/1e5:.2f} L",
            f"₹{net_remaining/1e7:.2f} Cr"
        ]
    }
    st.table(pd.DataFrame(summary_data))
