# PROJECT PLAN -- RSI Trading Bot on Hyperliquid

**Project:** Automated crypto trading platform using regime-based RSI strategy
**Venue:** Hyperliquid (L1 onchain order book, perpetuals)
**MVP Universe:** BTC, ETH, SOL perpetuals
**Methodology:** Agile with phase-gated milestones
**Date:** 2026-04-28
**Status:** Planning -- pre-development

---

## Table of Contents

1. [Phase 1: Foundation](#phase-1-foundation)
2. [Phase 2: Core Engine](#phase-2-core-engine)
3. [Phase 3: Product](#phase-3-product)
4. [Parallel Execution Map](#parallel-execution-map)
5. [Risk Register](#risk-register)
6. [MVP Scope Boundaries](#mvp-scope-boundaries)
7. [Definition of Done](#definition-of-done)

---

## Phase 1: Foundation

**Goal:** Working data pipeline that connects to Hyperliquid, records market data, and stores it for backtesting. Zero trading logic yet.

**Duration estimate:** 3-4 weeks
**Gate criterion:** Can query 15m/1h/4h candles from local storage for BTC, ETH, SOL with gaps detected and filled.

---

### 1.1 -- Project scaffolding and repository structure

| Field | Value |
|---|---|
| **Task ID** | F-001 |
| **Name** | Project scaffolding and repository structure |
| **Description** | Initialize monorepo with Python backend package, frontend placeholder, Docker Compose for local dev (PostgreSQL, Redis, MinIO), pyproject.toml with dependencies (FastAPI, httpx, websockets, pandas, numpy, sqlalchemy, asyncpg), linter (ruff), formatter, and CI skeleton. Create service directory layout: `services/data_plane/`, `services/execution_plane/`, `services/api/`, `services/shared/`. |
| **Agent** | backend-developer |
| **Dependencies** | None |
| **Complexity** | S |
| **Acceptance criteria** | 1) `docker compose up` starts PostgreSQL, Redis, MinIO locally. 2) `make lint` and `make test` pass with a smoke test. 3) Directory structure matches agreed layout. 4) CI pipeline runs on push to any branch. |

---

### 1.2 -- Database schema for market data and configuration

| Field | Value |
|---|---|
| **Task ID** | F-002 |
| **Name** | Database schema -- PostgreSQL and TimescaleDB |
| **Description** | Design and implement PostgreSQL schema with TimescaleDB extension for timeseries. Tables: `candles` (symbol, timeframe, ts, open, high, low, close, volume -- hypertable partitioned by ts), `instruments` (symbol, base, quote, tick_size, lot_size, active), `data_gaps` (symbol, timeframe, start_ts, end_ts, status), `strategy_params` (id, name, params_json, created_at), `backtest_runs` (id, strategy_params_id, symbol, start_date, end_date, status, results_json). Include Alembic migrations. |
| **Agent** | database-architect |
| **Dependencies** | F-001 |
| **Complexity** | M |
| **Acceptance criteria** | 1) Migrations run cleanly on fresh DB. 2) Hypertable created on `candles.ts`. 3) Can insert and query 100k candle rows with sub-50ms response for a single symbol/timeframe range query. 4) Indexes exist on (symbol, timeframe, ts). |

---

### 1.3 -- Hyperliquid WebSocket ingestion service

| Field | Value |
|---|---|
| **Task ID** | F-003 |
| **Name** | Hyperliquid WebSocket ingestion service |
| **Description** | Build async Python service that connects to Hyperliquid WebSocket API (`wss://api.hyperliquid.xyz/ws`). Subscribe to `candle` channels for BTC, ETH, SOL on 15m, 1h, 4h timeframes. Handle: connection lifecycle, automatic reconnection with exponential backoff, ping/pong keepalive (server closes idle connections after 60s), message parsing, and publishing normalized candle data to an internal event bus (Redis pub/sub or asyncio queue). Log connection events, message counts, and errors. |
| **Agent** | backend-developer |
| **Dependencies** | F-001 |
| **Complexity** | L |
| **Acceptance criteria** | 1) Connects and stays connected to Hyperliquid WS for 24h without manual intervention. 2) Receives and parses candle messages for all 9 symbol/timeframe combinations (3 symbols x 3 timeframes). 3) Reconnects automatically within 10 seconds if connection drops. 4) Publishes normalized messages to Redis channel. 5) Logs message rate and connection state. |

---

### 1.4 -- Market data recorder and gap detection

