# QA Audit Report v2 - Multi-User Authentication & Wallet System

**Date:** 2026-04-28
**Auditor:** QA Expert Agent
**Scope:** Auth, encryption, wallet management, route protection, frontend token handling
**Test Results:** 72/72 existing tests PASS (no auth/wallet tests exist yet)

---

## Summary Verdict: BLOCKED -- 4 Critical, 6 High, 5 Medium, 3 Low

The multi-user auth and wallet system has a solid architectural foundation but contains critical integration bugs that will cause runtime failures. The system must not ship until criticals are resolved.

---

## CRITICAL (must fix before merge)

### C1. Frontend-Backend API Contract Mismatch -- Login/Register Returns Wrong Field Name

**Files:**
- `/workspace/RSITradingBot/RSITradingBot/frontend/src/types/index.ts` (line 10)
- `/workspace/RSITradingBot/RSITradingBot/frontend/src/api/auth.ts` (line 9)
- `/workspace/RSITradingBot/RSITradingBot/frontend/src/store/useAuthStore.ts` (line 22)
- `/workspace/RSITradingBot/RSITradingBot/backend/app/api/v1/routes/auth.py` (lines 31-43)

**Description:** The frontend `AuthResponse` type expects `{ token: string; user: User }`. The backend `/v1/auth/login` returns `{ access_token: string; token_type: string }` (no `user` field). The backend `/v1/auth/register` returns `{ user_id: string; email: string }` (no `token` or `user` field at all).

**Impact:** Login and registration will fail at runtime. The store does `res.token` which will be `undefined`, and `res.user` which will also be `undefined`. The user will be "logged in" with no valid token, causing all subsequent API calls to 401.

**Evidence:**
```
// Frontend expects:
export interface AuthResponse { token: string; user: User; }

// Backend login actually returns:
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

// Backend register actually returns:
class RegisterResponse(BaseModel):
    user_id: str
    email: str
```

**Fix:** Either align the frontend types to match the backend, or change the backend to return `{ token, user }` on both login and register.

---

### C2. Wallet Route Accepts String `wallet_id` Without UUID Validation

**File:** `/workspace/RSITradingBot/RSITradingBot/backend/app/api/v1/routes/wallets.py` (lines 95-113, 116-132)

**Description:** The `deactivate_wallet` and `get_wallet_balance` endpoints accept `wallet_id: str` as a path parameter and pass it directly into SQLAlchemy `Wallet.id == wallet_id`. The `Wallet.id` column is `UUID(as_uuid=True)`. Passing an arbitrary string that is not a valid UUID will cause an unhandled database error (DataError) rather than a clean 400/404.

**Impact:** Malformed UUIDs cause 500 Internal Server Error instead of 400 Bad Request. This also opens potential for unexpected query behavior.

**Fix:** Validate `wallet_id` as a UUID early in the handler:
```python
try:
    wallet_uuid = uuid.UUID(wallet_id)
except ValueError:
    raise HTTPException(status_code=400, detail="Invalid wallet ID format")
```
Then use `wallet_uuid` in the query.

---

### C3. `encryption_key` Default is Empty String -- Wallet Operations Will Crash at Runtime

**File:** `/workspace/RSITradingBot/RSITradingBot/backend/app/config.py` (line 47)

**Description:** `encryption_key: str = ""` with no validation. When `connect_wallet` is called, `encrypt_private_key` calls `bytes.fromhex("")` which raises `ValueError: non-hexadecimal number found in fromhex() arg at position 0`. This is an unhandled 500 error.

**Impact:** Any user attempting to connect a wallet in development (or any environment where ENCRYPTION_KEY is not set) gets a 500 crash.

**Fix:** Add a startup validation that `encryption_key` is a valid 64-character hex string, or at minimum add a guard in the wallet route before calling encrypt. Consider using a Pydantic validator on the Settings model.

---

### C4. AI Route Missing Authentication -- Unauthenticated Access to AI Classification

**File:** `/workspace/RSITradingBot/RSITradingBot/backend/app/api/v1/routes/ai.py` (lines 31-32)

**Description:** The `classify_exception` endpoint does not include `current_user: User = Depends(get_current_user)`. It is mounted at `/v1/ai/exceptions/classify` and is fully accessible without any JWT token.

**Impact:** Any anonymous user can call the AI classification endpoint, potentially abusing the z.ai API key and incurring costs. This violates the requirement that all user-specific routes enforce JWT auth.

**Fix:** Add authentication dependency to the endpoint.

---

## HIGH (should fix before merge)

### H1. `docker-compose.yml` Still Contains `HYPERLIQUID_PRIVATE_KEY` and `HYPERLIQUID_ACCOUNT_ADDRESS`

**File:** `/workspace/RSITradingBot/RSITradingBot/docker-compose.yml` (lines 55-56)

