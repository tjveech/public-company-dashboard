import yfinance as yf
import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Public Company Dashboard", layout="wide")

st.title("📊 Public Company Financial Dashboard")

st.markdown("""
<style>
    html, body, [class*="css"]  {
        font-size: 13px !important;
        line-height: 1.2;
    }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    section.main > div { overflow-x: auto; }
    div[data-testid="metric-container"] {
        padding: 0.25rem !important;
        font-size: 13px !important;
    }
</style>
""", unsafe_allow_html=True)

ticker_input = st.text_input("Enter Ticker Symbol (e.g., AAPL, MSFT):", value="AAPL")

if ticker_input:
    ticker = yf.Ticker(ticker_input)
    info = ticker.info

    # Data range selector
    date_range = st.selectbox("Select historical data range:", ["1y", "5y", "10y", "max"], index=1)

    # Annual or Quarterly toggle
    view = st.radio("Data View:", ["Annual", "Quarterly"], horizontal=True)

    # Price Data
    hist = ticker.history(period=date_range)
    hist.index = hist.index.tz_localize(None)
    last_price_date = hist.index.max().date()
    last_price = hist['Close'].iloc[-1]

    st.subheader("📈 Stock Price History")
    st.line_chart(hist['Close'])

    # Financials
    raw_fin = ticker.financials.T
    raw_qfin = ticker.quarterly_financials.T
    raw_bs = ticker.balance_sheet.T
    raw_cf = ticker.cashflow.T
    fin = raw_fin if view == "Annual" else raw_qfin
    fin.index = pd.to_datetime(fin.index)
    fin = fin.sort_index()
    ltm_df = raw_qfin.copy()
    ltm_df.index = pd.to_datetime(ltm_df.index)
    ltm = ltm_df.sort_index().iloc[-4:].sum()

    # Capitalization Section
    st.subheader("💼 Capitalization")
    try:
        shares_out = info.get('sharesOutstanding', 0)
        market_cap = shares_out * last_price if shares_out else info.get('marketCap', 0)
        total_debt = info.get('totalDebt', 0)
        cash = info.get('totalCash', 0)
        enterprise_value = market_cap + total_debt - cash

        revenue = fin.get("Total Revenue", pd.Series([None])).dropna().iloc[-1] if "Total Revenue" in fin.columns else None
        ebitda = fin.get("EBITDA", pd.Series([None])).dropna().iloc[-1] if "EBITDA" in fin.columns else None
        net_income = fin.get("Net Income", pd.Series([None])).dropna().iloc[-1] if "Net Income" in fin.columns else None

        forward_pe = info.get("forwardPE")
        forward_eps = info.get("forwardEps")
        est_net_income = forward_eps * shares_out if forward_eps and shares_out else None

        pe = market_cap / net_income if net_income else None
        ev_ebitda = enterprise_value / ebitda if ebitda else None
        ev_sales = enterprise_value / revenue if revenue else None

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Share Price (as of {last_price_date})**: ${last_price:,.2f} [🔗](https://finance.yahoo.com/quote/{ticker_input})")
            st.markdown(f"**Shares Outstanding (as of {last_price_date})**: {shares_out:,.0f} [🔗](https://finance.yahoo.com/quote/{ticker_input}/key-statistics)")
            st.markdown(f"**Market Cap (as of {last_price_date})**: ${market_cap:,.0f} [🔗](https://finance.yahoo.com/quote/{ticker_input}/key-statistics)")
        with col2:
            st.markdown(f"**Cash (as of {fin.index.max().date()})**: ${cash:,.0f} [🔗](https://finance.yahoo.com/quote/{ticker_input}/balance-sheet)")
            st.markdown(f"**Total Debt (as of {fin.index.max().date()})**: ${total_debt:,.0f} [🔗](https://finance.yahoo.com/quote/{ticker_input}/balance-sheet)")
            st.markdown(f"**Enterprise Value (as of {last_price_date})**: ${enterprise_value:,.0f} [🔗](https://finance.yahoo.com/quote/{ticker_input}/key-statistics)")


        st.markdown("### 📊 Valuation Multiples")
        col3, col4 = st.columns(2)
        with col3:
            st.markdown(f"P/E (LTM): {'{:.2f}'.format(pe) if pe else 'N/A'} [🔗](https://finance.yahoo.com/quote/{ticker_input}/key-statistics)")
            st.markdown(f"EV / EBITDA (LTM): {'{:.2f}'.format(ev_ebitda) if ev_ebitda else 'N/A'} [🔗](https://finance.yahoo.com/quote/{ticker_input}/key-statistics)")
        with col4:
            st.markdown(f"P/E (NTM): {'{:.2f}'.format(forward_pe) if forward_pe else 'N/A'} [🔗](https://finance.yahoo.com/quote/{ticker_input}/key-statistics)")
            st.markdown(f"EV / Revenue (LTM): {'{:.2f}'.format(ev_sales) if ev_sales else 'N/A'} [🔗](https://finance.yahoo.com/quote/{ticker_input}/key-statistics)")

    except Exception as e:
        st.warning(f"Some key data is missing or caused an error: {e}")

    st.subheader("📄 Financial Overview")
    try:
        rows = [
            "Revenue", "YoY Revenue Growth", "Gross Profit", "Gross Margin",
            "EBITDA", "EBITDA Margin",
            "Net Income", "Net Income Margin", "Capital Expenditures", "Operating Cash Flow", "LTM Revenue", "LTM EBITDA"
        ]

        income_map = {
            "Revenue": "Total Revenue",
            "Gross Profit": "Gross Profit",
            "Operating Expenses": "Operating Expenses",
            "EBITDA": "EBITDA",
            "Net Income": "Net Income",
            "Capital Expenditures": "Capital Expenditures",
            "Operating Cash Flow": "Operating Cash Flow"
        }

        df = pd.DataFrame()
        for label, raw in income_map.items():
            source_df = raw_cf if raw in raw_cf.columns else fin
            if raw in source_df.columns:
                temp = source_df[raw].copy()
                temp.index = pd.to_datetime(temp.index).year
                grouped = temp.groupby(level=0).first()
                df[label] = pd.to_numeric(grouped, errors='coerce')

        df = df.T
        df.columns = df.columns.astype(str)
        df.loc["LTM Revenue"] = ltm.get("Total Revenue", float("nan"))
        df.loc["LTM EBITDA"] = ltm.get("EBITDA", float("nan"))

        if "Revenue" in df.index:
            df.loc["YoY Revenue Growth"] = df.loc["Revenue"].pct_change().apply(lambda x: f"{x:.0%}" if pd.notnull(x) else "")
        if "Gross Profit" in df.index and "Revenue" in df.index:
            df.loc["Gross Margin"] = (df.loc["Gross Profit"] / df.loc["Revenue"]).apply(lambda x: f"{x:.0%}" if pd.notnull(x) else "")
        if "EBITDA" in df.index and "Revenue" in df.index:
            df.loc["EBITDA Margin"] = (df.loc["EBITDA"] / df.loc["Revenue"]).apply(lambda x: f"{x:.0%}" if pd.notnull(x) else "")
        if "Net Income" in df.index and "Revenue" in df.index:
            df.loc["Net Income Margin"] = (df.loc["Net Income"] / df.loc["Revenue"]).apply(lambda x: f"{x:.0%}" if pd.notnull(x) else "")

        for row in df.index:
            if "Margin" not in row and "Growth" not in row:
                df.loc[row] = df.loc[row].apply(lambda x: f"${x:,.0f}" if pd.notnull(x) else "")

        df = df.reindex(rows)
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.warning(f"Could not generate financial overview: {e}")

    with st.expander("📂 Detailed Financial Statements (Past 5 Years)", expanded=False):
        try:
            for title, data in zip(["Income Statement", "Cash Flow Statement", "Balance Sheet"], [raw_fin, raw_cf, raw_bs]):
                data = data.copy()
            data.index = pd.to_datetime(data.index).year
            grouped = data.groupby(level=0).first().T.fillna(0)
            grouped = grouped.iloc[:, :5]  # Show most recent 5 years
            st.markdown(f"#### {title}")
            st.dataframe(grouped.style.format("${:,.0f}"), use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load detailed statements: {e}")

    st.subheader("📤 Export to Excel")
    def to_excel():
        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for title, data in zip(["Income Statement", "Cash Flow Statement", "Balance Sheet"], [raw_fin, raw_cf, raw_bs]):
                    df = data.copy()
                    df.index = pd.to_datetime(df.index).year
                    df = df.groupby(level=0).first().T.iloc[:, :5]
                    df.to_excel(writer, sheet_name=title[:31])
            output.seek(0)
            return output
        except Exception as e:
            st.error(f"Excel generation error: {e}")
            return None

    excel = to_excel()
    if excel:
        st.download_button(
            label="📥 Download Excel File",
            data=excel,
            file_name=f"{ticker_input}_financials_{datetime.today().date()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