| Field | Value |
|---|---|
| **Task ID** | F-004 |
| **Name** | Market data recorder and gap detection |
| **Description** | Service that consumes candle events from the event bus and persists them to TimescaleDB. On startup, compare latest stored candle timestamp per symbol/timeframe against current time to detect gaps. For gaps, attempt backfill using Hyperliquid REST `candleSnapshot` endpoint (limited to 5000 candles). Record any unfilled gaps in `data_gaps` table. Store raw data in Parquet on MinIO as secondary archive. Run as a background worker. |
| **Agent** | backend-developer |
| **Dependencies** | F-002, F-003 |
| **Complexity** | L |
| **Acceptance criteria** | 1) Candles are persisted to TimescaleDB within 5 seconds of WS receipt. 2) Gap detection runs on startup and identifies missing periods. 3) Backfill successfully fetches history for the past 5000 candles per symbol/timeframe. 4) Parquet files written to MinIO with correct schema. 5) `data_gaps` table populated for any gaps beyond the 5000-candle window. |

---

### 1.5 -- Shared models and utilities package

| Field | Value |
|---|---|
| **Task ID** | F-005 |
| **Name** | Shared models and utilities |
| **Description** | Create `services/shared/` package with: Pydantic models for Candle, Signal, Order, Position, Trade, BacktestResult; enum types for Timeframe (M15, H1, H4), Direction (LONG, SHORT), Regime (BULL, BEAR, NEUTRAL), OrderStatus; configuration loader from environment variables; structured logging setup; RSI calculation function (Wilder smoothing, configurable period) as a pure function tested against known inputs. |
| **Agent** | backend-developer |
| **Dependencies** | F-001 |
| **Complexity** | M |
| **Acceptance criteria** | 1) RSI calculation matches a reference implementation (e.g., pandas-ta or manual calculation on a known price series) to within 0.01 RSI units. 2) All Pydantic models validate correctly with valid input and reject invalid input. 3) Configuration loads from env vars with sensible defaults. 4) Unit test coverage above 90% for this package. |

---

### 1.6 -- Integration test framework and Hyperliquid mock

| Field | Value |
|---|---|
| **Task ID** | F-006 |
| **Name** | Integration test framework and Hyperliquid mock |
| **Description** | Set up pytest fixtures for integration tests: a mock Hyperliquid WebSocket server (using `websockets` library) that sends scripted candle messages, a mock REST API for `candleSnapshot`, a test PostgreSQL instance (Docker), a test Redis instance (Docker), and factory functions for generating test candles, signals, and orders. Create a test harness that can replay a recorded session. |
| **Agent** | qa-expert |
| **Dependencies** | F-001, F-005 |
| **Complexity** | M |
| **Acceptance criteria** | 1) Integration test suite runs in under 60 seconds with all containers started via docker-compose test profile. 2) Mock WS server sends configurable candle sequences. 3) At least 3 integration test scenarios: normal ingestion, reconnection after disconnect, gap detection on startup. |

---

### 1.7 -- Git branching strategy and CI/CD pipeline

| Field | Value |
|---|---|
| **Task ID** | F-007 |
| **Name** | Git branching strategy and CI/CD pipeline |
| **Description** | Implement Git Flow: `main` (production-ready), `develop` (integration), `feature/*` branches. CI pipeline: lint (ruff), type check (mypy or pyright), unit tests, integration tests, build Docker images. CD pipeline: merge to `develop` deploys to staging environment; merge to `main` deploys to production. Set up branch protection rules, required reviews, and conventional commit enforcement. |
| **Agent** | git-flow-manager |
| **Dependencies** | F-001 |
| **Complexity** | S |
| **Acceptance criteria** | 1) Branch protection active on `main` and `develop`. 2) CI runs on every PR and blocks merge on failure. 3) Feature branches follow naming convention. 4) Docker images build and push to registry. |

---

## Phase 2: Core Engine

**Goal:** RSI engine that detects signals, risk engine that validates them, backtester that proves them. No live trading yet.

**Duration estimate:** 4-5 weeks
**Gate criterion:** Backtester produces reproducible results with Sharpe, MDD, expectancy, and trade distribution for at least one symbol with walk-forward validation.

---

### 2.1 -- RSI engine -- regime detection and signal generation

| Field | Value |
|---|---|
| **Task ID** | E-001 |
| **Name** | RSI engine -- regime detection and signal generation |
| **Description** | Implement the core strategy logic as a stateless computation module. Input: ordered series of candles for 4h, 1h, and 15m timeframes. Output: current regime (bull/bear/neutral), signal state (waiting/pullback-detected/entry-triggered/no-signal), and actionable signal events. Logic: (1) Regime: RSI-14 on 4h -- bull if >55, bear if <45, neutral otherwise. (2) Signal: in bull regime, watch for RSI-14 on 1h to drop into 40-48 zone and then reclaim 50; in bear regime, watch for RSI-14 on 1h to rise into 52-60 zone and then lose 50. (3) Confirmation: on 15m, wait for a candle close in the direction of the signal before emitting the final signal. The engine must process candles chronologically and emit signals at the correct bar boundaries. |
| **Agent** | backend-developer |
| **Dependencies** | F-005 |
| **Complexity** | L |
| **Acceptance criteria** | 1) Given a known price series, the engine produces the correct regime classification at each 4h bar. 2) Signal events fire at the correct bar boundaries (not intrabar). 3) Confirmation step requires a 15m close in the signal direction. 4) Engine processes 10,000 bars in under 1 second. 5) Unit tests cover: bull regime entry, bear regime entry, neutral regime (no signal), signal without confirmation (not emitted), and signal with confirmation (emitted). |

