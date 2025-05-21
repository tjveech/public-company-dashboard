
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
    st.subheader("📈 Stock Price (5 Years)")
    st.line_chart(hist['Close'])

    # Key Metrics
    st.subheader("📌 Key Market Data")
    try:
        shares_out = info.get('sharesOutstanding', 0)
        market_cap = info.get('marketCap', 0)
        total_debt = info.get('totalDebt', 0)
        cash = info.get('totalCash', 0)
        enterprise_value = market_cap + total_debt - cash

        st.metric("Market Cap", f"${market_cap:,.0f}")
        st.metric("Enterprise Value (EV)", f"${enterprise_value:,.0f}")
        st.metric("Shares Outstanding", f"{shares_out:,.0f}")
        st.metric("Total Debt", f"${total_debt:,.0f}")
        st.metric("Cash", f"${cash:,.0f}")
    except:
        st.warning("Some market data is missing or incomplete.")

    # Financial Statements
    st.subheader("📄 Income Statement (Last 4 Years)")
    fin = ticker.financials
    fin = fin.T
    fin.index = pd.to_datetime(fin.index)
    st.dataframe(fin.tail(4))

    # Valuation Metrics
    st.subheader("📊 Valuation Multiples")
    try:
        revenue = fin["Total Revenue"].iloc[-1]
        ebitda = fin["Ebit"] + fin["Interest Expense"] + fin["Depreciation"]
        ebitda = ebitda.iloc[-1]
        net_income = fin["Net Income"].iloc[-1]
        pe = market_cap / net_income if net_income else None
        ev_ebitda = enterprise_value / ebitda if ebitda else None
        ev_sales = enterprise_value / revenue if revenue else None

        st.write({
            "P/E": round(pe, 2) if pe else "N/A",
            "EV/EBITDA": round(ev_ebitda, 2) if ev_ebitda else "N/A",
            "EV/Sales": round(ev_sales, 2) if ev_sales else "N/A",
        })
    except:
        st.warning("Unable to calculate valuation multiples.")

    # Excel Export
    st.subheader("📤 Export to Excel")
    def to_excel():
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            summary = pd.DataFrame({
                "Metric": ["Market Cap", "Enterprise Value", "Shares Outstanding", "Total Debt", "Cash"],
                "Value": [market_cap, enterprise_value, shares_out, total_debt, cash]
            })
            summary.to_excel(writer, index=False, sheet_name="Summary")
            hist[['Close']].to_excel(writer, sheet_name="Price History")
            fin.to_excel(writer, sheet_name="Income Statement")
            val = pd.DataFrame({
                "Metric": ["P/E", "EV/EBITDA", "EV/Sales"],
                "Value": [round(pe, 2) if pe else "N/A",
                          round(ev_ebitda, 2) if ev_ebitda else "N/A",
                          round(ev_sales, 2) if ev_sales else "N/A"]
            })
            val.to_excel(writer, index=False, sheet_name="Valuation")
        output.seek(0)
        return output

    excel = to_excel()
    st.download_button(
        label="📥 Download Excel File",
        data=excel,
        file_name=f"{ticker_input}_summary_{datetime.today().date()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
