import pandas as pd
import os

class DataLoader:
    def __init__(self, data_path='./data'):
        self.data_path = data_path
        self.div_data_path = os.path.join(data_path, 'div_data')
        self.eps_data_path = os.path.join(data_path, 'eps_data')
        self.market_data_path = os.path.join(data_path, 'market_data')
        self.spx_mask_path = os.path.join(data_path, 'in_spx_mask.csv')
        self.sectors_path = os.path.join(data_path, 'sectors.csv')

    def load_market_data(self, ticker):
        """Loads market data for a given ticker."""
        file_path = os.path.join(self.market_data_path, f'{ticker}.csv')
        if os.path.exists(file_path):
            return pd.read_csv(file_path, index_col='dt', parse_dates=True)
        return None

    def load_dividend_data(self, ticker):
        """Loads dividend data for a given ticker."""
        file_path = os.path.join(self.div_data_path, f'{ticker}.csv')
        if os.path.exists(file_path):
            return pd.read_csv(file_path, index_col='Ex-Date', parse_dates=True)
        return None

    def load_eps_data(self, ticker):
        """Loads EPS data for a given ticker."""
        file_path = os.path.join(self.eps_data_path, f'{ticker}.csv')
        if os.path.exists(file_path):
            return pd.read_csv(file_path, index_col='Announcement Date', parse_dates=True)
        return None

    def load_spx_mask(self):
        """Loads the S&P 500 mask."""
        if os.path.exists(self.spx_mask_path):
            return pd.read_csv(self.spx_mask_path, index_col='date', parse_dates=True)
        return None

    def load_sectors(self):
        """Loads sector information for all tickers."""
        if os.path.exists(self.sectors_path):
            return pd.read_csv(self.sectors_path)
        return None

    def get_available_tickers(self):
        """Gets a list of available tickers from the market_data directory."""
        files = os.listdir(self.market_data_path)
        return [f.split('.')[0] for f in files if f.endswith('.csv')]