---

### 2.2 -- Risk engine -- position sizing and exposure limits

| Field | Value |
|---|---|
| **Task ID** | E-002 |
| **Name** | Risk engine -- position sizing and exposure limits |
| **Description** | Implement risk management as a pure function. Input: signal (direction, symbol, entry price, stop distance), account equity, current open positions, risk parameters. Output: approved/rejected signal, position size in units, stop-loss price, take-profit levels (partial at 1.5R), leverage (capped at 3x isolated), and any rejection reason. Rules: (1) Risk per trade: configurable, default 0.5% of equity. (2) Max open positions: 3 (one per symbol). (3) Max leverage: 3x isolated, never cross. (4) No new entry if same-direction position already open on the symbol. (5) Time stop: flag if position held beyond 36 hours. (6) Hard daily loss limit: configurable, default 2% of equity. |
| **Agent** | backend-developer |
| **Dependencies** | F-005, E-001 |
| **Complexity** | M |
| **Acceptance criteria** | 1) Position size = (equity * risk_pct) / stop_distance, capped by leverage limit. 2) Rejects signal when 3 positions already open. 3) Rejects signal when daily loss limit reached. 4) Rejects duplicate direction on same symbol. 5) Leverage never exceeds 3x isolated. 6) All rejection reasons are returned as structured messages. 7) Unit tests for each rule in isolation and in combination. |

---

### 2.3 -- Exit logic -- trailing stop, RSI cross, and time stop

| Field | Value |
|---|---|
| **Task ID** | E-003 |
| **Name** | Exit logic -- trailing stop, RSI cross, and time stop |
| **Description** | Implement exit evaluation as a function called on each new candle for each open position. Input: position details, current candle data for 15m and 1h, current regime 4h. Output: exit signal (yes/no), exit type (partial_tp, trailing_stop, rsi_cross, regime_change, time_stop, hard_stop). Logic: (1) Partial exit: close 50% at 1.5R profit, move stop to breakeven. (2) Trailing: after partial exit, trail stop using RSI 15m cross against position direction. (3) RSI cross exit: close remaining if RSI 1h crosses back against the trade direction. (4) Regime exit: close if 4h regime returns to neutral or flips. (5) Time stop: close if held beyond 36 hours. (6) Hard stop: close if price hits stop-loss level. |
| **Agent** | backend-developer |
| **Dependencies** | F-005, E-001 |
| **Complexity** | M |
| **Acceptance criteria** | 1) Partial exit triggers at exactly 1.5R. 2) After partial exit, remaining position uses trailing logic based on RSI 15m. 3) Full exit triggers on RSI 1h cross against position. 4) Full exit triggers on regime change to neutral or opposite. 5) Full exit triggers at 36-hour hold limit. 6) Full exit triggers at stop-loss price. 7) Priority order is enforced when multiple exits trigger simultaneously (hard_stop > regime > rsi_1h > trailing > time). 8) All scenarios covered by unit tests. |

---

### 2.4 -- Backtester engine

| Field | Value |
|---|---|
| **Task ID** | E-004 |
| **Name** | Backtester engine |
| **Description** | Build event-driven backtester that replays historical candles bar-by-bar through the RSI engine, risk engine, and exit logic. Input: symbol, date range, strategy parameters, cost model (taker/maker fee, slippage bps, funding assumption). Output: trade log (entry ts, exit ts, direction, entry price, exit price, size, pnl, exit reason, holding hours), equity curve, and aggregate metrics (CAGR, Sharpe, MDD, win rate, expectancy, profit factor, avg win/loss, trades per year, avg time in market). Must handle: multi-timeframe synchronization (4h/1h/15m bars), realistic fill at next-bar open after signal, commission deduction, and slippage modeling. Results must be reproducible given same inputs. |
| **Agent** | backend-developer |
| **Dependencies** | F-002, F-005, E-001, E-002, E-003 |
| **Complexity** | L |
| **Acceptance criteria** | 1) Given the same input data and parameters, produces identical results on every run. 2) Correctly synchronizes 4h, 1h, and 15m bar boundaries. 3) Fills at next-bar open after signal, not at signal bar close. 4) Deducts commission and slippage on every trade. 5) Output includes all required metrics. 6) Completes a 6-month backtest in under 10 seconds. 7) Trade log is exportable as CSV and Parquet. 8) At least 5 integration test scenarios: bull-trending period, bear-trending period, choppy period, no-trade period, single-trade detailed walkthrough. |

