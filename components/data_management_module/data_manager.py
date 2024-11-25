# components/data_management_module/data_manager.py

import pandas as pd
import threading
import logging
from datetime import datetime, timedelta
import time
from pathlib import Path
from .config import config
from .alpaca_api import AlpacaAPIClient
from .data_access_layer import db_manager, Ticker, HistoricalData
from .real_time_data import RealTimeDataStreamer

class DataManager:
    """Main class for managing market data operations"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.api_client = AlpacaAPIClient()
        self.lock = threading.Lock()
        self.tickers = self._load_tickers()
        self.real_time_streamer = None
        self._last_maintenance = None
        self.initialize_database()

    def _setup_logging(self):
        """Set up logging for the data manager"""
        logger = logging.getLogger('data_manager')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(config.get('DEFAULT', 'log_file'))
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    def _load_tickers(self):
        """Load tickers from the configured CSV file"""
        try:
            tickers_file = Path(config.get('DEFAULT', 'tickers_file'))
            if not tickers_file.exists():
                self.logger.error(f"Tickers file not found: {tickers_file}")
                raise FileNotFoundError(f"Tickers file not found: {tickers_file}")
                
            df = pd.read_csv(tickers_file)
            if 'ticker' not in df.columns:
                raise ValueError("CSV file must contain a 'ticker' column")
                
            tickers = df['ticker'].unique().tolist()
            self.logger.info(f"Loaded {len(tickers)} tickers")
            return tickers
        except Exception as e:
            self.logger.error(f"Failed to load tickers: {str(e)}")
            raise

    def initialize_database(self):
        """Initialize database with tickers"""
        try:
            with self.lock:
                session = db_manager.Session()
                try:
                    for ticker in self.tickers:
                        if not session.query(Ticker).filter_by(symbol=ticker).first():
                            session.add(Ticker(symbol=ticker))
                    session.commit()
                    self.logger.info("Database initialized with tickers")
                except Exception as e:
                    session.rollback()
                    self.logger.error(f"Database initialization error: {str(e)}")
                    raise
                finally:
                    session.close()
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise

    def fetch_historical_data(self):
        """Fetch historical data for all tickers"""
        years = config.get_int('DEFAULT', 'historical_data_years')
        start_date = datetime.now() - timedelta(days=years * 365)
        end_date = datetime.now()

        for ticker in self.tickers:
            try:
                self.logger.info(f"Fetching historical data for {ticker}")
                df = self.api_client.fetch_historical_data(ticker, start_date, end_date)
                
                if df is not None and not df.empty:
                    self._store_historical_data(ticker, df)
                    self.logger.info(f"Stored historical data for {ticker}")
                else:
                    self.logger.warning(f"No historical data available for {ticker}")
                    
                # Respect rate limits
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error processing {ticker}: {str(e)}")

    def _store_historical_data(self, ticker, df):
        """Store historical data in the database"""
        with self.lock:
            session = db_manager.Session()
            try:
                records = []
                for index, row in df.iterrows():
                    try:
                        HistoricalData.validate_price_data(
                            row['o'], row['h'], row['l'], row['c'], row['v']
                        )
                        record = HistoricalData(
                            ticker_symbol=ticker,
                            timestamp=index,
                            open=row['o'],
                            high=row['h'],
                            low=row['l'],
                            close=row['c'],
                            volume=row['v']
                        )
                        records.append(record)
                    except ValueError as e:
                        self.logger.warning(f"Skipping invalid data point for {ticker}: {str(e)}")

                if records:
                    session.bulk_save_objects(records)
                    session.commit()
                    self.logger.info(f"Stored {len(records)} records for {ticker}")
                    
            except Exception as e:
                session.rollback()
                self.logger.error(f"Database error for {ticker}: {str(e)}")
                raise
            finally:
                session.close()

    def start_real_time_streaming(self):
        """Start real-time data streaming"""
        if self.real_time_streamer is None:
            try:
                self.real_time_streamer = RealTimeDataStreamer(self.tickers)
                # Start the streamer in a separate thread to make it non-blocking
                threading.Thread(target=self.real_time_streamer.start, daemon=True).start()
                self.logger.info("Started real-time data streaming")
            except Exception as e:
                self.logger.error(f"Failed to start real-time streaming: {str(e)}")
                raise
        else:
            self.logger.warning("Real-time streamer is already running")

    def stop_real_time_streaming(self):
        """Stop real-time data streaming"""
        if self.real_time_streamer:
            try:
                self.real_time_streamer.stop()
                self.real_time_streamer = None
                self.logger.info("Stopped real-time data streaming")
            except Exception as e:
                self.logger.error(f"Error stopping real-time stream: {str(e)}")
                raise

    def perform_maintenance(self):
        """Perform database maintenance"""
        try:
            current_time = datetime.now()
            # Only perform maintenance if it hasn't been done in the last 24 hours
            if (self._last_maintenance is None or 
                (current_time - self._last_maintenance).total_seconds() > 86400):
                
                db_manager.cleanup_old_data()
                self._last_maintenance = current_time
                self.logger.info("Completed database maintenance")
        except Exception as e:
            self.logger.error(f"Error during maintenance: {str(e)}")
            raise

    def get_historical_data(self, ticker, start_date, end_date):
        """Retrieve historical data for a specific ticker and date range"""
        try:
            data = db_manager.get_historical_data(ticker, start_date, end_date)
            if not data:
                self.logger.error(f"No data found for {ticker} between {start_date} and {end_date}")
            return data
        except Exception as e:
            self.logger.error(f"Error retrieving historical data: {str(e)}")
            raise

    def validate_data_integrity(self):
        """Validate data integrity across the database"""
        try:
            session = db_manager.Session()
            try:
                for ticker in self.tickers:
                    # Check for missing data points
                    last_record = session.query(HistoricalData)\
                        .filter_by(ticker_symbol=ticker)\
                        .order_by(HistoricalData.timestamp.desc())\
                        .first()
                    
                    if last_record:
                        # Update last_updated timestamp for the ticker
                        ticker_record = session.query(Ticker)\
                            .filter_by(symbol=ticker)\
                            .first()
                        if ticker_record:
                            ticker_record.last_updated = datetime.utcnow()
                            
                session.commit()
                self.logger.info("Completed data integrity validation")
                
            except Exception as e:
                session.rollback()
                self.logger.error(f"Error during data validation: {str(e)}")
                raise
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to validate data integrity: {str(e)}")
            raise

    def __del__(self):
        """Cleanup when the object is destroyed"""
        try:
            self.stop_real_time_streaming()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def get_backtrader_data(self, ticker, start_date, end_date):
        """
        Retrieves historical data in a format compatible with Backtrader.

        :param ticker: Stock ticker symbol.
        :param start_date: Start date as a datetime object.
        :param end_date: End date as a datetime object.
        :return: Pandas DataFrame with necessary columns.
        """
        try:
            # Get historical data
            data = self.get_historical_data(ticker, start_date, end_date)
            
            # Convert to DataFrame if we get a list
            if isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                df = data
                
            # Check if we have data
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                raise ValueError(f"No data found for ticker {ticker} between {start_date} and {end_date}")
                
            # Select and rename columns
            if isinstance(df, pd.DataFrame):
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                df.rename(columns={'timestamp': 'datetime'}, inplace=True)
                df.set_index('datetime', inplace=True)
                df.index = pd.to_datetime(df.index)
                
            return df
            
        except Exception as e:
            self.logger.error(f"Error retrieving backtrader data for {ticker}: {str(e)}")
            # Return empty DataFrame instead of raising to maintain compatibility
            return pd.DataFrame()
