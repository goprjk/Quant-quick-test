import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import coint
from itertools import combinations
from ..engine import Strategy

class PairsTradingStrategy(Strategy):
    def __init__(self, data_loader, lookback_period=60, zscore_threshold=2.0):
        super().__init__(data_loader)
        self.lookback_period = lookback_period
        self.zscore_threshold = zscore_threshold

    def run(self, start_date, end_date):
        """
        Runs the pairs trading strategy for a given date range and yields log messages.
        """
        yield "Running pairs trading strategy..."

        spx_mask = self.data_loader.load_spx_mask()
        if spx_mask is None:
            yield "S&P 500 data not found."
            return

        # Iterate through each day in the date range
        for current_date in pd.date_range(start_date, end_date):
            yield f"--- Processing date: {current_date.date()} ---"

            constituents = self.get_constituents_for_date(spx_mask, current_date)
            if not constituents:
                yield f"No constituents found for {current_date.date()}"
                continue

            all_market_data = self.load_historical_data(constituents, current_date)
            if len(all_market_data) < 2:
                yield "Not enough historical data to find pairs."
                continue

            cointegrated_pairs = self.find_cointegrated_pairs(all_market_data)

            if not cointegrated_pairs:
                yield "No cointegrated pairs found."
                continue

            yield f"Found {len(cointegrated_pairs)} cointegrated pairs:"
            for pair, p_value in cointegrated_pairs:
                yield f"  - Pair: {pair}, Cointegration p-value: {p_value:.4f}"

    def get_constituents_for_date(self, spx_mask, date):
        try:
            constituents_series = spx_mask.loc[spx_mask.index.date == date.date()].iloc[0]
            return constituents_series[constituents_series == 1].index.tolist()
        except IndexError:
            return []

    def load_historical_data(self, tickers, current_date):
        all_market_data = {}
        for ticker in tickers:
            market_data = self.data_loader.load_market_data(ticker)
            if market_data is not None and not market_data.empty:
                historical_data = market_data[market_data.index <= current_date].tail(self.lookback_period)
                if len(historical_data) == self.lookback_period:
                    all_market_data[ticker] = historical_data['close']
        return all_market_data

    def find_cointegrated_pairs(self, data):
        """
        Finds cointegrated pairs of stocks from the given data.
        """
        cointegrated_pairs = []
        tickers = list(data.keys())
        
        for pair in combinations(tickers, 2):
            stock1_data = data[pair[0]]
            stock2_data = data[pair[1]]

            if stock1_data.empty or stock2_data.empty:
                continue

            score, p_value, _ = coint(stock1_data, stock2_data)

            if p_value < 0.05:
                cointegrated_pairs.append((pair, p_value))
        
        return cointegrated_pairs
