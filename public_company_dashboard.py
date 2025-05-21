import yfinance as yf
import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Public Company Dashboard", layout="wide")

st.title("📊 Public Company Financial Dashboard")

st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    section.main > div { overflow-x: auto; }
</style>
""", unsafe_allow_html=True)

ticker_input = st.text_input("Enter Ticker Symbol (e.g., AAPL, MSFT):", value="AAPL")

if ticker_input:
    ticker = yf.Ticker(ticker_input)
    info = ticker.info

    # Price Data
    hist = ticker.history(period="5y")
    hist.index = hist.index.tz_localize(None)
    last_price_date = hist.index.max().date()
    last_price = hist['Close'].iloc[-1]

    # Dropdown chart selector
    st.subheader("📈 Historical Trend Chart")
    chart_option = st.selectbox("Choose metric to plot:", ["Share Price", "P/E (LTM)", "EV / EBITDA (LTM)", "EV / Revenue (LTM)"])
    chart_data = hist[['Close']].copy()
    chart_data.rename(columns={'Close': 'Share Price'}, inplace=True)
    st.line_chart(chart_data[chart_option] if chart_option in chart_data.columns else chart_data['Share Price'])

    # Financials
    fin = ticker.financials.T
    qfin = ticker.quarterly_financials.T
    fin.index = pd.to_datetime(fin.index)
    fin = fin.sort_index()
    ltm_date = fin.index.max()

    # Key Market Data & Valuation
    st.subheader("📌 Key Financial Snapshot")
    try:
        shares_out = info.get('sharesOutstanding', 0)
        market_cap = shares_out * last_price if shares_out else info.get('marketCap', 0)
        total_debt = info.get('totalDebt', 0)
        cash = info.get('totalCash', 0)
        enterprise_value = market_cap + total_debt - cash

        # LTM figures
        revenue = fin.get("Total Revenue", pd.Series([None])).dropna().iloc[-1]
        ebitda = fin.get("EBITDA", pd.Series([None])).dropna().iloc[-1]
        net_income = fin.get("Net Income", pd.Series([None])).dropna().iloc[-1]

        # NTM estimates
        forward_pe = info.get("forwardPE")
        forward_eps = info.get("forwardEps")
        est_net_income = forward_eps * shares_out if forward_eps and shares_out else None

        pe = market_cap / net_income if net_income else None
        ev_ebitda = enterprise_value / ebitda if ebitda else None
        ev_sales = enterprise_value / revenue if revenue else None

        st.markdown(f"**As of {last_price_date}**")
        st.metric("Share Price", f"${last_price:,.2f}")
        st.metric("Shares Outstanding", f"{shares_out:,.0f}")
        st.metric("Market Cap", f"${market_cap:,.0f}")
        st.metric("Cash (as of {ltm_date.date()})", f"${cash:,.0f}")
        st.metric("Total Debt (as of {ltm_date.date()})", f"${total_debt:,.0f}")
        st.metric("Enterprise Value", f"${enterprise_value:,.0f}")

        st.markdown("### 📊 Valuation Multiples")
        st.metric("P/E (LTM)", f"{round(pe, 2)}" if pe else "N/A")
        st.metric("EV / EBITDA (LTM)", f"{round(ev_ebitda, 2)}" if ev_ebitda else "N/A")
        st.metric("EV / Revenue (LTM)", f"{round(ev_sales, 2)}" if ev_sales else "N/A")
        st.metric("P/E (NTM)", f"{round(forward_pe, 2)}" if forward_pe else "N/A")

    except Exception as e:
        st.warning(f"Some key data is missing or caused an error: {e}")

    # Income Statement
    st.subheader("📄 Income Statement (5 Years + LTM + NTM)")
    try:
        rows = [
            "Revenue", "YoY Revenue Growth", "Gross Profit", "Gross Margin",
            "Operating Expenses", "EBITDA", "EBITDA Margin", "EBIT", "EBIT Margin",
            "Net Income", "Net Income Margin", "Capital Expenditures", "Operating Cash Flow"
        ]

        income_map = {
            "Revenue": "Total Revenue",
            "Gross Profit": "Gross Profit",
            "Operating Expenses": "Operating Expenses",
            "EBITDA": "EBITDA",
            "EBIT": "Ebit",
            "Net Income": "Net Income",
            "Capital Expenditures": "Capital Expenditures",
            "Operating Cash Flow": "Operating Cash Flow"
        }

        df = pd.DataFrame()
        for label, raw in income_map.items():
            if raw in fin.columns:
                temp = fin[raw].copy()
                temp.index = temp.index.year
                grouped = temp.groupby(level=0).first()
                df[label] = grouped

        df = df.T
        df.columns = df.columns.astype(str)

        if "Revenue" in df.index:
            df.loc["YoY Revenue Growth"] = df.loc["Revenue"].pct_change().apply(lambda x: f"{x:.0%}" if pd.notnull(x) else "")
        if "Gross Profit" in df.index and "Revenue" in df.index:
            df.loc["Gross Margin"] = (df.loc["Gross Profit"] / df.loc["Revenue"]).apply(lambda x: f"{x:.0%}" if pd.notnull(x) else "")
        if "EBITDA" in df.index and "Revenue" in df.index:
            df.loc["EBITDA Margin"] = (df.loc["EBITDA"] / df.loc["Revenue"]).apply(lambda x: f"{x:.0%}" if pd.notnull(x) else "")
        if "EBIT" in df.index and "Revenue" in df.index:
            df.loc["EBIT Margin"] = (df.loc["EBIT"] / df.loc["Revenue"]).apply(lambda x: f"{x:.0%}" if pd.notnull(x) else "")
        if "Net Income" in df.index and "Revenue" in df.index:
            df.loc["Net Income Margin"] = (df.loc["Net Income"] / df.loc["Revenue"]).apply(lambda x: f"{x:.0%}" if pd.notnull(x) else "")

        for row in df.index:
            if "Margin" not in row and "Growth" not in row:
                df.loc[row] = df.loc[row].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "")

        df = df.reindex(rows)
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.warning(f"Could not generate income statement: {e}")