---

### 2.5 -- Walk-forward validation module

| Field | Value |
|---|---|
| **Task ID** | E-005 |
| **Name** | Walk-forward validation module |
| **Description** | Implement walk-forward analysis on top of the backtester. Input: symbol, total date range, training window (e.g., 90 days), test window (e.g., 30 days), parameter grid (rsi_length: [9,14,21], regime thresholds: [45/55, 50/50]). Process: for each walk-forward step, (1) run optimization on training window selecting best Sharpe, (2) freeze parameters, (3) run backtest on test window, (4) advance windows, (5) aggregate out-of-sample results. Output: in-sample vs out-of-sample metrics comparison, degradation percentage, Deflated Sharpe Ratio estimate. |
| **Agent** | backend-developer |
| **Dependencies** | E-004 |
| **Complexity** | L |
| **Acceptance criteria** | 1) Walk-forward correctly partitions data into non-overlapping train/test windows. 2) Parameters are frozen during test window (no look-ahead). 3) Output includes both in-sample and out-of-sample metrics side by side. 4) Degradation percentage calculated as (IS_Sharpe - OOS_Sharpe) / IS_Sharpe. 5) Completes a 1-year walk-forward with 3x3 parameter grid in under 5 minutes. 6) Results are reproducible. |

---

### 2.6 -- Backtester unit and integration tests

| Field | Value |
|---|---|
| **Task ID** | E-006 |
| **Name** | Backtester unit and integration tests |
| **Description** | Comprehensive test suite for the entire engine pipeline. Unit tests: RSI calculation edge cases (all-up, all-down, flat), regime transitions at exact thresholds, signal generation at boundary values, risk rejection scenarios, exit priority conflicts. Integration tests: full backtest on synthetic data with known outcomes, walk-forward on pre-built price series, multi-symbol concurrent backtest, cost model impact comparison (zero-cost vs realistic vs adversarial). Performance test: backtest 2 years of 15m data for 3 symbols runs in under 30 seconds. |
| **Agent** | qa-expert |
| **Dependencies** | E-004, E-005 |
| **Complexity** | M |
| **Acceptance criteria** | 1) Test coverage above 85% for `services/execution_plane/`. 2) All edge cases from strategy document covered (RSI at 0, RSI at 100, empty periods, gap handling). 3) Synthetic data test: 100 bars with known RSI values, verify exact signals produced. 4) Cost model test: zero-cost backtest has strictly higher Sharpe than adversarial-cost backtest for same data. 5) All tests pass in CI. |

---

### 2.7 -- Backtester API endpoint

| Field | Value |
|---|---|
| **Task ID** | E-007 |
| **Name** | Backtester API endpoint |
| **Description** | Expose backtester as a REST endpoint. `POST /v1/backtests` accepts: symbol, start_date, end_date, strategy_params, cost_model. Response: backtest_id, status (queued/running/complete/failed), results_url. Run backtest asynchronously (background task). `GET /v1/backtests/{id}` returns status and results when complete. `POST /v1/walkforward` for walk-forward runs. Implement rate limiting. Store results in PostgreSQL `backtest_runs` table and results Parquet in MinIO. |
| **Agent** | backend-developer |
| **Dependencies** | E-004, E-005, F-002 |
| **Complexity** | M |
| **Acceptance criteria** | 1) POST returns 202 with backtest_id immediately. 2) Backtest runs asynchronously and completes within expected time. 3) GET returns complete results with all metrics. 4) Concurrent backtest requests (up to 3) do not interfere. 5) Invalid parameters return 422 with clear error message. 6) Rate limited to 10 requests per minute per client. |

---

## Phase 3: Product

**Goal:** Web dashboard showing live signals, backtest results, and paper trading. Ready for internal testing.

**Duration estimate:** 4-5 weeks
**Gate criterion:** Dashboard displays live regime/signal state for BTC/ETH/SOL, can run and visualize a backtest, and paper-trading mode tracks simulated positions end-to-end.

---

### 3.1 -- FastAPI application skeleton with auth