**Description:** The docker-compose passes `HYPERLIQUID_PRIVATE_KEY` and `HYPERLIQUID_ACCOUNT_ADDRESS` as environment variables to the backend container. These are per-user credentials that should not exist in global config now that the multi-user wallet system exists. The `config.py` does not read these fields, so they are harmless dead config, but their presence is confusing and violates the stated requirement.

**Impact:** Misleading configuration that could lead to accidental use of single-user mode. Also a potential security concern if someone puts a real key in the host `.env`.

**Fix:** Remove both lines from docker-compose.yml.

---

### H2. No Password Strength Validation on Backend

**File:** `/workspace/RSITradingBot/RSITradingBot/backend/app/api/v1/routes/auth.py` (lines 53-67)

**Description:** The register endpoint accepts any non-empty string as a password. While the frontend validates `password.length >= 8`, the backend has zero validation. An API client can register with a 1-character password.

**Impact:** Weak passwords accepted via direct API calls, bypassing frontend validation.

**Fix:** Add Pydantic field validation or explicit password length/complexity check in the register handler.

---

### H3. No Rate Limiting on Auth Endpoints

**Files:** `/workspace/RSITradingBot/RSITradingBot/backend/app/api/v1/routes/auth.py`

**Description:** No rate limiting on `/register` or `/login`. These are high-value targets for brute force attacks and account enumeration.

**Impact:** Attackers can brute-force passwords or mass-register accounts without throttling.

**Fix:** Add rate limiting middleware (e.g., `slowapi`) or reverse-proxy level rate limiting.

---

### H4. `SECRET_KEY` Has an Insecure Default

**File:** `/workspace/RSITradingBot/RSITradingBot/backend/app/config.py` (line 46)

**Description:** `secret_key: str = "change-me-to-random-string"` is the default. If deployed without changing it, all JWTs are trivially forgeable.

**Impact:** Complete auth bypass if the secret key is not overridden in production.

**Fix:** Either set the default to empty string and fail fast on startup if not set in production, or add a startup check.

---

### H5. Registration Does Not Auto-Login (Frontend Expects Token)

**File:** `/workspace/RSITradingBot/RSITradingBot/backend/app/api/v1/routes/auth.py` (lines 53-67)
**File:** `/workspace/RSITradingBot/RSITradingBot/frontend/src/store/useAuthStore.ts` (lines 26-29)

**Description:** The backend `/register` returns `{ user_id, email }` with no JWT token. The frontend store's `register` method does `localStorage.setItem("token", res.token)` where `res.token` is `undefined`. The user would be in a broken state -- `isAuthenticated` is `true` but no valid token exists.

**Impact:** After registration, the user appears logged in but cannot make any API calls. They must manually navigate to login and re-authenticate.

**Fix:** Either have register also return a JWT, or change the frontend flow to redirect to the login page after successful registration.

---

### H6. `datetime.utcnow` Used Throughout Models (Deprecated in Python 3.12+)

**Files:** All model files in `/workspace/RSITradingBot/RSITradingBot/backend/app/models/`

**Description:** Every model uses `default=datetime.utcnow` (bare callable). `datetime.utcnow()` is deprecated since Python 3.12 in favor of `datetime.now(timezone.utc)`. While functionally it works today, the bare `datetime.utcnow` callable passed as `default` is evaluated lazily and does not produce timezone-aware datetimes.

**Impact:** Dates stored without timezone info. Will break when upgrading to Python 3.12+ and could cause subtle bugs with timezone comparisons (the auth module already uses `timezone.utc`).

**Fix:** Replace `default=datetime.utcnow` with `default=lambda: datetime.now(timezone.utc)` consistently.

---

## MEDIUM (should fix soon)

### M1. Unreachable Code in AI Route

**File:** `/workspace/RSITradingBot/RSITradingBot/backend/app/api/v1/routes/ai.py` (line 65)

**Description:** `await service.close()` appears after a `return` statement and will never execute.

**Impact:** HTTP client connection is never properly closed, causing a resource leak.

**Fix:** Move the close call into a `try/finally` block, or use an async context manager.

---

### M2. Frontend `loadUser` Effect Missing `token` Dependency

**File:** `/workspace/RSITradingBot/RSITradingBot/frontend/src/App.tsx` (lines 46-52)

**Description:** The `AuthBootstrap` component's `useEffect` has an empty dependency array `[]` but reads `token` from the store. While the intent is to run once on mount, the ESLint `react-hooks/exhaustive-deps` rule would flag this, and the behavior could be fragile if the component remounts.

**Impact:** Low risk, but could lead to stale state in edge cases.

---

### M3. No CSRF Protection

**Description:** The API uses Bearer token auth (not cookies) so CSRF is not a direct concern for the API itself. However, the CORS config allows `allow_credentials=True` with wildcard methods and headers. If the CORS origins are misconfigured, this opens cross-origin attack vectors.

**Impact:** Depends on CORS configuration strictness.

