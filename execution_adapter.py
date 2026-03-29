import MetaTrader5 as mt5
import logging

class HeadwayExecutor:
    def __init__(self, config):
        """Initializes the connection to Headway MT5 terminal."""
        self.config = config
        self.account = int(config['execution']['account'])
        self.password = config['execution']['password']
        self.server = config['execution']['server']

        if not mt5.initialize():
            logging.error(f"MT5 Init failed: {mt5.last_error()}")
            return

        # Attempt Login
        authorized = mt5.login(self.account, password=self.password, server=self.server)
        if authorized:
            logging.info(f"✅ Connected to Headway Account: {self.account}")
        else:
            logging.error(f"❌ Login failed: {mt5.last_error()}")

    def execute_trade(self, symbol, signal_data, risk_data):
        """Places a live trade on the Headway terminal."""
        
        # Determine Trade Type
        is_buy = "BUY" in signal_data['action']
        order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
        
        # Get Current Price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logging.error(f"Could not get tick for {symbol}")
            return False
            
        price = tick.ask if is_buy else tick.bid

        # Prepare Request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(risk_data.get('lots', 0.01)), # Adjusted for Cent/Pro account
            "type": order_type,
            "price": price,
            "sl": float(risk_data['sl']),
            "tp": float(risk_data['tp']),
            "magic": 202603,
            "comment": "Delphi Oracle PC-Native",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Send Trade
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Trade Failed: {result.comment} (Code: {result.retcode})")
            return False
            
        logging.info(f"🔥 TRADE PLACED: {symbol} {signal_data['action']} at {price}")
        return True

    def shutdown(self):
        mt5.shutdown()
