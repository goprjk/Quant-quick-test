class BacktestEngine:
    def __init__(self, data_loader, strategy):
        self.data_loader = data_loader
        self.strategy = strategy

    def run(self):
        """Runs the backtest."""
        # This is where the backtesting logic will go.
        # For now, it's just a placeholder.
        print("Running backtest...")
        self.strategy.run()
        print("Backtest finished.")

class Strategy:
    def __init__(self, data_loader):
        self.data_loader = data_loader

    def run(self):
        """Runs the strategy."""
        raise NotImplementedError("Strategy.run() must be implemented in a subclass.")
