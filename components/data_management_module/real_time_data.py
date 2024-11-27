# components/data_management_module/real_time_data.py

import zmq
import json
import threading
import logging
from datetime import datetime, timedelta
import asyncio
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL
from .config import config
from .data_access_layer import db_manager, HistoricalData
import pytz

class RealTimeDataStreamer:
    """Handles real-time market data streaming using ZeroMQ for internal distribution"""
    
    def __init__(self, tickers):
        self.logger = self._setup_logging()
        self.tickers = tickers
        
        # Initialize ZeroMQ context and sockets
        self.zmq_context = zmq.Context()
        self.publisher = self.zmq_context.socket(zmq.PUB)
        self.publisher.bind(f"tcp://*:{config.get('DEFAULT', 'zeromq_port')}")
        
        # Initialize Alpaca stream
        self.stream = Stream(
            config.get('api', 'key_id'),
            config.get('api', 'secret_key'),
            base_url=URL(config.get('api', 'base_url')),
            data_feed='sip'
        )
        
        self._running = False
        self._last_prices = {}
        self._last_update = {}
        self._interval = timedelta(minutes=5)

    def _setup_logging(self):
        """Set up logging for the real-time data streamer"""
        logger = logging.getLogger('realtime_data')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(config.get('DEFAULT', 'log_file'))
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    async def _is_market_hours(self):
        """Check if current time is within market hours"""
        ny_time = datetime.now(pytz.timezone('America/New_York'))
        market_open = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = ny_time.replace(hour=16, minute=0, second=0, microsecond=0)
        return market_open <= ny_time <= market_close

    async def handle_bar(self, bar):
        """Handle incoming bar data"""
        try:
            if not await self._is_market_hours():
                return

            current_time = datetime.now(pytz.UTC)
            last_update = self._last_update.get(bar.symbol)
            
            # Only process if 5 minutes have passed since last update
            if (last_update is None or 
                current_time - last_update >= self._interval):
                
                # Validate the data
                HistoricalData.validate_price_data(
                    bar.open, bar.high, bar.low, bar.close, bar.volume
                )
                
                # Store and publish
                await self._store_bar_data(bar)
                await self._publish_bar_data(bar)
                
                self._last_update[bar.symbol] = current_time
                self._last_prices[bar.symbol] = bar.close
                
        except Exception as e:
            self.logger.error(f"Error processing bar data: {str(e)}")

    def _store_bar_data(self, bar):
        """Store bar data in the database"""
        try:
            record = HistoricalData(
                ticker_symbol=bar.symbol,
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume
            )
            
            session = db_manager.Session()
            try:
                session.add(record)
                session.commit()
                self.logger.debug(f"Stored bar data for {bar.symbol}")
            finally:
                session.close()
                
        except Exception as e:
            self.logger.error(f"Failed to store bar data: {str(e)}")

    def _publish_bar_data(self, bar):
        """Publish bar data through ZeroMQ"""
        try:
            message = {
                'symbol': bar.symbol,
                'timestamp': bar.timestamp.isoformat(),
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume
            }
            
            topic = f"{config.get('DEFAULT', 'zeromq_topic')}.{bar.symbol}"
            self.publisher.send_string(f"{topic} {json.dumps(message)}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish bar data: {str(e)}")

    def start(self):
        """Start the real-time data streaming"""
        if self._running:
            self.logger.warning("Streamer is already running")
            return

        self._running = True
        self.logger.info("Starting real-time data streaming")
        
        # Subscribe to bars for all tickers
        for ticker in self.tickers:
            self.stream.subscribe_bars(self.handle_bar, ticker)
            self.logger.info(f"Subscribed to bars for {ticker}")

        # Start the stream in a separate thread
        try:
            self.stream_thread = threading.Thread(target=self._run_stream, daemon=True)
            self.stream_thread.start()
        except Exception as e:
            self._running = False
            self.logger.error(f"Stream error: {str(e)}")
            raise

    def _run_stream(self):
        """Run the stream in the event loop"""
        try:
            self.stream.run()
        except Exception as e:
            self._running = False
            self.logger.error(f"Stream encountered an error: {str(e)}")

    def stop(self):
        """Stop the real-time data streaming"""
        if not self._running:
            return

        self._running = False
        try:
            self.stream.stop()
            if hasattr(self, 'stream_thread') and self.stream_thread.is_alive():
                self.stream_thread.join(timeout=5)
            self.publisher.close()
            self.zmq_context.term()
            self.logger.info("Stopped real-time data streaming")
        except Exception as e:
            self.logger.error(f"Error stopping stream: {str(e)}")
