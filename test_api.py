"""
Comprehensive API Test Suite for Causal Finance Platform
Tests all major endpoints and features
"""
import sys
import time
import requests

# Force UTF-8 stdout so this runs on a stock Windows console (cp1252) without
# needing PYTHONIOENCODING=utf-8 set externally - printing the pass/fail
# markers used to crash mid-run under the default codepage.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:5000"
TOKEN = None
RESULTS = {"passed": 0, "failed": 0, "errors": []}


def test(name, method, endpoint, expected_status=200, body=None, headers=None,
         allow_statuses=None, check=None, timeout=30):
    """Run a single API test.

    `check`, when given, is a callable(json_body) -> bool run only after the
    status code already passed. A 2xx response with the wrong shape (e.g. a
    404 masquerading as success, or a route that changed its contract) still
    fails the test - status code alone is not enough to call it a pass.
    """
    global TOKEN
    url = f"{BASE_URL}{endpoint}"
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    if TOKEN:
        hdrs["Authorization"] = f"Bearer {TOKEN}"

    try:
        if method == "GET":
            r = requests.get(url, headers=hdrs, timeout=timeout)
        elif method == "POST":
            r = requests.post(url, json=body, headers=hdrs, timeout=timeout)
        elif method == "PUT":
            r = requests.put(url, json=body, headers=hdrs, timeout=timeout)
        elif method == "DELETE":
            r = requests.delete(url, headers=hdrs, timeout=timeout)
        else:
            raise ValueError(f"Unsupported method: {method}")

        ok_statuses = allow_statuses or [expected_status]
        if r.status_code not in ok_statuses:
            RESULTS["failed"] += 1
            try:
                detail = r.json()
            except Exception:
                detail = r.text[:200]
            RESULTS["errors"].append(f"{name}: expected {ok_statuses}, got {r.status_code} - {detail}")
            print(f"  FAIL {name} [{r.status_code}] - {detail}")
            return None

        try:
            data = r.json()
        except Exception:
            data = {}

        if check is not None:
            try:
                shape_ok = check(data)
            except Exception as e:
                shape_ok = False
            if not shape_ok:
                RESULTS["failed"] += 1
                RESULTS["errors"].append(
                    f"{name}: status {r.status_code} OK but response shape check failed - {data}"
                )
                print(f"  FAIL {name} [{r.status_code}] (bad response shape) - {data}")
                return data

        RESULTS["passed"] += 1
        print(f"  PASS {name} [{r.status_code}]")
        return data

    except Exception as e:
        RESULTS["failed"] += 1
        RESULTS["errors"].append(f"{name}: {str(e)}")
        print(f"  FAIL {name} [ERROR] - {e}")
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

# Get current user (was hitting the wrong path, /api/auth/profile, and
# accepting a 404 as a pass; the real route is /api/auth/me)
if TOKEN:
    test("Get current user", "GET", "/api/auth/me",
         check=lambda d: isinstance(d, dict) and d.get("user", {}).get("email") == email)

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
    print("  (skipped) Skipping portfolio tests (no auth token)")

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

# ML health/status (was hitting the nonexistent /api/ml/status and
# accepting a 404 as a pass; the real status endpoint is /api/ml/health)
test("ML health check", "GET", "/api/ml/health",
     check=lambda d: d.get("success") is True and "ml_service" in d.get("status", {}))

# Sensitivity matrix (was hitting /api/ml/sensitivity-matrix, which doesn't
# exist - the real route is under /api/ml/causal/)
test("Sensitivity matrix", "GET", "/api/ml/causal/sensitivity-matrix",
     check=lambda d: d.get("success") is True and len(d.get("sensitivity_matrix", {})) > 0)

# Forecast (was POSTing a single-sector body to /api/ml/forecast, which
# doesn't exist - the real endpoint is GET /api/ml/forecast/all and returns
# every sector at once, no body)
test("Forecast all sectors", "GET", "/api/ml/forecast/all",
     check=lambda d: d.get("success") is True and len(d.get("forecasts", {})) > 0)

# Regime detection (was hitting /api/ml/regime, which doesn't exist - the
# real route is /api/ml/regime/current)
test("Detect market regime", "GET", "/api/ml/regime/current",
     check=lambda d: d.get("success") is True and "current_regime" in d.get("regime", {}))

# ML causal DAG (was hitting /api/ml/dag, which doesn't exist - the real
# route is /api/ml/causal/dag). This one runs PC + Granger causal discovery
# across every sector at once (~11 variables x 6000+ samples), which is a
# legitimately heavier computation (~25-30s) than the other endpoints here,
# so it gets a longer timeout rather than the default 30s.
test("ML causal DAG", "GET", "/api/ml/causal/dag", timeout=60,
     check=lambda d: d.get("success") is True and "nodes" in d.get("dag", {}))

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
    print("  (skipped) Skipping scenario tests (no auth token)")

# ===== USER ENDPOINTS =====
print("\n" + "="*60)
print("SECTION 8: USER MANAGEMENT")
print("="*60)

if TOKEN:
    # Was hitting /api/users/activity (singular), which doesn't exist - the
    # real route is /api/users/activities (plural)
    test("Get user activities", "GET", "/api/users/activities",
         check=lambda d: isinstance(d.get("activities"), list))

    # Was PUTting to /api/users/preferences, which doesn't exist. The real
    # settings route is /api/users/settings, and it's GET-only (there's no
    # endpoint that updates these fields directly - PUT /api/users/profile
    # covers risk_tolerance/investment fields instead).
    test("Get user settings", "GET", "/api/users/settings",
         check=lambda d: "risk_tolerance" in d.get("settings", {}))

    # There is no /api/users/dashboard route anywhere in the backend
    # (confirmed by reading every blueprint) - the old test accepted a 404
    # as a pass here, which just hid the fact this endpoint never existed.
    # Removed rather than asserting against something that isn't real.

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
        print(f"  FAIL {err}")

sys.exit(0 if RESULTS["failed"] == 0 else 1)
