# components/data_management_module/data_manager.py

import pandas as pd
import threading
import logging
from datetime import datetime, timedelta, time
import time as time_module  # Alias to avoid conflict with datetime.time
from pathlib import Path
from .config import config
from .alpaca_api import AlpacaAPIClient
from .data_access_layer import db_manager, Ticker, HistoricalData
from .real_time_data import RealTimeDataStreamer
import pytz
from dateutil.relativedelta import relativedelta  # Added for accurate date calculations
from sqlalchemy.exc import IntegrityError        # Added for handling database integrity errors
import traceback         


class DataManager:
    """Main class for managing market data operations"""

    def __init__(self):
        self.logger = self._setup_logging()
        self.api_client = AlpacaAPIClient()
        self.lock = threading.RLock()
        self.tickers = self._load_tickers()
        self.real_time_streamer = None
        self.logger.info("DataManager initialized.")
        self._last_maintenance = None
        self.initialize_database()
        self.start_real_time_streaming()

    def _setup_logging(self):
        """Set up logging for the data manager"""
        logger = logging.getLogger('data_manager')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(config.get('DEFAULT', 'log_file'))
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
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
        """Initialize database with historical data"""
        try:
            with self.lock:
                print(f"CRITICAL DEBUG: Starting database initialization")
                ny_tz = pytz.timezone('America/New_York')
                end_date = datetime.now(ny_tz)
                
                # Retrieve the number of years from the configuration
                years = config.get_int('DEFAULT', 'historical_data_years')
                start_date = end_date - relativedelta(years=years)  # Use relativedelta for accurate year subtraction

                # Print the date range for debugging
                print(f"CRITICAL DEBUG: Date range from {start_date} to {end_date}")

                for ticker in self.tickers:
                    self.logger.info(f"Fetching historical data for {ticker}")

                    # Fetch and store historical data
                    historical_data = self.api_client.fetch_historical_data(
                        ticker, start_date, end_date, timeframe='5Min'
                    )

                    print(f"CRITICAL DEBUG: Got data empty={historical_data.empty}")

                    if not historical_data.empty:
                        # Filter data to market hours (9:30 AM to 4:00 PM EST)
                        historical_data = self._filter_market_hours(historical_data, ny_tz)
                        self._save_historical_data(ticker, historical_data)

                    # Respect rate limits
                    time_module.sleep(1)  # Ensure 'time_module' is correctly imported

        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise




                    
    def _filter_market_hours(self, data, timezone):
        """Filter data to only include market hours (9:30 AM to 4:00 PM EST)"""
        market_open = time(9, 30)    # Corrected from datetime_time(9, 30)
        market_close = time(16, 0)   # Corrected from datetime_time(16, 0)
        data = data.tz_convert(timezone)
        data = data.between_time(market_open, market_close)
        return data


    def fetch_historical_data(self, ticker, start_date, end_date, timeframe='5Min'):
        """Fetch historical data with proper formatting"""
        all_data = []
        current_date = start_date
        
        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=self.chunk_size), end_date)
            chunk_data = self._fetch_data_chunk(ticker, current_date, chunk_end, timeframe)
            
            if not chunk_data.empty:
                all_data.append(chunk_data)
            current_date = chunk_end + timedelta(seconds=1)  # Avoid overlapping

        final_data = pd.concat(all_data) if all_data else pd.DataFrame()
        print(f"CRITICAL DEBUG: Final data shape={final_data.shape}, columns={final_data.columns.tolist()}")

        if not final_data.empty:
            earliest_date = final_data.index.min()
            latest_date = final_data.index.max()
            print(f"CRITICAL DEBUG: Data ranges from {earliest_date} to {latest_date}")

        return final_data


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
        if not self.real_time_streamer:
            self.logger.info("Starting real-time data streaming")
            try:
                self.real_time_streamer = RealTimeDataStreamer(self.tickers)
                # Start the streamer in a separate thread to make it non-blocking
                threading.Thread(target=self.real_time_streamer.start, daemon=True).start()
                self.logger.info("Real-time streaming started successfully")
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

    def _save_historical_data(self, ticker, df):
        """Store historical data in the database"""
        with self.lock:
            session = db_manager.Session()
            try:
                records = []
                for index, row in df.iterrows():
                    try:
                        # Updated column names to match DataFrame
                        HistoricalData.validate_price_data(
                            row['open'], row['high'], row['low'], row['close'], row['volume']
                        )
                        record = HistoricalData(
                            ticker_symbol=ticker,
                            timestamp=index,
                            open=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row['volume']
                        )
                        records.append(record)
                    except ValueError as e:
                        self.logger.warning(f"Skipping invalid data point for {ticker}: {str(e)}")
                        print(f"CRITICAL DEBUG: Skipping invalid data point for {ticker}: {str(e)}")

                if records:
                    batch_size = config.get_int('DEFAULT', 'batch_size')  # Use batch_size from config
                    num_records = len(records)
                    print(f"CRITICAL DEBUG: Attempting to save {num_records} records for {ticker}")

                    for i in range(0, num_records, batch_size):
                        batch = records[i:i+batch_size]
                        try:
                            session.bulk_save_objects(batch)
                            session.commit()
                            print(f"CRITICAL DEBUG: Successfully saved batch {i//batch_size +1} with {len(batch)} records")
                        except IntegrityError as ie:
                            session.rollback()
                            self.logger.warning(f"IntegrityError when saving batch {i//batch_size +1} for {ticker}: {str(ie)}")
                            print(f"CRITICAL DEBUG: IntegrityError when saving batch {i//batch_size +1} for {ticker}: {str(ie)}")
                        except Exception as e:
                            session.rollback()
                            self.logger.error(f"Exception when saving batch {i//batch_size +1} for {ticker}: {str(e)}")
                            print(f"CRITICAL DEBUG: Exception when saving batch {i//batch_size +1} for {ticker}: {str(e)}")
                            traceback.print_exc()
                            raise

                self.logger.info(f"Stored {len(records)} records for {ticker}")
                print(f"CRITICAL DEBUG: Stored {len(records)} records for {ticker}")
                    
            except Exception as e:
                session.rollback()
                self.logger.error(f"Database error for {ticker}: {str(e)}")
                print(f"CRITICAL DEBUG: Database error for {ticker}: {str(e)}")
                raise
            finally:
                session.close()
                print("CRITICAL DEBUG: Database session closed.")



    def __del__(self):
        """Cleanup when the object is destroyed"""
        try:
            self.stop_real_time_streaming()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def _fetch_historical_data(self, ticker):
        """Fetch historical data for a ticker"""
        try:
            end_date = datetime.now(pytz.timezone('US/Eastern'))
            start_date = end_date - timedelta(days=5*365)  # 5 years
            
            self.logger.info(f"Fetching data for {ticker}")
            data = self.alpaca_client.fetch_historical_data(
                ticker,
                start_date,
                end_date,
                timeframe='1Day'
            )
            
            if not data.empty:
                self.logger.info(f"Storing {len(data)} records for {ticker}")
                self._save_historical_data(ticker, data)
                self.logger.info(f"Successfully stored data for {ticker}")
            else:
                self.logger.warning(f"No data received for {ticker}")
                
            return data
        except Exception as e:
            self.logger.error(f"Error in fetch_historical_data for {ticker}: {e}")
            raise
