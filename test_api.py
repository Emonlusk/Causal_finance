"""
Comprehensive API Test Suite for Causal Finance Platform
Tests all major endpoints and features
"""
import requests
import json
import time
import sys

BASE_URL = "http://localhost:5000"
TOKEN = None
RESULTS = {"passed": 0, "failed": 0, "errors": []}

def test(name, method, endpoint, expected_status=200, body=None, headers=None, allow_statuses=None):
    """Run a single API test"""
    global TOKEN
    url = f"{BASE_URL}{endpoint}"
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    if TOKEN:
        hdrs["Authorization"] = f"Bearer {TOKEN}"
    
    try:
        if method == "GET":
            r = requests.get(url, headers=hdrs, timeout=30)
        elif method == "POST":
            r = requests.post(url, json=body, headers=hdrs, timeout=30)
        elif method == "PUT":
            r = requests.put(url, json=body, headers=hdrs, timeout=30)
        elif method == "DELETE":
            r = requests.delete(url, headers=hdrs, timeout=30)
        
        ok_statuses = allow_statuses or [expected_status]
        if r.status_code in ok_statuses:
            RESULTS["passed"] += 1
            print(f"  ✓ {name} [{r.status_code}]")
            try:
                return r.json()
            except:
                return {}
        else:
            RESULTS["failed"] += 1
            try:
                detail = r.json()
            except:
                detail = r.text[:200]
            RESULTS["errors"].append(f"{name}: expected {ok_statuses}, got {r.status_code} - {detail}")
            print(f"  ✗ {name} [{r.status_code}] - {detail}")
            return None
    except Exception as e:
        RESULTS["failed"] += 1
        RESULTS["errors"].append(f"{name}: {str(e)}")
        print(f"  ✗ {name} [ERROR] - {e}")
        return None

# ===== HEALTH CHECK =====
print("\n" + "="*60)
print("SECTION 1: HEALTH CHECK")
print("="*60)
test("Health check", "GET", "/api/health")

# ===== AUTH =====
print("\n" + "="*60)
print("SECTION 2: AUTHENTICATION")
print("="*60)

ts = str(int(time.time()))
username = f"apitest_{ts}"
email = f"apitest_{ts}@test.com"
password = "SecurePass123!"

# Register
reg = test("Register new user", "POST", "/api/auth/register", 201, 
           body={"username": username, "email": email, "password": password})

# Login
login = test("Login", "POST", "/api/auth/login", 200,
             body={"email": email, "password": password})
if login:
    TOKEN = login.get("access_token") or login.get("token")
    print(f"    Token received: {'Yes' if TOKEN else 'No'}")

# Login with wrong password
test("Login wrong password", "POST", "/api/auth/login", 401,
     body={"email": email, "password": "wrong"})

# Get profile (requires auth)
if TOKEN:
    test("Get user profile", "GET", "/api/auth/profile", allow_statuses=[200, 404])

# ===== MARKET DATA =====
print("\n" + "="*60)
print("SECTION 3: MARKET DATA")
print("="*60)

# Market indicators
test("Get market indicators", "GET", "/api/market/indicators")

# Stock quote
test("Get stock quote (AAPL)", "GET", "/api/market/quote/AAPL")
test("Get stock quote (NVDA)", "GET", "/api/market/quote/NVDA")
test("Get stock quote (INVALID_TICKER)", "GET", "/api/market/quote/ZZZZZ", 
     allow_statuses=[200, 404])

# Sector performance
test("Sector performance (1M)", "GET", "/api/market/sectors?period=1M")
test("Sector performance (1Y)", "GET", "/api/market/sectors?period=1Y")

# FRED / macro data
test("Get FRED data (all)", "GET", "/api/market/macro")
test("Get FRED data (fed rate)", "GET", "/api/market/macro?series=FEDFUNDS",
     allow_statuses=[200, 404])

# Stock search
test("Search stocks (AAPL)", "GET", "/api/market/search?q=AAPL",
     allow_statuses=[200, 404])

# Benchmark
test("Get benchmark data", "GET", "/api/market/benchmark",
     allow_statuses=[200, 404])

# ===== PORTFOLIOS =====
print("\n" + "="*60)
print("SECTION 4: PORTFOLIOS")
print("="*60)

if TOKEN:
    # Create portfolio
    portfolio_data = {
        "name": f"Test Portfolio {ts}",
        "description": "API test portfolio",
        "holdings": [
            {"symbol": "AAPL", "weight": 0.3},
            {"symbol": "MSFT", "weight": 0.3},
            {"symbol": "GOOGL", "weight": 0.2},
            {"symbol": "NVDA", "weight": 0.2}
        ]
    }
    port = test("Create portfolio", "POST", "/api/portfolios/", 
                allow_statuses=[200, 201], body=portfolio_data)
    
    portfolio_id = None
    if port:
        portfolio_id = port.get("id") or port.get("portfolio", {}).get("id")
        print(f"    Portfolio ID: {portfolio_id}")
    
    # List portfolios
    test("List portfolios", "GET", "/api/portfolios/")
    
    # Get specific portfolio
    if portfolio_id:
        test("Get portfolio detail", "GET", f"/api/portfolios/{portfolio_id}")
        test("Get portfolio holdings", "GET", f"/api/portfolios/{portfolio_id}/holdings",
             allow_statuses=[200, 404])
    
    # Optimize portfolio
    opt_data = {
        "symbols": ["AAPL", "MSFT", "GOOGL", "NVDA", "JPM", "JNJ"],
        "objective": "max_sharpe",
        "risk_tolerance": 0.5
    }
    test("Optimize portfolio (max_sharpe)", "POST", "/api/portfolios/optimize",
         allow_statuses=[200, 201], body=opt_data)
    
    opt_data2 = {
        "symbols": ["AAPL", "MSFT", "GOOGL", "NVDA"],
        "risk_tolerance": 0.2
    }
    test("Optimize portfolio (low risk)", "POST", "/api/portfolios/optimize",
         allow_statuses=[200, 201], body=opt_data2)
    
    opt_data3 = {
        "symbols": ["AAPL", "MSFT", "GOOGL", "NVDA"],
        "risk_tolerance": 0.9
    }
    test("Optimize portfolio (high risk)", "POST", "/api/portfolios/optimize",
         allow_statuses=[200, 201], body=opt_data3)
