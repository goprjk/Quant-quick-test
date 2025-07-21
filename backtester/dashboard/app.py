from flask import Flask, render_template, request, redirect, url_for
import sys
import os
import importlib
import inspect
import pandas as pd

# Add the parent directory to the path so we can import the backtester modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backtester.data_loader import DataLoader
from backtester.engine import BacktestEngine, Strategy

app = Flask(__name__)
data_loader = DataLoader(data_path='./data')
backtest_results = {}

def get_strategies():
    """Dynamically loads all strategies from the strategies directory."""
    strategies = {}
    strategies_path = os.path.join(os.path.dirname(__file__), '..', 'strategies')
    for filename in os.listdir(strategies_path):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = f"backtester.strategies.{filename[:-3]}"
            module = importlib.import_module(module_name)
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, Strategy) and cls is not Strategy:
                    strategies[name] = cls
    return strategies

@app.route('/')
def index():
    """Main dashboard page."""
    strategies = get_strategies()
    indices = ["S&P 500"]  # Hardcoded for now
    return render_template('index.html', strategies=strategies.keys(), indices=indices)

@app.route('/data/<ticker>')
def view_data(ticker):
    """Displays market data for a given ticker."""
    market_data = data_loader.load_market_data(ticker)
    if market_data is not None:
        return render_template('data_viewer.html', ticker=ticker, data=market_data.to_html())
    return f"Data not found for ticker: {ticker}", 404

@app.route('/backtest/run', methods=['POST'])
def run_backtest():
    """Runs a backtest for a given strategy."""
    strategy_name = request.form.get('strategy')
    strategies = get_strategies()
    strategy_class = strategies.get(strategy_name)

    if strategy_class:
        strategy_instance = strategy_class(data_loader)
        backtest_engine = BacktestEngine(data_loader, strategy_instance)
        # In a real application, this would run in the background
        results = backtest_engine.run() 
        backtest_id = f"{strategy_name}_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
        backtest_results[backtest_id] = results
        return redirect(url_for('view_backtest_results', backtest_id=backtest_id))
    
    return "Strategy not found", 404

@app.route('/backtest/results/<backtest_id>')
def view_backtest_results(backtest_id):
    """Displays the results of a backtest."""
    results = backtest_results.get(backtest_id)
    if results is not None:
        return render_template('results.html', backtest_id=backtest_id, results=results)
    return "Backtest results not found", 404

@app.route('/indices')
def list_indices():
    """Lists available indices."""
    # For now, we only have S&P 500
    indices = ["S&P 500"]
    return render_template('indices.html', indices=indices)

@app.route('/indices/<index_name>')
def view_index_constituents(index_name):
    """Displays the constituents of an index."""
    if index_name == "S&P 500":
        spx_mask = data_loader.load_spx_mask()
        if spx_mask is not None and not spx_mask.empty:
            # Get constituents for the latest date
            latest_date = spx_mask.index.max()
            constituents = spx_mask.loc[latest_date]
            constituents = constituents[constituents == 1].index.tolist()
            return render_template('index_constituents.html', index_name=index_name, date=latest_date.date(), constituents=constituents)
        else:
            return "S&P 500 data not found or is empty.", 404
    return "Index not found", 404

if __name__ == '__main__':
    app.run(debug=True)