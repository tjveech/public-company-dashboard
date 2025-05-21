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
    fin = ticker.financials.T
    fin.index = pd.to_datetime(fin.index)
    st.dataframe(fin.tail(4))

    # Valuation Multiples
    st.subheader("📊 Valuation Multiples")
    pe = ev_ebitda = ev_sales = None
    try:
        revenue = fin.get("Total Revenue", pd.Series([None])).dropna()
        revenue = revenue.iloc[-1] if not revenue.empty else None

        ebitda_series = fin.get("EBITDA", pd.Series([None])).dropna()
        ebitda = ebitda_series.iloc[-1] if not ebitda_series.empty else None

        net_income = fin.get("Net Income", pd.Series([None])).dropna()
        net_income = net_income.iloc[-1] if not net_income.empty else None

        pe = market_cap / net_income if net_income and net_income != 0 else None
        ev_ebitda = enterprise_value / ebitda if ebitda and ebitda != 0 else None
        ev_sales = enterprise_value / revenue if revenue and revenue != 0 else None

        st.write({
            "P/E": round(pe, 2) if pe else "N/A",
            "EV/EBITDA": round(ev_ebitda, 2) if ev_ebitda else "N/A",
            "EV/Sales": round(ev_sales, 2) if ev_sales else "N/A",
        })
    except Exception as e:
        st.warning(f"Unable to calculate valuation multiples. Error: {e}")

    # Excel Export
    st.subheader("📤 Export to Excel")
    def to_excel():
        output = BytesIO()
        try:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                summary = pd.DataFrame({
                    "Metric": ["Market Cap", "Enterprise Value", "Shares Outstanding", "Total Debt", "Cash"],
                    "Value": [market_cap, enterprise_value, shares_out, total_debt, cash]
                })
                summary.to_excel(writer, index=False, sheet_name="Summary")

                # Price History (cleaned)
                hist_clean = hist[['Close']].copy()
                hist_clean.index.name = "Date"
                hist_clean = hist_clean.reset_index()
                hist_clean.columns = [str(col) for col in hist_clean.columns]
                hist_clean = hist_clean.applymap(lambda x: float(x) if pd.notnull(x) else "")
                hist_clean.to_excel(writer, index=False, sheet_name="Price History")

                # Income Statement (cleaned)
                fin_clean = fin.copy()
                fin_clean.index = fin_clean.index.strftime('%Y-%m-%d')
                fin_clean.columns = [str(col) for col in fin_clean.columns]
                fin_clean = fin_clean.reset_index().rename(columns={"index": "Date"})
                fin_clean = fin_clean.applymap(lambda x: float(x) if pd.notnull(x) else "")
                fin_clean.to_excel(writer, index=False, sheet_name="Income Statement")

                # Valuation Sheet
                val = pd.DataFrame({
                    "Metric": ["P/E", "EV/EBITDA", "EV/Sales"],
                    "Value": [round(pe, 2) if pe else "N/A",
                              round(ev_ebitda, 2) if ev_ebitda else "N/A",
                              round(ev_sales, 2) if ev_sales else "N/A"]
                })
                val.to_excel(writer, index=False, sheet_name="Valuation")
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
