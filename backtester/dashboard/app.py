from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import sys
import os
import importlib
import inspect
import pandas as pd
from datetime import datetime

# Add the parent directory to the path so we can import the backtester modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backtester.data_loader import DataLoader
from backtester.engine import BacktestEngine, Strategy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='gevent')
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

@app.route('/backtest/setup/<strategy_name>')
def backtest_setup(strategy_name):
    """Renders the setup page for a given strategy."""
    strategies = get_strategies()
    strategy_class = strategies.get(strategy_name)
    if not strategy_class:
        return "Strategy not found", 404
    
    # Get available date range from S&P 500 data
    spx_mask = data_loader.load_spx_mask()
    min_date = spx_mask.index.min().strftime('%Y-%m-%d')
    max_date = spx_mask.index.max().strftime('%Y-%m-%d')
    
    return render_template('backtest_setup.html', 
                           strategy_name=strategy_name,
                           min_date=min_date,
                           max_date=max_date)

@socketio.on('run_backtest')
def run_backtest_socket(data):
    """Runs the backtest and streams logs to the client."""
    strategy_name = data.get('strategy_name')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    strategies = get_strategies()
    strategy_class = strategies.get(strategy_name)

    if not strategy_class:
        emit('log', {'data': f"Error: Strategy '{strategy_name}' not found."})
        return

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        emit('log', {'data': "Error: Invalid date format. Please use YYYY-MM-DD."})
        return

    strategy_instance = strategy_class(data_loader)
    backtest_engine = BacktestEngine(data_loader, strategy_instance, start_date, end_date)

    emit('log', {'data': f"Starting backtest for {strategy_name} from {start_date} to {end_date}..."})
    
    for log_message in backtest_engine.run():
        emit('log', {'data': log_message})
        socketio.sleep(0.1) # Allow the client to receive the message

    emit('log', {'data': "Backtest finished."})


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

@app.route('/indecies')
def list_indecies():
    """Lists available indecies."""
    # For now, we only have S&P 500
    indecies = ["S&P 500"]
    return render_template('indecies.html', indecies=indecies)

