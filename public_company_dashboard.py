        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Share Price (as of {last_price_date})**: ${last_price:,.2f} [🔗](https://finance.yahoo.com/quote/{ticker_input})")
            st.markdown(f"**Shares Outstanding (as of {last_price_date})**: {shares_out:,.0f} [🔗](https://finance.yahoo.com/quote/{ticker_input}/key-statistics)")
            st.markdown(f"**Market Cap (as of {last_price_date})**: ${market_cap:,.0f} [🔗](https://finance.yahoo.com/quote/{ticker_input}/key-statistics)")
        with col2:
            st.markdown(f"**Cash (as of {fin.index.max().date()})**: ${cash:,.0f} [🔗](https://finance.yahoo.com/quote/{ticker_input}/balance-sheet)")
            st
