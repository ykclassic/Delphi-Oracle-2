import os
import time
from datetime import datetime

def get_file_age_days(filepath):
    """Returns how many days old a file is."""
    if not os.path.exists(filepath):
        return None
    file_stat = os.stat(filepath)
    age_seconds = time.time() - file_stat.st_mtime
    return age_seconds / (24 * 3600)

def check_brain_health(models_dir="models"):
    """Pillar 1: Checks if the ML models were retrained this weekend."""
    if not os.path.exists(models_dir):
        return "🔴 FAILED: 'models' directory not found."
    
    models = [f for f in os.listdir(models_dir) if f.endswith('.pkl')]
    if not models:
        return "🔴 FAILED: No ML models found. Retrainer has not run."
    
    # Check the age of the first model found
    age = get_file_age_days(os.path.join(models_dir, models[0]))
    if age > 7:
        return f"🟡 WARNING: Models are {age:.1f} days old. Weekend Retrainer missed a cycle."
    return f"🟢 OPTIMAL: Models updated {age:.1f} days ago."

def check_watchdog_status(safety_file="execution/safety.txt"):
    """Pillar 2: Checks if the latency monitor has triggered the Circuit Breaker."""
    if not os.path.exists(safety_file):
        # If file doesn't exist, assume no locks have been placed
        return "🟢 NOMINAL: No latency locks detected."
    
    with open(safety_file, "r") as f:
        status = f.read().strip()
        
    if status == "LOCKED":
        return "🔴 CRITICAL: Watchdog has LOCKED trading due to high latency!"
    return "🟢 NOMINAL: Connection latency is stable."

def check_audit_status(log_file="logs/trade_log.csv"):
    """Pillar 3: Checks if the Friday Audit has fresh data to process."""
    age = get_file_age_days(log_file)
    if age is None:
        return "⚪ N/A: No trade log generated yet."
    if age > 3:
        return f"🟡 IDLE: No trades taken in {age:.1f} days."
    return f"🟢 ACTIVE: Last trade logged {age:.1f} days ago."

def generate_dashboard():
    print("========================================")
    print("   🔮 DELPHI ORACLE: MISSION CONTROL")
    print(f"   Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("========================================\n")
    
    print("🧠 Pillar 1: ML Intelligence (Retrainer)")
    print(f"   Status: {check_brain_health()}\n")
    
    print("🛡️ Pillar 2: Execution Guard (Watchdog)")
    print(f"   Status: {check_watchdog_status()}\n")
    
    print("📊 Pillar 3: System Activity (Audit)")
    print(f"   Status: {check_audit_status()}\n")
    
    print("========================================")
    print("   SYSTEM EVALUATION: ", end="")
    
    # Simple logic to determine overall system readiness
    if "🔴" in check_brain_health() or "🔴" in check_watchdog_status():
        print("DO NOT TRADE 🛑")
    elif "🟡" in check_brain_health() or "🟡" in check_audit_status():
        print("PROCEED WITH CAUTION ⚠️")
    else:
        print("READY FOR EXECUTION 🚀")
    print("========================================")

if __name__ == "__main__":
    generate_dashboard()
