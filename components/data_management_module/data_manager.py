# components/data_management_module/data_manager.py

import pandas as pd
import threading
import logging
from datetime import datetime, timedelta, time
import time as time_module  # to avoid conflict with datetime.time
from pathlib import Path
from .config import config
from .alpaca_api import AlpacaAPIClient
from .data_access_layer import db_manager, Ticker, HistoricalData
from .real_time_data import RealTimeDataStreamer
import pytz
from dateutil.relativedelta import relativedelta  # for accurate date calculations
from sqlalchemy.exc import IntegrityError        # for handling database integrity errors
import traceback         
from datetime import datetime, timedelta
import threading


class DataManager:
    """Main class for managing market data operations"""

    def __init__(self):
        self.logger = self._setup_logging()
        self.api_client = AlpacaAPIClient()
        self.lock = threading.RLock()
        self.load_tickers()
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
    
    def load_tickers(self):
        """Load tickers from the tickers file."""
        tickers_file = Path(config.get('DEFAULT', 'tickers_file'))
        if not tickers_file.exists():
            self.logger.error(f"Tickers file not found: {tickers_file}")
            raise FileNotFoundError(f"Tickers file not found: {tickers_file}")
        
        with open(tickers_file, 'r') as f:
            self.tickers = [line.strip() for line in f if line.strip()]
        self.logger.info(f"Loaded {len(self.tickers)} tickers: {self.tickers}")

    # def _load_tickers(self):
    #     """Load tickers from the configured CSV file"""
    #     try:
    #         tickers_file = Path(config.get('DEFAULT', 'tickers_file'))
    #         if not tickers_file.exists():
    #             self.logger.error(f"Tickers file not found: {tickers_file}")
    #             raise FileNotFoundError(f"Tickers file not found: {tickers_file}")
                
    #         df = pd.read_csv(tickers_file)
    #         if 'ticker' not in df.columns:
    #             raise ValueError("CSV file must contain a 'ticker' column")
                
    #         tickers = df['ticker'].unique().tolist()
    #         self.logger.info(f"Loaded {len(tickers)} tickers")
    #         return tickers
    #     except Exception as e:
    #         self.logger.error(f"Failed to load tickers: {str(e)}")
    #         raise
        
    # def reload_tickers(self):
    #     """Reload tickers from the tickers file dynamically."""
    #     with self.lock:
    #         self.load_tickers()
    #         print("Tickers reloaded.")


    def initialize_database(self):
        """Initialize database with historical data"""
        try:
            with self.lock:
                print(f"CRITICAL DEBUG: Starting database initialization")
                ny_tz = pytz.timezone('America/New_York')
                end_date = datetime.now(ny_tz)
                
                for ticker in self.tickers:
                    print(f"CRITICAL DEBUG: Processing ticker {ticker}")
                    # Get the last record timestamp
                    last_timestamp = self.get_last_record_timestamp(ticker)
                    
                    if last_timestamp:
                        # If we have data, start from the last record
                        # Add a small buffer (1 bar) to ensure we don't miss any data
                        start_date = last_timestamp - timedelta(minutes=5)
                        print(f"CRITICAL DEBUG: Found last record for {ticker}, starting from {start_date}")
                        print(f"CRITICAL DEBUG: Start date timezone info: {start_date.tzinfo}")
                    else:
                        # If no existing data, fetch historical data for configured years
                        years = config.get_int('DEFAULT', 'historical_data_years')
                        start_date = end_date - relativedelta(years=years)  # Will inherit timezone from end_date
                        print(f"CRITICAL DEBUG: No existing data for {ticker}, fetching {years} years of history")
                        print(f"CRITICAL DEBUG: Start date timezone info: {start_date.tzinfo}")

                    # Print the date range for debugging
                    print(f"CRITICAL DEBUG: Date range from {start_date} to {end_date}")
                    print(f"CRITICAL DEBUG: End date timezone info: {end_date.tzinfo}")

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
                        print(f"CRITICAL DEBUG: Saved {len(historical_data)} records for {ticker}")
                    else:
                        print(f"CRITICAL DEBUG: No data to save for {ticker}")

                    # Respect rate limits
                    time_module.sleep(1)  # Ensure 'time_module' is correctly imported

                print("CRITICAL DEBUG: Database initialization completed")

        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            print(f"CRITICAL DEBUG: Error during initialization: {str(e)}")
            raise

                    
    def _filter_market_hours(self, data, timezone):
        """Filter data to only include market hours (9:30 AM to 4:00 PM EST)"""
        market_open = time(9, 30)    # Corrected from datetime_time(9, 30)
        market_close = time(16, 0)   # Corrected from datetime_time(16, 0)
        data = data.tz_convert(timezone)
        data = data.between_time(market_open, market_close)
        return data


    def fetch_historical_data_for_ticker(self, ticker_symbol):
        """Fetch and store historical data for a single ticker."""
        try:
            with self.lock:
                ny_tz = pytz.timezone('America/New_York')
                end_date = datetime.now(ny_tz)
                years = config.get_int('DEFAULT', 'historical_data_years')
                start_date = end_date - relativedelta(years=years)

                self.logger.info(f"Fetching historical data for {ticker_symbol}")

                historical_data = self.api_client.fetch_historical_data(
                    ticker_symbol, start_date, end_date, timeframe='5Min'
                )

                if not historical_data.empty:
                    historical_data = self._filter_market_hours(historical_data, ny_tz)
                    self._save_historical_data(ticker_symbol, historical_data)
                    self.logger.info(f"Historical data for {ticker_symbol} fetched and stored.")
                    print(f"Historical data for {ticker_symbol} fetched and stored.")
                else:
                    self.logger.warning(f"No historical data fetched for {ticker_symbol}")
                    print(f"No historical data fetched for {ticker_symbol}")
        except Exception as e:
            self.logger.error(f"Error fetching data for {ticker_symbol}: {str(e)}")
            print(f"Error fetching data for {ticker_symbol}: {str(e)}")
        
    def fetch_historical_data_async(self, ticker_symbol):
        """Fetch historical data for a ticker asynchronously."""
        threading.Thread(target=self.fetch_historical_data_for_ticker, args=(ticker_symbol,)).start()

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
            if (self._last_maintenance is None or 
                (current_time - self._last_maintenance).total_seconds() > 86400):
                
                # Disable the cleanup to retain all data
                # db_manager.cleanup_old_data()
                
                # Verify data continuity for all tickers
                for ticker in self.tickers:
                    self.verify_data_continuity(ticker)
                
                self._last_maintenance = current_time
                self.logger.info("Performed maintenance without data cleanup")
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
        
    def fetch_historical_data_for_ticker(self, ticker_symbol):
        """Fetch and store historical data for a single ticker."""
        try:
            with self.lock:
                ny_tz = pytz.timezone('America/New_York')
                end_date = datetime.now(ny_tz)
                
                # Get the last record timestamp
                last_timestamp = self.get_last_record_timestamp(ticker_symbol)
                
                if last_timestamp:
                    # If we have data, start from the last record
                    # Add a small buffer (1 bar) to ensure we don't miss any data
                    start_date = last_timestamp - timedelta(minutes=5)
                    self.logger.info(f"Fetching data for {ticker_symbol} from last record: {start_date}")
                    print(f"Fetching data for {ticker_symbol} from last record: {start_date}")
                else:
                    # If no existing data, fetch historical data for configured years
                    years = config.get_int('DEFAULT', 'historical_data_years')
                    start_date = end_date - relativedelta(years=years)
                    self.logger.info(f"No existing data found. Fetching {years} years of historical data for {ticker_symbol}")
                    print(f"No existing data found. Fetching {years} years of historical data for {ticker_symbol}")

                self.logger.info(f"Fetching historical data for {ticker_symbol}")

                historical_data = self.api_client.fetch_historical_data(
                    ticker_symbol, start_date, end_date, timeframe='5Min'
                )

                if not historical_data.empty:
                    historical_data = self._filter_market_hours(historical_data, ny_tz)
                    self._save_historical_data(ticker_symbol, historical_data)
                    self.logger.info(f"Historical data for {ticker_symbol} fetched and stored.")
                    print(f"Historical data for {ticker_symbol} fetched and stored.")
                else:
                    self.logger.warning(f"No historical data fetched for {ticker_symbol}")
                    print(f"No historical data fetched for {ticker_symbol}")
                    
        except Exception as e:
            self.logger.error(f"Error fetching data for {ticker_symbol}: {str(e)}")
            print(f"Error fetching data for {ticker_symbol}: {str(e)}")

    def fetch_historical_data_async(self, ticker_symbol):
        """Fetch historical data for a ticker asynchronously."""
        threading.Thread(target=self.fetch_historical_data_for_ticker, args=(ticker_symbol,)).start()
        
    def add_new_ticker(self, ticker_symbol):
        """Add a new ticker, reload tickers, and fetch historical data."""
        tickers_file = config.get('DEFAULT', 'tickers_file')
        ticker_added = append_ticker_to_csv(ticker_symbol, tickers_file)
        if ticker_added:
            self.reload_tickers()
            self.fetch_historical_data_async(ticker_symbol)
            # Update the real-time streamer
            if self.real_time_streamer:
                self.real_time_streamer.update_tickers(self.tickers)
            print(f"Ticker {ticker_symbol} added and data retrieval initiated.")
        else:
            print(f"Ticker {ticker_symbol} was not added.")
            
    def get_last_record_timestamp(self, ticker_symbol):
        """Get the timestamp of the last record for a ticker in the database"""
        session = db_manager.Session()
        try:
            last_record = session.query(HistoricalData)\
                .filter_by(ticker_symbol=ticker_symbol)\
                .order_by(HistoricalData.timestamp.desc())\
                .first()
            
            if last_record:
                # Make sure the timestamp is timezone-aware
                ny_tz = pytz.timezone('America/New_York')
                if last_record.timestamp.tzinfo is None:
                    aware_timestamp = ny_tz.localize(last_record.timestamp)
                else:
                    aware_timestamp = last_record.timestamp.astimezone(ny_tz)
                
                self.logger.info(f"Found last record for {ticker_symbol} at {aware_timestamp}")
                print(f"CRITICAL DEBUG: Found last record for {ticker_symbol} at {aware_timestamp}")
                print(f"CRITICAL DEBUG: Timestamp timezone info: {aware_timestamp.tzinfo}")
                return aware_timestamp
            else:
                self.logger.info(f"No existing records found for {ticker_symbol}")
                print(f"CRITICAL DEBUG: No existing records found for {ticker_symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting last record timestamp for {ticker_symbol}: {str(e)}")
            print(f"CRITICAL DEBUG: Error getting last record timestamp: {str(e)}")
            raise
        finally:
            session.close()
            
    def verify_data_continuity(self, ticker):
        """Verify there are no gaps in the data and fetch missing data if needed"""
        try:
            last_timestamp = self.get_last_record_timestamp(ticker)
            if last_timestamp:
                current_time = datetime.now(pytz.timezone('America/New_York'))
                # Check if we've missed any data (gap larger than 5 minutes during market hours)
                if (current_time - last_timestamp).total_seconds() > 300:  # 5 minutes
                    self.logger.info(f"Data gap detected for {ticker}, fetching missing data")
                    self.fetch_historical_data_for_ticker(ticker)
        except Exception as e:
            self.logger.error(f"Error verifying data continuity for {ticker}: {str(e)}")
            raise
            
            