| Field | Value |
|---|---|
| **Task ID** | P-001 |
| **Name** | FastAPI application skeleton with authentication |
| **Description** | Set up the main FastAPI application with: CORS middleware, request logging, health check endpoint, JWT-based authentication (register, login, token refresh), API key management for programmatic access, and route organization with routers for `/v1/backtests`, `/v1/signals`, `/v1/positions`, `/v1/risk`, `/v1/reports`. Add user table to PostgreSQL schema. |
| **Agent** | backend-developer |
| **Dependencies** | F-001, F-002 |
| **Complexity** | M |
| **Acceptance criteria** | 1) User can register, login, and receive JWT. 2) Protected endpoints reject requests without valid token. 3) Health check returns 200 with DB and Redis connectivity status. 4) API documentation auto-generated at `/docs`. 5) Request logging captures method, path, status code, and latency. |

---

### 3.2 -- Live signal evaluation endpoint

| Field | Value |
|---|---|
| **Task ID** | P-002 |
| **Name** | Live signal evaluation endpoint |
| **Description** | `GET /v1/signals/{symbol}` returns current regime (4h RSI), signal state (1h RSI relative to zones), and confirmation status (latest 15m bar). `GET /v1/signals` returns summary for all watched symbols. Data sourced from TimescaleDB (latest candles) with computation done by the RSI engine module. Cache results in Redis with 15-second TTL. |
| **Agent** | backend-developer |
| **Dependencies** | F-002, F-005, E-001 |
| **Complexity** | S |
| **Acceptance criteria** | 1) Returns current regime, RSI values for all three timeframes, and signal state for requested symbol. 2) Response time under 200ms. 3) Cache invalidates correctly when new candle arrives. 4) Returns 404 for unsupported symbols. |

---

### 3.3 -- Paper trading engine

| Field | Value |
|---|---|
| **Task ID** | P-003 |
| **Name** | Paper trading engine |
| **Description** | Implement simulated order management for paper trading. Maintains in-memory and persistent state for: open positions, pending orders, filled trades, account equity (starting virtual balance). On each new candle (consumed from event bus), run RSI engine -> risk engine -> exit logic pipeline. If a signal is approved, create a simulated fill at next-bar open price minus estimated slippage. Track PnL, equity curve, and all trade history. Support start/stop/reset of paper trading sessions. Store state in PostgreSQL to survive restarts. |
| **Agent** | backend-developer |
| **Dependencies** | E-001, E-002, E-003, F-002, F-003 |
| **Complexity** | L |
| **Acceptance criteria** | 1) Paper trading processes live candles and generates simulated trades. 2) Positions track entry price, stop, take-profit, unrealized PnL in real time. 3) Equity curve updates with each closed trade. 4) State persists across service restarts. 5) Can start, stop, and reset paper trading sessions via API. 6) Trade log is queryable via API. |

---

### 3.4 -- Paper trading API endpoints

| Field | Value |
|---|---|
| **Task ID** | P-004 |
| **Name** | Paper trading and positions API |
| **Description** | REST endpoints: `POST /v1/paper/session` (start/stop/reset), `GET /v1/paper/status` (current session state), `GET /v1/paper/positions` (open positions), `GET /v1/paper/trades` (closed trades), `GET /v1/paper/equity` (equity curve), `GET /v1/paper/performance` (aggregate metrics: PnL, Sharpe, MDD, win rate). All endpoints require authentication. |
| **Agent** | backend-developer |
| **Dependencies** | P-001, P-003 |
| **Complexity** | S |
| **Acceptance criteria** | 1) All endpoints return correct data matching paper trading state. 2) Session lifecycle works (start -> active trades -> stop -> reset). 3) Performance metrics match manual calculation on same trade set. 4) Paginated trade history with date filtering. |

---

### 3.5 -- Frontend project setup and shared layout

| Field | Value |
|---|---|
| **Task ID** | P-005 |
| **Name** | Frontend project setup and shared layout |
| **Description** | Initialize Next.js project with TypeScript, Tailwind CSS, and chart library (Lightweight Charts or Recharts). Set up: authentication flow (login/register pages), dashboard layout with sidebar navigation, API client module with JWT refresh handling, and WebSocket client for real-time updates. Pages: Dashboard, Backtest, Paper Trading, Settings. |
| **Agent** | frontend-developer |
| **Dependencies** | P-001 |
| **Complexity** | M |
| **Acceptance criteria** | 1) User can register and login through the UI. 2) Dashboard layout renders with navigation between pages. 3) API client handles token refresh transparently. 4) WebSocket client connects and receives real-time candle updates. 5) Build and lint pass with zero errors. |

---

### 3.6 -- Dashboard -- live market overview

