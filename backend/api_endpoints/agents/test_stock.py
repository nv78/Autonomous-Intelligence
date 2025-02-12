import handler as handler
if __name__ == "__main__":
    stock_agent = handler.StockMarketAgent()
    result = stock_agent.fetch_stock_price("AAPL")  # AAPL = Apple Inc.
    print(result)
