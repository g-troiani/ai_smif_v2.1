# components/ui_module/routes.py

from flask import render_template, redirect, url_for, jsonify, request, flash
from app import app
from forms import TickerForm, StrategyForm, BacktestForm, DataConfigForm, DataSettingsForm
from socketio_events import send_alert
from flask import send_file
import sqlite3
from datetime import datetime

# Import backtesting components
from components.backtesting_module.backtester import Backtester
from components.backtesting_module.optimizer import Optimizer
from components.backtesting_module.parameter_validator import ParameterValidator
from components.backtesting_module.formatters import ResultFormatter
from components.backtesting_module.results_viewer import ResultsViewer

from flask import request, jsonify
from components.ui_module import app
from components.trading_execution_engine.execution_engine import ExecutionEngine
from components.trading_execution_engine.trade_signal import TradeSignal
from datetime import datetime

execution_engine = ExecutionEngine()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/strategy', methods=['GET', 'POST'])
def strategy():
    form = StrategyForm()
    if form.validate_on_submit():
        # Process strategy configuration
        return redirect(url_for('dashboard'))
    return render_template('strategy.html', form=form)

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/add_ticker', methods=['POST'])
def api_add_ticker():
    data = request.get_json()
    ticker = data.get('ticker')
    if not ticker:
        return jsonify({'status': 'error', 'message': 'No ticker provided'}), 400
    # Process ticker addition
    return jsonify({'status': 'success'})

@app.route('/api/manual_trade', methods=['POST'])
def manual_trade():
    data = request.json
    try:
        ticker = data['ticker'].upper()
        quantity = float(data['quantity'])
        side = data['side'].upper()
        if side not in ('BUY', 'SELL'):
            return jsonify({'error': 'Invalid side. Must be BUY or SELL.'}), 400

        trade_signal = TradeSignal(
            ticker=ticker,
            signal_type=side,
            quantity=quantity,
            strategy_id='manual_trade',
            timestamp=datetime.utcnow(),
            price=None
        )
        execution_engine.add_trade_signal(trade_signal)
        return jsonify({'message': 'Trade signal received and being processed.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    

@app.route('/api/liquidate_positions', methods=['POST'])
def liquidate_positions():
    # Handle emergency liquidation
    return jsonify({'message': 'All positions liquidated'})

@app.route('/backtest', methods=['GET', 'POST'])
def backtest():
    form = BacktestForm()
    if form.validate_on_submit():
        try:
            # Extract form data
            strategy_name = form.strategy.data
            ticker = form.ticker.data.upper()
            start_date = form.start_date.data
            end_date = form.end_date.data
            strategy_params = {
                'short_window': form.short_window.data,
                'long_window': form.long_window.data
            }
            optimize = form.optimize.data

            # Validate parameters
            try:
                ParameterValidator.validate_parameters(strategy_name, strategy_params)
            except ValueError as e:
                flash(f"Invalid parameters: {str(e)}", 'danger')
                return redirect(url_for('backtest'))

            # Run backtest
            backtester = Backtester(strategy_name, strategy_params, ticker, start_date, end_date)
            
            if optimize:
                optimizer = Optimizer(strategy_name, ticker, start_date, end_date)
                param_ranges = ParameterValidator.generate_grid_parameters(strategy_name)
                results = optimizer.run_optimization(param_ranges)
                best_params = optimizer.get_best_params(results)
                strategy_params.update(best_params)
                backtester.strategy_params = strategy_params
            
            backtester.run_backtest()
            backtester.save_results()
            
            # Format results
            metrics = backtester.get_performance_metrics()
            formatted_metrics = ResultFormatter.format_metrics(metrics)
            comparison = backtester.compare_with_benchmark()
            formatted_comparison = {
                'strategy': ResultFormatter.format_metrics(comparison['Strategy']),
                'benchmark': ResultFormatter.format_metrics(comparison['Benchmark'])
            }
            
            return render_template(
                'backtest_results.html',
                metrics=formatted_metrics,
                comparison=formatted_comparison,
                strategy_name=strategy_name,
                ticker=ticker
            )
            
        except Exception as e:
            flash(f"Error during backtesting: {str(e)}", 'danger')
            return redirect(url_for('backtest'))
            
    return render_template('backtest.html', form=form)

@app.route('/api/backtest/results', methods=['GET'])
def get_backtest_results():
    try:
        viewer = ResultsViewer()
        results = viewer.get_results()
        formatted_results = ResultFormatter.format_metrics(results.to_dict('records'))
        return jsonify({
            'success': True,
            'results': formatted_results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.route('/data_management', methods=['GET', 'POST'])
def data_management():
    form = DataConfigForm()
    if form.validate_on_submit():
        # Process data configuration
        return redirect(url_for('dashboard'))
    return render_template('data_management.html', form=form)

@app.route('/api/load_historical_data', methods=['POST'])
def load_historical_data():
    try:
        data = request.get_json()
        tickers = data.get('tickers', [])
        interval = data.get('interval', '5min')
        period = data.get('period', '5y')
        # Process historical data request
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/upload_tickers', methods=['POST'])
def upload_tickers():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'}), 400
    try:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No file selected'}), 400
        if file and file.filename.endswith('.csv'):
            # Process ticker list CSV
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Invalid file format'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/data_settings', methods=['GET', 'POST'])
def data_settings():
    form = DataSettingsForm()
    if form.validate_on_submit():
        if form.tickers_file.data:
            # Process tickers CSV file
            file = form.tickers_file.data
            process_tickers_file(file)
        return redirect(url_for('data_settings'))
    
    # Get current data status
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM historical_data")
    data_count = cursor.fetchone()[0]
    cursor.execute("SELECT MAX(timestamp) FROM historical_data")
    last_update = cursor.fetchone()[0]
    conn.close()
    
    return render_template('data_settings.html', 
                         form=form, 
                         data_count=data_count,
                         last_update=last_update)

@app.route('/api/data_status')
def get_data_status():
    conn = sqlite3.connect('data/data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(timestamp) FROM historical_data")
    last_update = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT ticker_symbol) FROM historical_data")
    ticker_count = cursor.fetchone()[0]
    conn.close()
    
    return jsonify({
        'last_update': last_update,
        'ticker_count': ticker_count,
        'interval': '5min',
        'period': '5y'
    })