| Field | Value |
|---|---|
| **Task ID** | P-006 |
| **Name** | Dashboard -- live market overview |
| **Description** | Main dashboard page showing real-time state for BTC, ETH, SOL. Each symbol displays: current price, 4h RSI with regime badge (bull/bear/neutral), 1h RSI with signal zone indicator, 15m RSI with confirmation status, and current signal state (waiting / pullback-detected / entry-triggered / no-signal). Price chart with lightweight charts showing recent 4h candles with RSI overlay. Auto-updates via WebSocket. |
| **Agent** | frontend-developer |
| **Dependencies** | P-005, P-002 |
| **Complexity** | M |
| **Acceptance criteria** | 1) Dashboard loads and shows data for all three symbols within 2 seconds. 2) Price and RSI values update in real time as new candles arrive. 3) Regime badge displays correct color/label matching strategy rules (bull=green, bear=red, neutral=gray). 4) Signal state changes are visually highlighted. 5) Responsive layout works on screens 1280px and wider. |

---

### 3.7 -- Dashboard -- backtest results visualization

| Field | Value |
|---|---|
| **Task ID** | P-007 |
| **Name** | Dashboard -- backtest results visualization |
| **Description** | Backtest page with: form to configure and launch a backtest (symbol, date range, strategy params, cost model), results display with equity curve chart, drawdown chart, trade distribution bar chart, and metrics table (CAGR, Sharpe, MDD, win rate, expectancy, profit factor, trades count, avg hold time). Trade list table with sorting and filtering. Walk-forward results view comparing in-sample vs out-of-sample performance. |
| **Agent** | frontend-developer |
| **Dependencies** | P-005, E-007 |
| **Complexity** | L |
| **Acceptance criteria** | 1) Can configure and submit a backtest from the UI. 2) Progress indicator shown while backtest runs. 3) Equity curve, drawdown, and trade distribution charts render correctly. 4) Metrics table displays all required values. 5) Trade list is sortable by date, pnl, direction, and exit reason. 6) Walk-forward view shows IS vs OOS comparison. |

---

### 3.8 -- Dashboard -- paper trading view

| Field | Value |
|---|---|
| **Task ID** | P-008 |
| **Name** | Dashboard -- paper trading view |
| **Description** | Paper trading page with: session controls (start/stop/reset), open positions table (symbol, direction, entry price, current price, unrealized PnL, stop, take-profit, hold time), closed trades table, live equity curve, and performance summary (same metrics as backtest). Real-time updates via WebSocket. Visual indicator when a new trade is opened or closed. |
| **Agent** | frontend-developer |
| **Dependencies** | P-005, P-004 |
| **Complexity** | M |
| **Acceptance criteria** | 1) Can start/stop/reset paper trading session from UI. 2) Open positions update in real time. 3) Equity curve updates with each closed trade. 4) Performance metrics match backtester output format. 5) Visual notification on new trade events. |

---

### 3.9 -- Reporting and export

| Field | Value |
|---|---|
| **Task ID** | P-009 |
| **Name** | Reporting and export |
| **Description** | `GET /v1/reports/performance` endpoint returning equity curve, trade log, and metrics for a given date range. Support CSV and JSON export of trade history. Support PDF export of backtest results (using reportlab or weasyprint) with charts rendered server-side. Frontend download buttons on backtest and paper trading pages. |
| **Agent** | backend-developer, frontend-developer |
| **Dependencies** | P-004, E-007 |
| **Complexity** | M |
| **Acceptance criteria** | 1) Trade history downloadable as CSV with all fields. 2) Backtest results downloadable as PDF with equity curve and metrics. 3) Export completes in under 5 seconds for up to 500 trades. |

---

### 3.10 -- Deployment setup

| Field | Value |
|---|---|
| **Task ID** | P-010 |
| **Name** | Deployment setup -- Kubernetes and Docker |
| **Description** | Create Dockerfiles for each service (data-plane, execution-plane, api, frontend). Kubernetes manifests (or Helm chart) for: API deployment, data-plane deployment, worker deployment, PostgreSQL StatefulSet (or managed DB reference), Redis StatefulSet, MinIO StatefulSet. ConfigMaps for environment configuration. Secrets for API keys and database credentials. Ingress for API and frontend. Health check and readiness probes on all services. |
| **Agent** | backend-developer |
| **Dependencies** | All Phase 1 and Phase 2 tasks |
| **Complexity** | M |
| **Acceptance criteria** | 1) `kubectl apply` brings up entire stack in a fresh namespace. 2) All health checks pass. 3) Frontend accessible via ingress. 4) API accessible via ingress with authentication. 5) Data plane connects to Hyperliquid and records data. 6) Secrets are not in any Docker image or manifest. |

---

### 3.11 -- End-to-end testing and performance validation

