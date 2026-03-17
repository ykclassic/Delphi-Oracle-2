import MetaTrader5 as mt5
import yaml
import os

def verify_all_connections(config_path="settings.yaml"):
    """
    Programmatic Verification Module for Delphi Oracle.
    Iterates through all accounts in settings.yaml and attempts a secure login.
    """
    # 1. Load the Configuration
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
    except Exception as e:
        print(f"❌ Error loading {config_path}: {e}")
        return

    print(f"--- 🔮 {config['bot_name']} Connection Audit ---")
    
    # 2. Initialize MT5 Engine
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed. Error: {mt5.last_error()}")
        return

    # 3. Iterate and Verify Each Account
    for account in config.get('accounts', []):
        if not account.get('enabled'):
            print(f"⚪ {account['name']}: Skipped (Enabled: False)")
            continue

        # Extract environment variables (Security Rule Compliance)
        # Note: If running locally, ensure these match your .env or OS variables
        raw_password = os.getenv(account['password'].replace("${", "").replace("}", ""))
        
        # Fallback for debugging (Remove in production)
        if not raw_password and account['name'] == "Octa_Demo":
             raw_password = "by5uQuDu" 

        print(f"🔄 Attempting connection: {account['name']} ({account['server']})...")
        
        authorized = mt5.login(
            login=int(account['login']),
            password=raw_password,
            server=account['server']
        )

        if authorized:
            acc_info = mt5.account_info()
            print(f"✅ {account['name']} CONNECTED")
            print(f"   - Balance: {acc_info.balance} {acc_info.currency}")
            print(f"   - Leverage: 1:{acc_info.leverage}")
            print(f"   - Margin Level: {acc_info.margin_level}%")
        else:
            error = mt5.last_error()
            print(f"🔴 {account['name']} FAILED. Error Code: {error}")

    # 4. Shutdown MT5 to release resources
    mt5.shutdown()
    print("------------------------------------------")

if __name__ == "__main__":
    verify_all_connections()
