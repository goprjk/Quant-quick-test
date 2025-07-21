class BacktestEngine:
    def __init__(self, data_loader, strategy, start_date, end_date):
        self.data_loader = data_loader
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date

    def run(self):
        """Runs the backtest and yields log messages."""
        yield "Initializing backtest..."
        
        # In a real backtest, you would iterate through the date range
        # and apply the strategy on each day.
        
        # For now, we'll just run the strategy once as a demonstration.
        yield from self.strategy.run(self.start_date, self.end_date)
        
        yield "Backtest finished."

class Strategy:
    def __init__(self, data_loader):
        self.data_loader = data_loader

    def run(self, start_date, end_date):
        """Runs the strategy for a given date range and yields log messages."""
        raise NotImplementedError("Strategy.run() must be implemented in a subclass.")