| Field | Value |
|---|---|
| **Task ID** | P-011 |
| **Name** | End-to-end testing and performance validation |
| **Description** | Full E2E test suite covering: user registration -> login -> run backtest -> view results -> start paper trading -> verify live signal processing -> verify trade execution -> stop paper trading -> export report. Performance validation: API p95 latency under 500ms for all endpoints, WebSocket processes 1000 msgs/sec without backlog, backtest 1 year of data in under 30 seconds. Load test with 10 concurrent users. |
| **Agent** | qa-expert |
| **Dependencies** | All Phase 3 tasks |
| **Complexity** | L |
| **Acceptance criteria** | 1) E2E test suite passes in staging environment. 2) API p95 latency under 500ms for all read endpoints. 3) WebSocket ingestion handles 1000 msgs/sec with sub-second processing latency. 4) Backtest performance within budget. 5) No data loss during a 1-hour sustained ingestion test. 6) Load test with 10 concurrent users shows no errors. |

---

### 3.12 -- Documentation and runbook

| Field | Value |
|---|---|
| **Task ID** | P-012 |
| **Name** | Documentation and runbook |
| **Description** | Write: API reference (auto-generated from FastAPI with supplementary examples), deployment guide (step-by-step Kubernetes setup), operational runbook (how to monitor, what alerts mean, how to restart services, how to handle Hyperliquid connectivity loss), and developer onboarding guide (local dev setup, testing, architecture overview). |
| **Agent** | backend-developer |
| **Dependencies** | P-010 |
| **Complexity** | S |
| **Acceptance criteria** | 1) A new developer can set up local environment following the guide in under 30 minutes. 2) API reference covers all endpoints with request/response examples. 3) Runbook covers all critical alert scenarios from the risk register. |

---

## Parallel Execution Map

The following diagram shows which tasks can run concurrently, organized by stream.

```
WEEK 1-2:
  Stream A: F-001 (scaffolding)
  Stream B: F-007 (git branching) -- starts after F-001

WEEK 2-3:
  Stream A: F-002 (database) + F-005 (shared models) -- parallel after F-001
  Stream B: F-003 (WebSocket ingestion) -- after F-001
  Stream C: F-006 (test framework) -- after F-001, F-005

WEEK 3-4:
  Stream A: F-004 (recorder) -- after F-002, F-003
  Stream B: F-006 (test framework) -- continuing

  --- PHASE 1 GATE: Data pipeline recording market data ---

WEEK 4-5:
  Stream A: E-001 (RSI engine) -- after F-005
  Stream B: E-002 (risk engine) -- after F-005, starts E-001 for interface

WEEK 5-6:
  Stream A: E-003 (exit logic) -- after F-005, parallel with E-001
  Stream B: E-002 (risk engine) -- continuing

WEEK 6-7:
  Stream A: E-004 (backtester) -- after E-001, E-002, E-003, F-002
  Stream B: E-006 (tests) -- starts alongside E-004

WEEK 7-8:
  Stream A: E-005 (walk-forward) -- after E-004
  Stream B: E-007 (backtester API) -- after E-004, F-002

  --- PHASE 2 GATE: Backtester produces reproducible results ---

WEEK 8-9:
  Stream A: P-001 (API skeleton with auth) -- after F-001, F-002
  Stream B: P-002 (live signal endpoint) -- after E-001
  Stream C: P-005 (frontend setup) -- after P-001
  Stream D: P-003 (paper trading engine) -- after E-001, E-002, E-003

WEEK 9-10:
  Stream A: P-006 (dashboard live view) -- after P-005, P-002
  Stream B: P-004 (paper trading API) -- after P-001, P-003
  Stream C: P-010 (deployment) -- starts, depends on Phase 1+2

WEEK 10-11:
  Stream A: P-007 (backtest visualization) -- after P-005, E-007
  Stream B: P-008 (paper trading view) -- after P-005, P-004
  Stream C: P-009 (reporting) -- after P-004, E-007

WEEK 11-12:
  Stream A: P-011 (E2E testing) -- after all Phase 3 tasks
  Stream B: P-012 (documentation) -- after P-010

  --- PHASE 3 GATE: MVP ready for internal testing ---
```

**Parallelization summary:**
- Phase 1: Up to 3 concurrent streams after week 2.
- Phase 2: Up to 2 concurrent streams. Engine work is sequential by dependency but risk/exit can parallelize once interfaces are defined.
- Phase 3: Up to 4 concurrent streams. Frontend and backend develop in parallel against agreed API contracts.

**Critical path:** F-001 -> F-002/F-005 -> E-001 -> E-004 -> E-005 -> P-003 -> P-011

**Estimated total duration:** 11-12 weeks from first commit to MVP ready.

---

## Risk Register

