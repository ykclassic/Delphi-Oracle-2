import pandas as pd
import logging

def run_monte_carlo():
    # Example: df = pd.read_csv('execution/trade_log.csv')
    # ... your existing data loading logic here ...

    # 1. Prevent crash if the dataset is entirely empty
    if df.empty:
        logging.warning("Monte Carlo: Dataset is empty. No trades to simulate.")
        return

    # 2. Defensively check for the column name to prevent KeyError
    if 'Outcome' not in df.columns:
        # Check for common alternative column names and standardize them
        if 'status' in df.columns:
            df.rename(columns={'status': 'Outcome'}, inplace=True)
        elif 'Result' in df.columns:
            df.rename(columns={'Result': 'Outcome'}, inplace=True)
        else:
            logging.error(f"Monte Carlo Error: 'Outcome' column missing. Available columns: {df.columns.tolist()}")
            return

    # 3. Filter safely now that the column is guaranteed to exist
    completed_trades = df[df['Outcome'].isin(['✅ TAKE PROFIT', '❌ STOP LOSS'])]
    
    if completed_trades.empty:
        logging.warning("Monte Carlo: No completed trades found for simulation.")
        return

    # ... rest of your Monte Carlo math ...
