import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 1. Set Page Config
st.set_page_config(page_title="VPlanner", layout="wide")

# 2. Optimized CSS
hide_st_style = """
            <style>
            footer {visibility: hidden;}
            .main .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("🛡️ Shamna's Retirement Planner")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Timeline")
current_age = st.sidebar.slider("Current Age", 35, 55, 41)
retirement_age = st.sidebar.slider(
    "Retirement Age", 
    50, 70, 55,
    help="Age when you plan to stop working and start drawing down corpus"
)

# Input validation
if retirement_age <= current_age:
    st.error("⚠️ Retirement age must be greater than current age")
    st.stop()

inflation_rate = st.sidebar.slider("Annual Inflation (%)", 4.0, 9.0, 6.0) / 100

st.sidebar.header("2. Wealth & Income Sources")
current_portfolio = st.sidebar.number_input(
    "Current MF Portfolio (₹)", 
    value=3300000,
    help="Your current mutual fund investments"
)

include_epf = st.sidebar.checkbox("Include EPF/PF", value=True)
if include_epf:
    existing_epf = st.sidebar.number_input(
        "Existing EPF Corpus (₹)", 
        value=1050000,
        help="Your current EPF/PF balance"
    )
    monthly_epf = st.sidebar.number_input("Monthly EPF Contribution (₹)", value=6000)
    epf_return = st.sidebar.slider("EPF Return (%)", 6.0, 10.0, 8.1) / 100
else:
    existing_epf = 0
    monthly_epf = 0
    epf_return = 0

other_assets = st.sidebar.number_input(
    "Other Assets - Kannur Home (₹)", 
    value=0,
    help="Real estate and other assets"
)
asset_appreciation = st.sidebar.slider(
    "Asset Appreciation (%)", 
    0.0, 10.0, 5.0,
    help="Annual appreciation rate for other assets"
) / 100

monthly_sip = st.sidebar.number_input("Monthly SIP (₹)", value=100000)

st.sidebar.header("3. Returns")
pre_ret_return = st.sidebar.slider("Pre-Retirement MF Return (%)", 8.0, 16.0, 12.0) / 100
post_ret_return = st.sidebar.slider("Post-Retirement Return (%)", 4.0, 9.0, 7.0) / 100

st.sidebar.header("4. Tax Considerations")
include_ltcg = st.sidebar.checkbox(
    "Include LTCG Tax", 
    value=True,
    help="Account for Long-Term Capital Gains tax on withdrawals"
)

if include_ltcg:
    equity_allocation = st.sidebar.slider(
        "Equity Allocation (%)", 
        0, 100, 70,
        help="Percentage in equity funds (taxed at 12.5% LTCG)"
    ) / 100
    
    debt_allocation = 1 - equity_allocation
    
    # Show tax rates
    st.sidebar.info(f"""
    **Tax Rates:**
    - Equity LTCG: 12.5% (above ₹1.25L/year)
    - Debt LTCG: As per slab rate
    - EPF: Tax-free
    - Property: Exempt if sold after retirement
    """)
    
    debt_tax_slab = st.sidebar.select_slider(
        "Expected Tax Slab in Retirement",
        options=[0, 5, 10, 15, 20, 30],
        value=10,
        help="Your expected income tax slab rate in retirement"
    ) / 100
    
    ltcg_exempt_limit = 125000  # Current limit
else:
    equity_allocation = 1.0
    debt_allocation = 0
    debt_tax_slab = 0
    ltcg_exempt_limit = 0

st.sidebar.header("5. Expenses")
current_monthly_exp = st.sidebar.number_input("Current Monthly Expense (₹)", value=100000)
one_time_exp = st.sidebar.number_input(
    "One-time Outflows (₹)", 
    value=6500000,
    help="Education, marriage, etc. - deducted at retirement"
)

# Comparison mode
st.sidebar.header("6. Compare Scenarios")
compare_mode = st.sidebar.checkbox("Compare Multiple Retirement Ages")
if compare_mode:
    alt_retirement_age = st.sidebar.slider("Alternative Retirement Age", 50, 70, 60)
else:
    alt_retirement_age = None

show_real_terms = st.sidebar.checkbox(
    "Show in Today's Rupees", 
    help="Adjust future values for inflation to show purchasing power"
)

# Warning for high savings rate
if monthly_sip * 12 > current_monthly_exp * 12 * 0.8:
    st.sidebar.warning("⚠️ You're saving a very high percentage of income - is this sustainable?")

# --- CALCULATION FUNCTION ---
def calculate_ltcg_tax(withdrawal_amount, cost_basis, current_value, equity_allocation, 
                       debt_allocation, debt_tax_slab, ltcg_exempt_limit):
    """
    Calculate LTCG tax on withdrawal
    """
    if current_value <= 0:
        return 0
    
    # Calculate gains proportion
    total_gains = max(0, current_value - cost_basis)
    gains_ratio = total_gains / current_value if current_value > 0 else 0
    
    # Gains in this withdrawal
    gains_in_withdrawal = withdrawal_amount * gains_ratio
    
    # Equity portion
    equity_gains = gains_in_withdrawal * equity_allocation
    taxable_equity_gains = max(0, equity_gains - ltcg_exempt_limit)
    equity_tax = taxable_equity_gains * 0.125  # 12.5% LTCG
    
    # Debt portion
    debt_gains = gains_in_withdrawal * debt_allocation
    debt_tax = debt_gains * debt_tax_slab  # Taxed at slab rate
    
    total_tax = equity_tax + debt_tax
    return total_tax

def calculate_retirement_plan(current_age, retirement_age, current_portfolio, monthly_sip, 
                              existing_epf, monthly_epf, epf_return, other_assets, asset_appreciation,
                              pre_ret_return, post_ret_return, inflation_rate, 
                              current_monthly_exp, one_time_exp, show_real_terms=False,
                              include_ltcg=False, equity_allocation=0.7, debt_allocation=0.3,
                              debt_tax_slab=0.1, ltcg_exempt_limit=125000):
    
    years_to_ret = retirement_age - current_age
    months_to_ret = years_to_ret * 12
    monthly_rate_pre = pre_ret_return / 12
    monthly_epf_rate = epf_return / 12
    
    acc_ages = np.arange(current_age, retirement_age + 1)
    lump_vals, sip_vals, epf_vals, asset_vals = [], [], [], []
    
    # Track cost basis for LTCG calculation
    total_invested_mf = current_portfolio
    
    for y in range(len(acc_ages)):
        m = y * 12
        
        # Lumpsum growth
        lump_val = current_portfolio * (1 + pre_ret_return)**y
        
        # SIP accumulation
        if m > 0:
            sip_val = monthly_sip * (((1 + monthly_rate_pre)**m - 1) / monthly_rate_pre) * (1 + monthly_rate_pre)
            total_invested_mf += monthly_sip * 12  # Track annual investment
        else:
            sip_val = 0
        
        # EPF accumulation (existing corpus + new contributions)
        if monthly_epf > 0:
            # Grow existing EPF corpus
            existing_epf_growth = existing_epf * (1 + epf_return)**y
            
            # Add new contributions
            if m > 0:
                new_epf_contributions = monthly_epf * (((1 + monthly_epf_rate)**m - 1) / monthly_epf_rate) * (1 + monthly_epf_rate)
            else:
                new_epf_contributions = 0
            
            epf_val = existing_epf_growth + new_epf_contributions
        else:
            epf_val = 0
        
        # Asset appreciation
        asset_val = other_assets * (1 + asset_appreciation)**y
        
        # Adjust for inflation if showing real terms
        if show_real_terms:
            inflation_factor = (1 + inflation_rate)**y
            lump_val /= inflation_factor
            sip_val /= inflation_factor
            epf_val /= inflation_factor
            asset_val /= inflation_factor
        
        lump_vals.append(lump_val / 1e7)
        sip_vals.append(sip_val / 1e7)
        epf_vals.append(epf_val / 1e7)
        asset_vals.append(asset_val / 1e7)
    
    # MF value at retirement
    mf_value_at_ret = (lump_vals[-1] + sip_vals[-1]) * 1e7
    epf_value_at_ret = epf_vals[-1] * 1e7
    asset_value_at_ret = asset_vals[-1] * 1e7
    
    total_at_ret = mf_value_at_ret + epf_value_at_ret + asset_value_at_ret
    
    # Cost basis for MF (for LTCG calculation)
    mf_cost_basis = total_invested_mf
    
    # One-time expense (assume from assets, not MF)
    corpus_after_one_time = total_at_ret - one_time_exp
    mf_after_one_time = mf_value_at_ret  # MF untouched
    
    # Calculate expenses at retirement
    exp_at_ret_monthly = current_monthly_exp * (1 + inflation_rate)**years_to_ret
    if show_real_terms:
        exp_at_ret_monthly = current_monthly_exp
    
    # Depletion calculation with LTCG tax
    dep_ages, dep_values, dep_tax_paid = [], [], []
    temp_corpus = corpus_after_one_time
    temp_mf_value = mf_after_one_time
    temp_mf_cost_basis = mf_cost_basis
    temp_exp = exp_at_ret_monthly
    age = retirement_age
    monthly_rate_post = post_ret_return / 12
    monthly_inflation = (1 + inflation_rate)**(1/12) - 1
    if show_real_terms:
        monthly_inflation = 0
    
    annual_tax_paid = 0
    cumulative_tax = 0
    
    while temp_corpus > 0 and age < 100:
        annual_withdrawal_needed = 0
        annual_tax = 0
        
        for m in range(12):
            # Grow corpus
            temp_corpus = temp_corpus * (1 + monthly_rate_post)
            temp_mf_value = temp_mf_value * (1 + monthly_rate_post)
            
            # Calculate withdrawal needed (expense + tax)
            if include_ltcg and temp_mf_value > 0:
                # Estimate tax on this month's withdrawal
                monthly_tax = calculate_ltcg_tax(
                    temp_exp, temp_mf_cost_basis, temp_mf_value,
                    equity_allocation, debt_allocation, debt_tax_slab,
                    ltcg_exempt_limit / 12  # Monthly exempt limit
                )
                total_withdrawal = temp_exp + monthly_tax
                annual_tax += monthly_tax
            else:
                total_withdrawal = temp_exp
            
            # Withdraw
            temp_corpus -= total_withdrawal
            temp_mf_value -= total_withdrawal  # Assuming we withdraw proportionally
            annual_withdrawal_needed += total_withdrawal
            
            # Update cost basis proportionally
            if temp_mf_value > 0:
                withdrawal_ratio = total_withdrawal / (temp_mf_value + total_withdrawal)
                temp_mf_cost_basis = temp_mf_cost_basis * (1 - withdrawal_ratio)
            
            # Inflate expense
            temp_exp = temp_exp * (1 + monthly_inflation)
            
            if temp_corpus <= 0: 
                break
        
        age += 1
        dep_ages.append(age)
        dep_values.append(max(0, temp_corpus / 1e7))
        cumulative_tax += annual_tax
        dep_tax_paid.append(cumulative_tax / 1e5)  # In lakhs
        
        if temp_corpus <= 0:
            break
    
    return {
        'acc_ages': acc_ages,
        'lump_vals': lump_vals,
        'sip_vals': sip_vals,
        'epf_vals': epf_vals,
        'asset_vals': asset_vals,
        'dep_ages': dep_ages,
        'dep_values': dep_values,
        'dep_tax_paid': dep_tax_paid,
        'total_at_ret': total_at_ret,
        'corpus_after_one_time': corpus_after_one_time,
        'exp_at_ret_monthly': exp_at_ret_monthly,
        'survival_age': age if temp_corpus <= 0 else 100,
        'total_invested': total_invested_mf + existing_epf + (monthly_epf * months_to_ret if monthly_epf > 0 else 0),
        'cumulative_ltcg_tax': cumulative_tax,
        'mf_cost_basis': mf_cost_basis,
        'mf_value_at_ret': mf_value_at_ret
    }

# --- MAIN CALCULATIONS ---
result = calculate_retirement_plan(
    current_age, retirement_age, current_portfolio, monthly_sip,
    existing_epf, monthly_epf, epf_return, other_assets, asset_appreciation,
    pre_ret_return, post_ret_return, inflation_rate,
    current_monthly_exp, one_time_exp, show_real_terms,
    include_ltcg, equity_allocation, debt_allocation,
    debt_tax_slab, ltcg_exempt_limit
)

# --- METRICS DISPLAY ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Net Worth at Retirement", 
        f"₹{result['total_at_ret']/1e7:.2f} Cr",
        help="Total accumulated wealth at retirement age"
    )

with col2:
    after_tax_label = "After Expenses"
    if include_ltcg:
        after_tax_label += " (Pre-tax)"
    st.metric(
        after_tax_label, 
        f"₹{result['corpus_after_one_time']/1e7:.2f} Cr",
        help="Corpus available for retirement after major expenses"
    )

with col3:
    survival_age = result['survival_age']
    survival_color = "green" if survival_age >= 85 else "orange" if survival_age >= 75 else "red"
    label_suffix = " (with tax)" if include_ltcg else ""
    st.metric(f"Corpus Lasts Till{label_suffix}", f"{survival_age if survival_age < 100 else '100+'}")

with col4:
    returns = result['total_at_ret'] - result['total_invested']
    roi_multiple = result['total_at_ret'] / result['total_invested'] if result['total_invested'] > 0 else 0
    st.metric(
        "Total Returns", 
        f"₹{returns/1e7:.2f} Cr",
        delta=f"{roi_multiple:.1f}x invested",
        help="Net returns on your investments"
    )

# LTCG Impact Alert
if include_ltcg and result['cumulative_ltcg_tax'] > 0:
    st.warning(f"""
    ⚠️ **LTCG Tax Impact**: You'll pay approximately **₹{result['cumulative_ltcg_tax']/1e5:.2f} lakhs** 
    in capital gains tax over your retirement. This reduces your effective corpus by 
    **{(result['cumulative_ltcg_tax']/result['corpus_after_one_time'])*100:.1f}%**.
    """)

# --- MAIN CHART ---
fig = go.Figure()

# Stacked area chart
fig.add_trace(go.Scatter(
    x=result['acc_ages'], 
    y=result['asset_vals'], 
    stackgroup='one', 
    name='Other Assets',
    line=dict(width=0),
    fillcolor='rgba(255, 193, 7, 0.6)'
))

if include_epf and monthly_epf > 0:
    fig.add_trace(go.Scatter(
        x=result['acc_ages'], 
        y=result['epf_vals'], 
        stackgroup='one', 
        name='EPF (Tax-free)',
        line=dict(width=0),
        fillcolor='rgba(156, 39, 176, 0.6)'
    ))

fig.add_trace(go.Scatter(
    x=result['acc_ages'], 
    y=result['lump_vals'], 
    stackgroup='one', 
    name='MF Growth',
    line=dict(width=0),
    fillcolor='rgba(33, 150, 243, 0.6)'
))

fig.add_trace(go.Scatter(
    x=result['acc_ages'], 
    y=result['sip_vals'], 
    stackgroup='one', 
    name='SIP Accumulation',
    line=dict(width=0),
    fillcolor='rgba(76, 175, 80, 0.6)'
))

drawdown_label = 'Post-Retirement Drawdown'
if include_ltcg:
    drawdown_label += ' (After Tax)'

fig.add_trace(go.Scatter(
    x=result['dep_ages'], 
    y=result['dep_values'], 
    name=drawdown_label,
    line=dict(color='red', width=3),
    mode='lines'
))

# Retirement line
fig.add_vline(x=retirement_age, line_dash="dash", line_color="gray", annotation_text="Retirement")

fig.update_layout(
    height=500,
    margin=dict(l=10, r=10, t=40, b=80),
    legend=dict(
        orientation="h", 
        yanchor="top", 
        y=-0.15,
        xanchor="center", 
        x=0.5,
        font=dict(size=10)
    ),
    xaxis_title="Age",
    yaxis_title="Crores (INR)" + (" - Today's Value" if show_real_terms else ""),
    hovermode="x unified",
    plot_bgcolor='rgba(240, 240, 240, 0.5)'
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- LTCG BREAKDOWN ---
if include_ltcg and result['cumulative_ltcg_tax'] > 0:
    with st.expander("💰 LTCG Tax Breakdown"):
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.write("**At Retirement:**")
            st.write(f"MF Value: ₹{result['mf_value_at_ret']/1e7:.2f} Cr")
            st.write(f"Cost Basis: ₹{result['mf_cost_basis']/1e7:.2f} Cr")
            gains = result['mf_value_at_ret'] - result['mf_cost_basis']
            st.write(f"Unrealized Gains: ₹{gains/1e7:.2f} Cr ({gains/result['mf_value_at_ret']*100:.1f}%)")
        
        with col_b:
            st.write("**Over Retirement:**")
            st.write(f"Total LTCG Tax: ₹{result['cumulative_ltcg_tax']/1e5:.2f} L")
            avg_annual_tax = result['cumulative_ltcg_tax'] / (result['survival_age'] - retirement_age) if result['survival_age'] > retirement_age else 0
            st.write(f"Avg Annual Tax: ₹{avg_annual_tax/1000:.2f}K")
            st.write(f"Equity portion taxed at: 12.5%")
            st.write(f"Debt portion taxed at: {debt_tax_slab*100:.0f}%")

# --- COMPARISON MODE ---
if compare_mode and alt_retirement_age and alt_retirement_age != retirement_age:
    st.subheader("📊 Scenario Comparison")
    
    alt_result = calculate_retirement_plan(
        current_age, alt_retirement_age, current_portfolio, monthly_sip,
        existing_epf, monthly_epf, epf_return, other_assets, asset_appreciation,
        pre_ret_return, post_ret_return, inflation_rate,
        current_monthly_exp, one_time_exp, show_real_terms,
        include_ltcg, equity_allocation, debt_allocation,
        debt_tax_slab, ltcg_exempt_limit
    )
    
    comp_col1, comp_col2, comp_col3 = st.columns(3)
    
    with comp_col1:
        st.markdown("### Metric")
        st.write("**Years to Retirement**")
        st.write("**Corpus at Retirement**")
        st.write("**After Expenses**")
        if include_ltcg:
            st.write("**LTCG Tax Paid**")
        st.write("**Lasts Till Age**")
        st.write("**Monthly Expense**")
    
    with comp_col2:
        st.markdown(f"### Retire at {retirement_age}")
        st.write(f"{retirement_age - current_age} years")
        st.write(f"₹{result['total_at_ret']/1e7:.2f} Cr")
        st.write(f"₹{result['corpus_after_one_time']/1e7:.2f} Cr")
        if include_ltcg:
            st.write(f"₹{result['cumulative_ltcg_tax']/1e5:.2f} L")
        st.write(f"{result['survival_age']}" + ("+" if result['survival_age'] >= 100 else ""))
        st.write(f"₹{result['exp_at_ret_monthly']/1000:.1f}K")
    
    with comp_col3:
        st.markdown(f"### Retire at {alt_retirement_age}")
        st.write(f"{alt_retirement_age - current_age} years")
        st.write(f"₹{alt_result['total_at_ret']/1e7:.2f} Cr")
        st.write(f"₹{alt_result['corpus_after_one_time']/1e7:.2f} Cr")
        if include_ltcg:
            st.write(f"₹{alt_result['cumulative_ltcg_tax']/1e5:.2f} L")
        st.write(f"{alt_result['survival_age']}" + ("+" if alt_result['survival_age'] >= 100 else ""))
        st.write(f"₹{alt_result['exp_at_ret_monthly']/1000:.1f}K")
    
    # Difference highlight
    diff_corpus = alt_result['total_at_ret'] - result['total_at_ret']
    diff_years = alt_retirement_age - retirement_age
    diff_tax = alt_result['cumulative_ltcg_tax'] - result['cumulative_ltcg_tax']
    
    info_text = f"💡 Working {abs(diff_years)} {'more' if diff_years > 0 else 'fewer'} years " + \
                f"{'adds' if diff_corpus > 0 else 'reduces'} ₹{abs(diff_corpus)/1e7:.2f} Cr to your retirement corpus"
    
    if include_ltcg:
        info_text += f", but also increases LTCG tax by ₹{abs(diff_tax)/1e5:.2f} L"
    
    st.info(info_text)

# --- KEY INSIGHTS ---
st.subheader("📈 Key Insights")

col_a, col_b = st.columns(2)

with col_a:
    st.write(f"**Monthly Expense at Retirement:** ₹{result['exp_at_ret_monthly']/1000:.1f}K")
    if include_ltcg:
        first_year_tax = calculate_ltcg_tax(
            result['exp_at_ret_monthly'] * 12,
            result['mf_cost_basis'],
            result['mf_value_at_ret'],
            equity_allocation, debt_allocation, debt_tax_slab, ltcg_exempt_limit
        )
        st.write(f"**First Year LTCG Tax:** ₹{first_year_tax/1000:.2f}K")
        st.write(f"**Effective Monthly Need:** ₹{(result['exp_at_ret_monthly'] + first_year_tax/12)/1000:.1f}K")
    st.write(f"**Total SIP Investment:** ₹{(monthly_sip * (retirement_age - current_age) * 12)/1e7:.2f} Cr")
    if include_epf and monthly_epf > 0:
        st.write(f"**Existing EPF:** ₹{existing_epf/1e5:.2f} L")
        st.write(f"**New EPF Contributions:** ₹{(monthly_epf * (retirement_age - current_age) * 12)/1e5:.2f} L")

with col_b:
    wealth_multiple = result['total_at_ret'] / current_portfolio if current_portfolio > 0 else 0
    st.write(f"**Wealth Multiplication:** {wealth_multiple:.1f}x")
    safe_withdrawal_rate = (result['exp_at_ret_monthly'] * 12) / result['corpus_after_one_time'] * 100 if result['corpus_after_one_time'] > 0 else 0
    st.write(f"**Initial Withdrawal Rate:** {safe_withdrawal_rate:.1f}%")
    st.write(f"**Years in Retirement:** {result['survival_age'] - retirement_age if result['survival_age'] < 100 else '40+'}")
    if include_ltcg:
        effective_corpus = result['corpus_after_one_time'] - result['cumulative_ltcg_tax']
        st.write(f"**Post-Tax Effective Corpus:** ₹{effective_corpus/1e7:.2f} Cr")

# --- DETAILED TABLE ---
with st.expander("📊 View Detailed Year-by-Year Breakdown"):
    detail_df = pd.DataFrame({
        'Age': result['acc_ages'],
        'MF Growth (Cr)': [f"₹{v:.2f}" for v in result['lump_vals']],
        'SIP Value (Cr)': [f"₹{v:.2f}" for v in result['sip_vals']],
        'EPF Value (Cr)': [f"₹{v:.2f}" for v in result['epf_vals']] if include_epf else ['₹0.00'] * len(result['acc_ages']),
        'Assets (Cr)': [f"₹{v:.2f}" for v in result['asset_vals']],
        'Total Wealth (Cr)': [f"₹{(a+b+c+d):.2f}" for a,b,c,d in zip(
            result['lump_vals'], result['sip_vals'], result['epf_vals'], result['asset_vals']
        )]
    })
    st.dataframe(detail_df, use_container_width=True, height=400)

# --- DOWNLOAD OPTION ---
st.subheader("💾 Export Data")

if st.button("📥 Download Retirement Plan Summary"):
    # Prepare summary data
    summary_data = {
        'Parameter': [
            'Current Age', 'Retirement Age', 'Current Portfolio', 'Monthly SIP',
            'Existing EPF', 'Monthly EPF', 'Other Assets', 'Pre-Retirement Return', 'Post-Retirement Return',
            'Inflation Rate', 'Current Monthly Expense', 'One-time Expense',
            'LTCG Included', 'Equity Allocation', 'Debt Tax Slab',
            'Net Worth at Retirement', 'Corpus After Expenses', 'Total LTCG Tax', 'Survival Age'
        ],
        'Value': [
            current_age, retirement_age, f"₹{current_portfolio/1e5:.2f}L", f"₹{monthly_sip/1000:.0f}K",
            f"₹{existing_epf/1e5:.2f}L" if include_epf else 'N/A',
            f"₹{monthly_epf}" if include_epf else 'N/A', f"₹{other_assets/1e5:.2f}L",
            f"{pre_ret_return*100:.1f}%", f"{post_ret_return*100:.1f}%",
            f"{inflation_rate*100:.1f}%", f"₹{current_monthly_exp/1000:.0f}K", f"₹{one_time_exp/1e5:.2f}L",
            'Yes' if include_ltcg else 'No',
            f"{equity_allocation*100:.0f}%" if include_ltcg else 'N/A',
            f"{debt_tax_slab*100:.0f}%" if include_ltcg else 'N/A',
            f"₹{result['total_at_ret']/1e7:.2f}Cr", f"₹{result['corpus_after_one_time']/1e7:.2f}Cr",
            f"₹{result['cumulative_ltcg_tax']/1e5:.2f}L" if include_ltcg else '₹0',
            f"{result['survival_age']}"
        ]
    }
    
    summary_df = pd.DataFrame(summary_data)
    csv = summary_df.to_csv(index=False)
    st.download_button(
        label="Download Summary CSV",
        data=csv,
        file_name="retirement_plan_summary.csv",
        mime="text/csv"
    )

# --- FOOTER ---
 
