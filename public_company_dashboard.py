import yfinance as yf
import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime

# Set page config
st.set_page_config(page_title="Public Company Dashboard", layout="wide")

st.title("📊 Public Company Financial Dashboard")

ticker_input = st.text_input("Enter Ticker Symbol (e.g., AAPL, MSFT):", value="AAPL")

if ticker_input:
    ticker = yf.Ticker(ticker_input)
    info = ticker.info

    # Price Data
    hist = ticker.history(period="5y")
    hist.index = hist.index.tz_localize(None)
    last_price_date = hist.index.max().date()
    last_price = hist['Close'].iloc[-1]

    st.subheader("📈 Stock Price (5 Years)")
    st.line_chart(hist['Close'])

    # Financials
    fin = ticker.financials.T
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

        # Financial figures for LTM
        revenue = fin.get("Total Revenue", pd.Series([None])).dropna().iloc[-1]
        ebitda = fin.get("EBITDA", pd.Series([None])).dropna().iloc[-1]
        net_income = fin.get("Net Income", pd.Series([None])).dropna().iloc[-1]

        # Valuation multiples
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

        st.markdown("### 📊 Valuation Multiples (LTM)")
        st.metric("P/E", f"{round(pe, 2)}" if pe else "N/A")
        st.metric("EV / EBITDA", f"{round(ev_ebitda, 2)}" if ev_ebitda else "N/A")
        st.metric("EV / Revenue", f"{round(ev_sales, 2)}" if ev_sales else "N/A")

    except Exception as e:
        st.warning(f"Some key data is missing or caused an error: {e}")

    # Income Statement Reformatted
    st.subheader("📄 Income Statement (Fiscal Years + LTM)")
    try:
        income_items = [
            "Total Revenue", "Gross Profit", "Operating Expenses", "EBITDA",
            "Ebit", "Net Income", "Capital Expenditures", "Operating Cash Flow"
        ]

        income_renames = {
            "Total Revenue": "Revenue",
            "Gross Profit": "Gross Profit",
            "Operating Expenses": "OpEx",
            "EBITDA": "EBITDA",
            "Ebit": "EBIT",
            "Net Income": "Net Income",
            "Capital Expenditures": "CapEx",
            "Operating Cash Flow": "Op. Cash Flow"
        }

        fiscal_years = fin.index.year.unique().tolist()
        income_data = {}
        for item in income_items:
            if item in fin.columns:
                row = fin[item].copy()
                row.index = row.index.year
                row = row.groupby(level=0).first()
                income_data[income_renames.get(item, item)] = row

        df_income = pd.DataFrame(income_data).T
        df_income = df_income.loc[:, ~df_income.columns.duplicated()].copy()
        df_income.columns = df_income.columns.astype(str)
        st.dataframe(df_income)

    except Exception as e:
        st.warning(f"Could not generate income statement table: {e}")

    # Excel Export
    st.subheader("📤 Export to Excel")
    def to_excel():
        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Summary
                summary = pd.DataFrame({
                    "Metric": ["Share Price", "Shares Outstanding", "Market Cap", "Cash", "Debt", "Enterprise Value"],
                    "Value": [last_price, shares_out, market_cap, cash, total_debt, enterprise_value]
                })
                summary.to_excel(writer, index=False, sheet_name="Summary")

                # Valuation
                val = pd.DataFrame({
                    "Metric": ["P/E (LTM)", "EV/EBITDA (LTM)", "EV/Revenue (LTM)"],
                    "Value": [round(pe, 2) if pe else "N/A",
                              round(ev_ebitda, 2) if ev_ebitda else "N/A",
                              round(ev_sales, 2) if ev_sales else "N/A"]
                })
                val.to_excel(writer, index=False, sheet_name="Valuation")

                # Price History
                hist_clean = hist[['Close']].copy()
                hist_clean.index.name = "Date"
                hist_clean = hist_clean.reset_index()
                hist_clean['Date'] = pd.to_datetime(hist_clean['Date']).dt.date
                hist_clean = hist_clean.astype({"Close": float})
                hist_clean.to_excel(writer, index=False, sheet_name="Price History")

                # Income Statement
                df_income.to_excel(writer, sheet_name="Income Statement")

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
            file_name=f"{ticker_input}_summary_{datetime.today().date()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
