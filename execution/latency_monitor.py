import MetaTrader5 as mt5
import time
import logging

class LatencyMonitor:
    def __init__(self, max_acceptable_ping_ms=150):
        self.max_ping = max_acceptable_ping_ms

    def measure_execution_delay(self, symbol):
        """Measures the exact round-trip time to the broker's server."""
        if not mt5.terminal_info():
            logging.error("MT5 Terminal not connected.")
            return False, 999.9

        # Start the stopwatch
        start_time = time.perf_counter()
        
        # Request a single tick (forces a round-trip to the broker server)
        tick = mt5.symbol_info_tick(symbol)
        
        # Stop the stopwatch
        end_time = time.perf_counter()
        
        if tick is None:
            return False, 999.9

        # Calculate milliseconds
        latency_ms = (end_time - start_time) * 1000
        
        if latency_ms > self.max_ping:
            logging.warning(f"⚠️ LATENCY SPIKE: {latency_ms:.2f}ms. Trade Blocked to prevent slippage.")
            return False, latency_ms
            
        logging.info(f"⚡ Connection optimal. Latency: {latency_ms:.2f}ms")
        return True, latency_ms

# Quick standalone test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mt5.initialize()
    monitor = LatencyMonitor()
    monitor.measure_execution_delay("EURUSD")
    mt5.shutdown()
