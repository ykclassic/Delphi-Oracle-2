import pandas as pd
import numpy as np
import os
import logging

def run_monte_carlo(simulations=10000, trades_per_sim=100, starting_balance=100.0, risk_pct=0.02):
    """Calculates the mathematical Risk of Ruin based on live bot data."""
    log_path = "logs/trade_log.csv"
    
    if not os.path.exists(log_path):
        print("No live trade data found. Run the bot in demo first to generate a track record.")
        return

    # 1. Extract real performance metrics from your app
    df = pd.read_csv(log_path)
    completed_trades = df[df['Outcome'].isin(['✅ TAKE PROFIT', '❌ STOP LOSS'])]
    
    if len(completed_trades) < 10:
        print("Not enough data. You need at least 10 completed trades for a valid simulation.")
        return

    wins = len(completed_trades[completed_trades['Outcome'] == '✅ TAKE PROFIT'])
    win_rate = wins / len(completed_trades)
    
    # 2. Run 10,000 Alternate Realities
    print(f"Running 10,000 simulations based on your {win_rate*100:.1f}% Win Rate...")
    
    ruined_accounts = 0
    drawdown_threshold = starting_balance * 0.50 # 50% Drawdown = Ruin
    
    for _ in range(simulations):
        balance = starting_balance
        
        # Generate an array of random probabilities (0.0 to 1.0) for 100 trades
        random_events = np.random.random(trades_per_sim)
        
        for event in random_events:
            risk_amount = balance * risk_pct
            if event <= win_rate:
                balance += (risk_amount * 2) # Win (Assuming 1:2 Risk-Reward)
            else:
                balance -= risk_amount       # Loss
                
            if balance <= drawdown_threshold:
                ruined_accounts += 1
                break # Account hit critical failure, end this simulation loop
                
    # 3. Output the verdict
    risk_of_ruin = (ruined_accounts / simulations) * 100
    
    print("\n--- 🎲 MONTE CARLO STRESS TEST VERDICT ---")
    print(f"Simulations Run:   {simulations:,}")
    print(f"Starting Balance:  ${starting_balance}")
    print(f"Risk Per Trade:    {risk_pct*100}%")
    print(f"Risk of Ruin:      {risk_of_ruin:.2f}% (Chance of losing 50% of your account)")
    
    if risk_of_ruin < 5.0:
        print("Status: INSTITUTIONAL GRADE 🛡️ (Safe to scale capital)")
    elif risk_of_ruin < 20.0:
        print("Status: ACCEPTABLE 🟡 (Monitor closely)")
    else:
        print("Status: HIGH RISK 🔴 (Do not increase capital. Adjust strategy.)")

if __name__ == "__main__":
    run_monte_carlo()