@app.route('/indecies/<index_name>', defaults={'date_str': None})
@app.route('/indecies/<index_name>/<date_str>')
def view_index_constituents(index_name, date_str):
    """Displays the constituents of an index for a given date."""
    if index_name == "S&P 500":
        spx_mask = data_loader.load_spx_mask()
        sectors = data_loader.load_sectors()

        if spx_mask is not None and not spx_mask.empty and sectors is not None:
            if date_str:
                try:
                    current_date = datetime.strptime(date_str, '%Y%m%d').date()
                except ValueError:
                    return "Invalid date format. Please use YYYYMMDD.", 400
            else:
                current_date = spx_mask.index.max().date()

            # Get constituents for the specified date
            try:
                constituents_series = spx_mask.loc[spx_mask.index.date == current_date].iloc[0]
            except IndexError:
                return f"No S&P 500 data found for date: {current_date}", 404
                
            constituents_df = pd.DataFrame(constituents_series[constituents_series == 1].index, columns=['TICKER'])
            
            # Merge with sectors data
            constituents_with_sectors = pd.merge(constituents_df, sectors, on='TICKER', how='left')

            # Fill NaN values to prevent sorting/filtering errors
            for col in ['INDUSTRY_GROUP', 'INDUSTRY_SECTOR', 'INDUSTRY_SUBGROUP']:
                constituents_with_sectors[col] = constituents_with_sectors[col].fillna('')

            # Get unique values for filters from the actual data being displayed
            filter_options = {
                'industry_groups': sorted(constituents_with_sectors['INDUSTRY_GROUP'].unique()),
                'industry_sectors': sorted(constituents_with_sectors['INDUSTRY_SECTOR'].unique()),
                'industry_subgroups': sorted(constituents_with_sectors['INDUSTRY_SUBGROUP'].unique())
            }

            # Get filter values from query parameters
            industry_group = request.args.get('industry_group')
            industry_sector = request.args.get('industry_sector')
            industry_subgroup = request.args.get('industry_subgroup')
            sort_by = request.args.get('sort_by', 'TICKER')
            sort_order = request.args.get('sort_order', 'asc')

            # Filter data
            if industry_group:
                constituents_with_sectors = constituents_with_sectors[constituents_with_sectors['INDUSTRY_GROUP'] == industry_group]
            if industry_sector:
                constituents_with_sectors = constituents_with_sectors[constituents_with_sectors['INDUSTRY_SECTOR'] == industry_sector]
            if industry_subgroup:
                constituents_with_sectors = constituents_with_sectors[constituents_with_sectors['INDUSTRY_SUBGROUP'] == industry_subgroup]

            # Sort data
            if sort_by in constituents_with_sectors.columns:
                constituents_with_sectors = constituents_with_sectors.sort_values(by=sort_by, ascending=(sort_order == 'asc'))

            # Get all available dates for the date picker
            all_available_dates = spx_mask.index.strftime('%Y-%m-%d').tolist()

            return render_template('index_constituents.html', 
                                   index_name=index_name, 
                                   date=current_date,
                                   date_str=current_date.strftime('%Y%m%d'),
                                   constituents=constituents_with_sectors.to_dict(orient='records'),
                                   headers=constituents_with_sectors.columns.tolist(),
                                   filter_options=filter_options,
                                   current_filters={
                                       'industry_group': industry_group,
                                       'industry_sector': industry_sector,
                                       'industry_subgroup': industry_subgroup
                                   },
                                   sort_by=sort_by,
                                   sort_order=sort_order,
                                   available_dates=all_available_dates)
        else:
            return "S&P 500 data or sectors data not found or is empty.", 404
    return "Index not found", 404

@app.route('/api/market_data/<ticker>/<date_str>')
def get_market_data_for_date(ticker, date_str):
    """API endpoint to get market data for a specific ticker and date."""
    try:
        current_date = datetime.strptime(date_str, '%Y%m%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Please use YYYYMMDD."}), 400

    market_data = data_loader.load_market_data(ticker)
    if market_data is not None:
        daily_data = market_data[market_data.index.date == current_date]
        if not daily_data.empty:
            return jsonify(daily_data.iloc[0].to_dict())
    
    # Return empty data if not found, so the frontend can handle it gracefully
    return jsonify({'open': 'N/A', 'high': 'N/A', 'low': 'N/A', 'close': 'N/A', 'volume': 'N/A'})

@app.route('/ca/<index_name>/<date_str>')
def view_corporate_actions(index_name, date_str):
    """Displays corporate actions for an index on a given date."""
    if index_name == "S&P 500":
        spx_mask = data_loader.load_spx_mask()
        if spx_mask is None:
            return "S&P 500 data not found.", 404

        try:
            current_date = datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            return "Invalid date format. Please use YYYYMMDD.", 400

        try:
            constituents_series = spx_mask.loc[spx_mask.index.date == current_date].iloc[0]
            constituents = constituents_series[constituents_series == 1].index.tolist()
        except IndexError:
            return f"No S&P 500 data found for date: {current_date}", 404

        all_corporate_actions = []
        for ticker in constituents:
            div_data = data_loader.load_dividend_data(ticker)
            if div_data is not None:
                # Filter for actions on the given date
                actions_on_date = div_data[div_data.index.date == current_date]
                if not actions_on_date.empty:
                    for _, action in actions_on_date.iterrows():
                        action_data = action.to_dict()
                        action_data['TICKER'] = ticker
                        all_corporate_actions.append(action_data)
        
        return render_template('corporate_actions.html',
                               index_name=index_name,
                               date=current_date,
                               corporate_actions=all_corporate_actions)

    return "Index not found", 404


if __name__ == '__main__':
    socketio.run(app, debug=True)