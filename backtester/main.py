from backtester.data_loader import DataLoader
from backtester.engine import BacktestEngine
from backtester.strategies.pairs_trading import PairsTradingStrategy
from backtester.strategies.basket_trading import BasketTradingStrategy

def main():
    """Main entry point for the application."""
    data_loader = DataLoader()

    # Initialize strategies
    pairs_trading_strategy = PairsTradingStrategy(data_loader)
    basket_trading_strategy = BasketTradingStrategy(data_loader)

    # Run backtests
    print("--- Running Pairs Trading Strategy ---")
    pairs_backtest = BacktestEngine(data_loader, pairs_trading_strategy)
    pairs_backtest.run()

    print("\n--- Running Basket Trading Strategy ---")
    basket_backtest = BacktestEngine(data_loader, basket_trading_strategy)
    basket_backtest.run()

if __name__ == '__main__':
    main()