else:
    print("  ⚠ Skipping portfolio tests (no auth token)")

# ===== CAUSAL ANALYSIS =====
print("\n" + "="*60)
print("SECTION 5: CAUSAL ANALYSIS")
print("="*60)

# Discover causal relationships
test("Discover causal relationships", "POST", "/api/causal/discover",
     allow_statuses=[200, 201], body={"method": "granger", "sectors": ["XLK", "XLF", "XLE"]})

# Treatment effects
test("Estimate treatment effect", "POST", "/api/causal/treatment-effect",
     allow_statuses=[200, 201], body={
         "treatment": "interest_rates",
         "outcome": "XLK",
         "treatment_value": 0.5
     })

# Causal DAG
test("Get causal DAG", "GET", "/api/causal/dag", allow_statuses=[200, 404])

# What-if analysis
test("What-if analysis", "POST", "/api/causal/what-if",
     allow_statuses=[200, 201, 404], body={
         "variable": "interest_rate",
         "change": 0.25,
         "target_sectors": ["XLK", "XLF"]
     })

# ===== ML ENDPOINTS =====
print("\n" + "="*60)
print("SECTION 6: ML & FORECASTING")
print("="*60)

# ML status
test("ML model status", "GET", "/api/ml/status", allow_statuses=[200, 404])

# Sensitivity matrix
test("Sensitivity matrix", "GET", "/api/ml/sensitivity-matrix", allow_statuses=[200, 404])

# Forecast
test("Forecast (XLK)", "POST", "/api/ml/forecast",
     allow_statuses=[200, 201, 404], body={
         "sector": "XLK",
         "horizon": 30,
         "model": "arima"
     })

# Regime detection
test("Detect market regime", "GET", "/api/ml/regime", allow_statuses=[200, 404])

# DAG visualization
test("ML DAG visualization", "GET", "/api/ml/dag", allow_statuses=[200, 404])

# ===== SCENARIOS =====
print("\n" + "="*60)
print("SECTION 7: SCENARIOS")
print("="*60)

if TOKEN:
    # Run scenario with portfolio weights
    scenario_data = {
        "name": "Rate Hike Test",
        "scenario_type": "interest_rate_hike",
        "parameters": {"interest_rates": {"change": 0.5}},
        "portfolio_weights": {"XLK": 0.3, "XLF": 0.3, "XLE": 0.2, "XLV": 0.2}
    }
    test("Run scenario (rate hike)", "POST", "/api/scenarios/run",
         allow_statuses=[200, 201], body=scenario_data)
    
    # Market crash scenario
    crash_data = {
        "name": "Market Crash Test",
        "scenario_type": "market_crash",
        "parameters": {"equity_shock": {"change": -0.30}},
        "portfolio_weights": {"XLK": 0.25, "XLF": 0.25, "XLE": 0.25, "XLV": 0.25}
    }
    test("Run scenario (market crash)", "POST", "/api/scenarios/run",
         allow_statuses=[200, 201], body=crash_data)
    
    # List saved scenarios
    test("List scenarios", "GET", "/api/scenarios/", allow_statuses=[200, 404])
else:
    print("  ⚠ Skipping scenario tests (no auth token)")

# ===== USER ENDPOINTS =====
print("\n" + "="*60)
print("SECTION 8: USER MANAGEMENT")
print("="*60)

if TOKEN:
    test("Get user activity", "GET", "/api/users/activity", allow_statuses=[200, 404])
    test("Get user dashboard", "GET", "/api/users/dashboard", allow_statuses=[200, 404])
    test("Update user preferences", "PUT", "/api/users/preferences",
         allow_statuses=[200, 404], body={"theme": "dark", "risk_profile": "moderate"})

# ===== LOGOUT =====
print("\n" + "="*60)
print("SECTION 9: LOGOUT")
print("="*60)

if TOKEN:
    test("Logout", "POST", "/api/auth/logout", allow_statuses=[200, 204])
    # Verify token is revoked
    test("Access after logout (should fail)", "GET", "/api/portfolios/", 
         allow_statuses=[401, 422])

# ===== SUMMARY =====
print("\n" + "="*60)
print(f"TEST RESULTS: {RESULTS['passed']} passed, {RESULTS['failed']} failed")
print("="*60)

if RESULTS["errors"]:
    print("\nFailed tests:")
    for err in RESULTS["errors"]:
        print(f"  ✗ {err}")

sys.exit(0 if RESULTS["failed"] == 0 else 1)