**Fix:** Restrict CORS origins in production (never use `*` with `allow_credentials=True` -- this is actually rejected by browsers, so the current separate config is fine, but verify deployment).

---

### M4. Private Key Transmitted Over HTTP in Wallet Connect

**File:** `/workspace/RSITradingBot/RSITradingBot/backend/app/api/v1/routes/wallets.py` (line 25)
**File:** `/workspace/RSITradingBot/RSITradingBot/frontend/src/pages/SettingsPage.tsx` (line 259)

**Description:** The `ConnectWalletRequest` sends the plaintext `private_key` in the HTTP request body. If the connection is not HTTPS, the key is transmitted in cleartext.

**Impact:** Private key exposure if HTTPS is not enforced.

**Fix:** Add middleware or reverse-proxy config to reject non-HTTPS requests in production. Document that HTTPS is mandatory.

---

### M5. `WalletResponse` Field Name Inconsistency Between Backend and Frontend

**Files:**
- `/workspace/RSITradingBot/RSITradingBot/backend/app/api/v1/routes/wallets.py` (line 33: `wallet_id`)
- `/workspace/RSITradingBot/RSITradingBot/frontend/src/types/index.ts` (line 15: `id`)

**Description:** The backend `WalletResponse` returns `wallet_id`, but the frontend `Wallet` type expects `id`. The frontend uses `wallet.id` throughout (e.g., in `deleteWallet(wallet.id)`, query keys, etc.).

**Impact:** Wallet listing, deletion, and balance checks will all fail with undefined references.

---

## LOW (improve when convenient)

### L1. `HYPERLIQUID_ACCOUNT_ADDRESS` in docker-compose.yml But Not in config.py

**File:** `/workspace/RSITradingBot/RSITradingBot/docker-compose.yml` (line 56)

**Description:** The env var is passed to the container but `Settings` has no field to receive it. It is silently ignored (due to `extra = "ignore"`). This is dead configuration.

---

### L2. ApiKeysSection in SettingsPage is Non-Functional Placeholder

**File:** `/workspace/RSITradingBot/RSITradingBot/frontend/src/pages/SettingsPage.tsx` (lines 447-483)

**Description:** The API Keys section does not actually save anything -- `setSaved(true)` just shows a message. No API call is made. The "Hyperliquid API Key" field is misleading since the wallet system uses agent private keys, not API keys.

---

### L3. No Test Coverage for Auth or Wallet Modules

**Files:** `/workspace/RSITradingBot/RSITradingBot/backend/tests/`

**Description:** All 72 existing tests cover the RSI engine, signal detection, and backtester. Zero tests exist for auth, crypto, wallet routes, or user isolation.

**Impact:** The most security-critical code in the application has no automated test coverage.

---

## Checklist Results

| Check | Status | Notes |
|---|---|---|
| 1. No private keys in .env or config | FAIL | `HYPERLIQUID_PRIVATE_KEY` in docker-compose.yml (H1) |
| 2. Encryption correct (AES-256-GCM) | PASS | Nonce 12 bytes, key 32 bytes, proper encode/decode |
| 3. Auth enforced on all user routes | FAIL | AI route missing auth (C4) |
| 4. No key leakage from wallet endpoints | PASS | `WalletResponse` never includes `encrypted_private_key` |
| 5. User isolation in queries | PASS | All wallet queries filter by `current_user.id` |
| 6. Token handling (frontend) | FAIL | Field name mismatch breaks login/register (C1, H5) |
| 7. Import consistency | PASS | All modules imported in main.py and __init__.py |
| 8. Tests pass | PASS | 72/72 pass (but no auth/wallet tests) |

---

## Audit Trail

Files reviewed (20 files):
1. `backend/app/core/auth.py`
2. `backend/app/core/crypto.py`
3. `backend/app/api/v1/routes/auth.py`
4. `backend/app/api/v1/routes/wallets.py`
5. `backend/app/models/wallet.py`
6. `backend/app/models/api_key.py`
7. `backend/app/api/v1/routes/orders.py`
8. `backend/app/api/v1/routes/strategies.py`
9. `backend/app/api/v1/routes/signals.py`
10. `backend/app/api/v1/routes/risk.py`
11. `backend/app/api/v1/routes/reports.py`
12. `backend/app/config.py`
13. `backend/app/dependencies.py`
14. `.env.example`
15. `frontend/src/api/client.ts`
16. `frontend/src/store/useAuthStore.ts`
17. `frontend/src/App.tsx`
18. `frontend/src/pages/LoginPage.tsx`
19. `frontend/src/pages/RegisterPage.tsx`
20. `frontend/src/pages/SettingsPage.tsx`

Additional files reviewed:
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/user.py`
- `backend/app/api/v1/routes/health.py`
- `backend/app/api/v1/routes/ai.py`
- `docker-compose.yml`
- `frontend/src/types/index.ts`
- `frontend/src/api/auth.ts`
- `frontend/src/api/wallets.ts`