| ID | Risk | Probability | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R-01 | Hyperliquid WebSocket instability or undocumented breaking changes | Medium | High | Implement robust reconnection with exponential backoff. Version-lock the WebSocket client. Monitor Hyperliquid changelog. Keep REST fallback for candle backfill. | backend-developer |
| R-02 | Insufficient historical data for meaningful backtest (only 5000 candles via API) | High | High | Deploy market data recorder from day one. Accept that early backtests will cover shorter periods. Consider supplementing with Binance public data for BTC/ETH as cross-reference only. | backend-developer |
| R-03 | RSI strategy shows no edge in backtesting after costs | Medium | Medium | Design backtester to test multiple parameter sets and cost scenarios. Be prepared to iterate on thresholds before proceeding to Phase 3. The backtester itself has value regardless of outcome. | backend-developer |
| R-04 | Incorrect RSI calculation leads to false signals | Low | Critical | Validate RSI output against at least two reference implementations. Include edge case tests (all-up, all-down, flat series). Peer review of calculation code. | qa-expert |
| R-05 | TimescaleDB performance bottleneck at scale | Low | Medium | Design schema with proper partitioning from the start. Benchmark at 10x expected data volume. Have migration plan to ClickHouse if needed. | database-architect |
| R-06 | Look-ahead bias in backtester | Medium | Critical | Enforce strict chronological processing. Signal at bar N fills at bar N+1 open. Walk-forward validation with frozen parameters. Code review focused on data flow. | qa-expert |
| R-07 | Frontend WebSocket reconnection causes duplicate or missed events | Medium | Low | Implement idempotent event processing with sequence numbers. Show connection status in UI. Queue events during brief disconnections. | frontend-developer |
| R-08 | Scope creep -- adding features before core is solid | High | High | Strict phase gates. No live trading until paper trading proves stable for 2 weeks. No new indicators until RSI strategy is validated. AI sidecar explicitly deferred to post-MVP. | project-manager |
| R-09 | Hyperliquid nonce management issues in future live trading | Low | High | Research nonce patterns during Phase 1-2. Design OMS with nonce tracking from the start. Isolated signer service architecture prepared but not implemented until post-MVP. | backend-developer |
| R-10 | Regulatory uncertainty -- MiCA transitory period ends July 2026 | Medium | High | Keep SaaS non-custodial. User signs own agent wallet approval. No fiat rails. No investment advice. Document the non-custodial nature clearly. Consult legal before any beta with external users. | project-manager |
| R-11 | Key/credential exposure in codebase or containers | Low | Critical | Secrets in environment variables or vault only, never in code. Pre-commit hooks scan for secret patterns. CI fails on detected secrets. Separate signer service for production. | git-flow-manager |
| R-12 | Team bottleneck on backend-developer (most tasks assigned) | High | Medium | Prioritize backend tasks on critical path. Frontend and QA tasks can be picked up by dedicated agents. Consider splitting backend into data-plane and execution-plane specialists if team grows. | project-manager |

---

## MVP Scope Boundaries

### IN scope (MVP)
- WebSocket ingestion for BTC, ETH, SOL on 15m, 1h, 4h
- Market data storage in TimescaleDB with gap detection
- RSI engine with regime detection, signal generation, and confirmation
- Risk engine with position sizing and exposure limits
- Exit logic with trailing, RSI cross, regime change, and time stops
- Event-driven backtester with walk-forward validation
- Paper trading engine (simulated execution)
- REST API for backtests, signals, positions, performance
- Web dashboard with live market view, backtest results, paper trading
- Kubernetes deployment manifests
- Authentication and basic RBAC

### OUT of scope (post-MVP)
- Live trading with real funds
- Order management system for live execution
- Isolated signer service with nonce management
- Reconciliation against Hyperliquid fills
- AI sidecar (z.ai integration for exception classification, NLG)
- Multi-user tenancy with full isolation
- Builder fee integration
- Advanced metrics (Deflated Sharpe Ratio, CSCV/PBO)
- Mobile application
- Additional indicators beyond RSI
- Additional symbols beyond BTC, ETH, SOL
- Alerting and notification system (email, Telegram)
- Regulatory compliance automation (KYC, AML)
- Rate limiting and billing for external API consumers

---

## Definition of Done

A task is "done" when all of the following are true:

1. **Code complete:** All acceptance criteria met. No TODO comments or placeholder logic.
2. **Tests pass:** Unit tests for the task pass in CI. Integration tests pass if applicable.
3. **Reviewed:** Code reviewed by at least one other agent. Review comments addressed.
4. **Documented:** Public APIs have docstrings. Non-obvious logic has inline comments. No need for verbal explanation.
5. **Linted:** Passes ruff lint and type checking with zero errors.
6. **Merged:** Changes merged to `develop` branch via approved pull request.

A phase is "done" when:

1. All tasks in the phase meet the definition of done.
2. Phase gate criterion is satisfied (verified by demonstration, not assertion).
3. No known critical or high-severity bugs remain open.
4. Integration tests covering cross-task interactions pass.
