import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Set Page Config
st.set_page_config(page_title="Retirement Sustainability Planner", layout="wide")

st.title("💸 Life-Cycle Financial Planner")
st.markdown("This app projects your wealth growth and then simulates how long it lasts based on your lifestyle.")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Timeline & Inflation")
current_age = st.sidebar.slider("Current Age", 30, 55, 41)
retirement_age = st.sidebar.slider("Retirement Age", 45, 70, 60)
inflation_rate = st.sidebar.slider("Annual Inflation (%)", 4.0, 10.0, 6.0) / 100

st.sidebar.header("2. Income & Growth")
current_portfolio = st.sidebar.number_input("Current MF Portfolio (₹)", value=3300000)
monthly_sip = st.sidebar.number_input("Monthly SIP (₹)", value=100000)
pre_ret_return = st.sidebar.slider("Pre-Retirement Return (%)", 8.0, 18.0, 12.0) / 100
post_ret_return = st.sidebar.slider("Post-Retirement (Safe) Return (%)", 4.0, 9.0, 7.0) / 100

st.sidebar.header("3. Expenses")
current_monthly_exp = st.sidebar.number_input("Current Monthly Expenses (₹)", value=100000)
one_time_exp = st.sidebar.number_input("Total One-time Major Expenses (Education, etc.) (₹)", value=6480000)

# --- CALCULATIONS ---

# Timeframes
years_to_ret = retirement_age - current_age
months_to_ret = years_to_ret * 12

# Phase 1: Accumulation
# MF Growth
fv_lumpsum = current_portfolio * (1 + pre_ret_return)**years_to_ret
monthly_rate_pre = pre_ret_return / 12
if months_to_ret > 0:
    fv_sip = monthly_sip * (((1 + monthly_rate_pre)**months_to_ret - 1) / monthly_rate_pre) * (1 + monthly_rate_pre)
else:
    fv_sip = 0

# EPF Growth (Approximate)
epf_monthly = 6000
epf_rate = 0.081
epf_fv = epf_monthly * 12 * ((1 + epf_rate)**years_to_ret - 1) / epf_rate

total_corpus_at_ret = fv_lumpsum + fv_sip + epf_fv - one_time_exp

# Phase 2: Withdrawal Simulation
# Inflated expense at age of retirement
exp_at_ret_monthly = current_monthly_exp * (1 + inflation_rate)**years_to_ret

# Simulation
ages = [current_age]
corpus_history = [current_portfolio / 1e7]
current_corpus = total_corpus_at_ret
monthly_rate_post = post_ret_return / 12
monthly_inflation = (1 + inflation_rate)**(1/12) - 1

# Data for Charting
acc_ages = np.arange(current_age, retirement_age + 1)
acc_values = []
for y in range(len(acc_ages)):
    m = y * 12
    lump = current_portfolio * (1 + pre_ret_return)**y
    sip = monthly_sip * (((1 + monthly_rate_pre)**m - 1) / monthly_rate_pre) * (1 + monthly_rate_pre) if m > 0 else 0
    acc_values.append((lump + sip) / 1e7)

# Depletion Simulation
dep_ages = []
dep_values = []
temp_corpus = total_corpus_at_ret
temp_exp = exp_at_ret_monthly
age = retirement_age

while temp_corpus > 0 and age < 100:
    for m in range(12):
        temp_corpus = (temp_corpus * (1 + monthly_rate_post)) - temp_exp
        temp_exp = temp_exp * (1 + monthly_inflation)
        if temp_corpus <= 0:
            break
    age += 1
    dep_ages.append(age)
    dep_values.append(max(0, temp_corpus / 1e7))

# --- DASHBOARD ---
c1, c2, c3 = st.columns(3)
c1.metric("Corpus at Retirement", f"₹{total_corpus_at_ret/1e7:.2f} Cr")
c2.metric("Monthly Exp at Retirement", f"₹{exp_at_ret_monthly/1e3:.1f} K")
c3.metric("Money Lasts Until Age", f"{age if temp_corpus <= 0 else '>100'}")

# --- THE BIG CHART ---
fig = go.Figure()

# Accumulation Trace
fig.add_trace(go.Scatter(x=acc_ages, y=acc_values, fill='tozeroy', name='Accumulation Phase', line=dict(color='#00CC96')))
# Depletion Trace
fig.add_trace(go.Scatter(x=dep_ages, y=dep_values, fill='tozeroy', name='Withdrawal Phase', line=dict(color='#EF553B')))

fig.add_vline(x=retirement_age, line_dash="dash", line_color="gray", annotation_text="Retirement")
fig.update_layout(title="The Full Lifecycle: Wealth vs. Age", xaxis_title="Age", yaxis_title="Crores (INR)", hovermode="x")
st.plotly_chart(fig, use_container_width=True)

st.info(f"💡 **Observation:** Your current expenses of ₹{current_monthly_exp/1e3:.0f}K will feel like ₹{exp_at_ret_monthly/1e3:.0f}K in {years_to_ret} years due to inflation. This app ensures your withdrawals grow every year to maintain your lifestyle.")
