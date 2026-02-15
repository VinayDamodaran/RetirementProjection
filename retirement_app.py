import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. Set Page Config (Centered layout often works better for mobile reading)
st.set_page_config(page_title="VPlanner", layout="wide")

# 2. Optimized CSS: Remove footer but KEEP the header (so sidebar works on mobile)
hide_st_style = """
            <style>
            footer {visibility: hidden;}
            /* This ensures the chart doesn't have too much padding on small screens */
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("🛡️Shamna's Retirement Planner")

# --- SIDEBAR INPUTS ---
# No changes here, Streamlit will automatically hide this behind a menu on mobile
st.sidebar.header("1. Timeline")
current_age = st.sidebar.slider("Current Age", 35, 55, 41)
retirement_age = st.sidebar.slider("Retirement Age", 50, 70, 55)
inflation_rate = st.sidebar.slider("Annual Inflation (%)", 4.0, 9.0, 6.0) / 100

st.sidebar.header("2. Wealth & Returns")
current_portfolio = st.sidebar.number_input("Current MF Portfolio (₹)", value=3300000)
other_assets = st.sidebar.number_input("Other Assets-Kannur home (₹)", value=2000000)
monthly_sip = st.sidebar.number_input("Monthly SIP (₹)", value=100000)
pre_ret_return = st.sidebar.slider("MF Return (%)", 8.0, 16.0, 12.0) / 100
post_ret_return = st.sidebar.slider("Post-Retire Return (%)", 4.0, 9.0, 7.0) / 100

st.sidebar.header("3. Expenses")
current_monthly_exp = st.sidebar.number_input("Monthly Expense (₹)", value=100000)
one_time_exp = st.sidebar.number_input("One-time Outflows (₹)-Education,Misc", value=6500000)

# --- CALCULATIONS (Same as before) ---
years_to_ret = retirement_age - current_age
months_to_ret = years_to_ret * 12
monthly_rate_pre = pre_ret_return / 12

acc_ages = np.arange(current_age, retirement_age + 1)
lump_vals, sip_vals, epf_vals, asset_vals = [], [], [], []

for y in range(len(acc_ages)):
    m = y * 12
    lump_vals.append((current_portfolio * (1 + pre_ret_return)**y) / 1e7)
    sip = monthly_sip * (((1 + monthly_rate_pre)**m - 1) / monthly_rate_pre) * (1 + monthly_rate_pre) if m > 0 else 0
    sip_vals.append(sip / 1e7)
    epf = (6000 * 12 * ((1 + 0.081)**y - 1) / 0.081) if y > 0 else 0
    epf_vals.append(epf / 1e7)
    asset_vals.append(other_assets / 1e7)

total_at_ret = (lump_vals[-1] + sip_vals[-1] + epf_vals[-1] + asset_vals[-1]) * 1e7
corpus_after_one_time = total_at_ret - one_time_exp

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

# --- MOBILE OPTIMIZED UI ---

# Using st.columns for desktop; Streamlit automatically stacks these on mobile
c1, c2 = st.columns(2)
with c1:
    st.metric("Net Worth at Retirement", f"₹{total_at_ret/1e7:.2f} Cr")
with c2:
    st.metric("Survival Age", f"{age if temp_corpus <= 0 else '100+'}")

# --- CHART OPTIMIZATION ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=acc_ages, y=asset_vals, stackgroup='one', name='Assets', line=dict(width=0)))
fig.add_trace(go.Scatter(x=acc_ages, y=epf_vals, stackgroup='one', name='EPF', line=dict(width=0)))
fig.add_trace(go.Scatter(x=acc_ages, y=lump_vals, stackgroup='one', name='MF Growth', line=dict(width=0)))
fig.add_trace(go.Scatter(x=acc_ages, y=sip_vals, stackgroup='one', name='SIPs', line=dict(width=0)))
fig.add_trace(go.Scatter(x=dep_ages, y=dep_values, name='Drawdown', line=dict(color='red', width=3)))

fig.add_vline(x=retirement_age, line_dash="dash", line_color="gray")

# Key for Mobile: Put legend at the bottom and make chart height appropriate
fig.update_layout(
    height=500,
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
    xaxis_title="Age",
    yaxis_title="Crores (INR)",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

st.write(f"**Monthly Exp at {retirement_age}:** ₹{exp_at_ret_monthly/1e3:.1f}K")
