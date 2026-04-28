# QA Audit Report - RSI Trading Bot Backend

**Date:** 2026-04-28  
**Auditor:** QA Expert Agent  
**Scope:** Backend core modules (RSI engine, regime, signal, exit logic, risk manager, backtester, WebSocket, OMS)  
**Test Results:** 72/72 tests passing

---

## 1. Executive Summary

The backend is well-structured with clean separation of concerns. The RSI calculation engine correctly implements Wilder's smoothing method and produces values matching manual computation. However, the audit found **3 critical bugs**, **2 medium-severity issues**, and **4 low-severity findings** that should be addressed before production deployment.

---

## 2. Test Results

```
72 passed in 1.16s
```

All existing tests pass. Test coverage exists for:
- RSI engine (20 tests): computation, series, incremental updates, edge cases
- Regime detection (14 tests): thresholds, series, transitions, EMA
- Signal detection (16 tests): setup, trigger, confirmation, regime change, strength
- Backtester (16 tests): empty data, synthetic runs, cost model, DSR, metrics
- No tests for: exit_logic, risk_manager, websocket_client, oms, candle_builder

**Coverage Gap:** 4 core modules have zero test coverage (exit logic, risk manager, WebSocket client, OMS).

---

## 3. Critical Bugs

### BUG-1: Backtester crashes on open position at end of data [SEVERITY: CRITICAL]

**File:** `backend/app/core/backtester.py`, lines 372-378

**Description:** When a position is still open at the end of the backtest, the code calls `_close_position` passing `False` as the `record` parameter:

```python
trade = self._close_position(
    position, last_bar.close, last_bar.timestamp,
    action, current_equity, False
)
trades.append(trade)
```

The function signature is `_close_position(self, ..., record=None, ...)`. Passing `False` sets `record=False`. Inside the function at line 534: `if record is not None: record.append(trade)` -- since `False is not None` evaluates to `True`, it attempts `False.append(trade)`, causing `AttributeError: 'bool' object has no attribute 'append'`.

**Impact:** The backtester crashes whenever a position is open at the end of the data. This is a common scenario in backtesting.

**Fix:** Change line 372 from `..., current_equity, False)` to `..., current_equity, None)` and keep the manual `trades.append(trade)` on line 378. Or pass `trades` and remove the manual append.

---

### BUG-2: Backtester treats partial exits as full exits [SEVERITY: CRITICAL]

**File:** `backend/app/core/backtester.py`, lines 287-297

**Description:** When `ExitManager.evaluate()` returns a `PARTIAL_R` action (should_exit=True, close_pct=0.5), the backtester's main loop at line 287 checks `action.should_exit` and immediately closes the entire position:

```python
if action.should_exit:
    trade = self._close_position(position, ...)
    ...
    position = None
```

The position is set to None (fully closed) regardless of `action.close_pct`. The exit manager is designed to close 50% at 1.5R and keep the remainder open for trailing exit. The backtester ignores this and closes 100%.

**Impact:** Backtest results significantly overstate the number of round-trip trades and misrepresent the exit strategy. The partial profit-taking mechanism -- a core part of the strategy -- is completely broken in the backtester.

**Fix:** Check `action.close_pct` before setting `position = None`. For partial exits, reduce `position.position_size` by `close_pct`, record a partial trade, and keep the position open.

---

### BUG-3: OMS missing ACCEPTED -> CANCELED transition [SEVERITY: HIGH]

**File:** `backend/app/execution/oms.py`, line 38

**Description:** The `TRANSITIONS` dict does not allow `ACCEPTED -> CANCELED`. After an order is accepted by the venue, there is no way to cancel it. In real exchange workflows, cancellation after acceptance is a standard operation.

```python
OMSOrderStatus.ACCEPTED: [OMSOrderStatus.RESTING, OMSOrderStatus.FILLING, OMSOrderStatus.REJECTED],
```

**Impact:** Orders that are accepted but not yet resting (e.g., market orders being processed) cannot be canceled. This would prevent proper order management in live trading.

**Fix:** Add `OMSOrderStatus.CANCELED` to the accepted state's transition list.

---

## 4. Medium-Severity Issues

### ISSUE-4: Flat prices return RSI=100 instead of RSI=50 [SEVERITY: MEDIUM]

**File:** `backend/app/core/rsi_engine.py`, line 191

**Description:** When all prices are identical (zero change), both `avg_gain` and `avg_loss` are 0.0. The function `_rsi_from_averages` checks `if avg_loss < 1e-10: return 100.0`, so RSI=100 is returned. The conventional value for a no-change scenario is RSI=50 (no directional bias). Wilder's original text does not explicitly define this case, but most charting platforms (TradingView, etc.) return 50 or display undefined.

**Impact:** In a low-volatility regime where prices barely move, the regime detector could classify the market as bullish (RSI=100 > 55), leading to false signals. This is unlikely to cause issues with real crypto data but is a mathematical inconsistency.

**Fix:** Add a check for `avg_gain < 1e-10 and avg_loss < 1e-10: return 50.0` before the existing `avg_loss < 1e-10` check.

---

### ISSUE-5: Backtester look-ahead bias in 4H bar alignment [SEVERITY: MEDIUM]

**File:** `backend/app/core/backtester.py`, lines 476-485

**Description:** `_find_closest_4h_index` finds bars where `bar.timestamp <= timestamp`. When a 1H bar has the same timestamp as a 4H bar, the 4H RSI includes that bar's close price. In real-time, that 4H bar would still be forming and its close would not yet be known.

Additionally, if a 1H bar occurs during the first 4H candle (e.g., at timestamp 1001 when the 4H bar opened at 1000), the function returns index 0, using RSI computed from that still-forming 4H candle.

**Impact:** The backtester may use future information (4H bar close) for regime decisions. In practice, this affects the exact boundary timestamps where 4H and 1H bars coincide, which happens once every 4 hours. The bias is small but systematic.

**Fix:** Use `bar.timestamp < timestamp` (strict less-than) or add a buffer to ensure only fully-completed 4H bars are used for regime decisions.

---

## 5. Low-Severity Findings

### FINDING-6: WebSocket ping task not canceled on reconnect [SEVERITY: LOW]

**File:** `backend/app/data/websocket_client.py`, line 171

Each reconnect creates a new `ping_task` without canceling the previous one. While the old task should exit when it detects `ws.closed`, there is a race condition: `self._ws` is reassigned at line 162 before the new ping task is created, so the old ping task could briefly see the new WebSocket and ping on behalf of the wrong connection context.

**Fix:** Add `if self._ping_task and not self._ping_task.done(): self._ping_task.cancel()` before line 171.

---

### FINDING-7: Backtester skips 15M exit processing for bars after last 1H bar [SEVERITY: LOW]

**File:** `backend/app/core/backtester.py`, lines 256-367

The main loop iterates over 1H bars and processes 15M bars within each iteration. Any 15M bars that occur after the last 1H bar are never evaluated for exits. The position is simply force-closed at the end.

**Fix:** After the 1H loop, process remaining 15M bars through the exit manager before force-closing.

---

### FINDING-8: Walk-forward warmup uses fragile index arithmetic [SEVERITY: LOW]

**File:** `backend/app/core/backtester.py`, lines 440-441

The warmup calculation `train_end // 4 - 50` assumes a fixed 4:1 ratio between 15M and 1H bars. If bars have gaps or misalignment, the warmup may be insufficient.

**Fix:** Use timestamp-based lookback instead of index arithmetic.

---

### FINDING-9: Risk manager exposure cap silently distorts position sizing [SEVERITY: LOW]

**File:** `backend/app/core/risk_manager.py`, lines 138-140

When `size_notional` exceeds remaining exposure, it is capped down. The final risk amount is then recalculated based on the capped size, which could be significantly less than the intended risk. This is logged nowhere and the caller has no way to know the sizing was reduced.

**Fix:** Add a boolean flag or warning in `PositionSizing` to indicate when the exposure cap was applied.

---

## 6. RSI Strategy Mathematical Verification

### Wilder's Smoothing Formula: VERIFIED CORRECT

The implementation correctly uses:
```
G_t = ((n-1) * G_{t-1} + U_t) / n
```

This is confirmed at line 95 of `rsi_engine.py`:
```python
avg_gain = (avg_gain * (period - 1) + gains[i]) / period
```

### RSI Formula: VERIFIED CORRECT

The code uses `RSI = 100 - 100/(1 + RS)` where `RS = avg_gain / avg_loss`. This is mathematically identical to `RSI = 100 * G/(G + L)` as specified:

```
100 - 100/(1 + G/L) = 100 - 100L/(L+G) = 100G/(G+L)
```

### Wilder's Original Book Example: VERIFIED

Using Wilder's sample data from "New Concepts in Technical Trading Systems" (1978, page 64):
- Seed avg_gain = 0.2386 (Wilder: 0.24) -- matches
- Seed avg_loss = 0.1000 (Wilder: 0.10) -- matches
- Seed RSI = 70.46 (Wilder: 70.46) -- matches exactly

### Incremental Update: VERIFIED

Incremental update from prior state matches full recalculation within floating-point precision (< 0.01).

### Edge Cases:
- Zero average loss (all gains): RSI = 100 -- CORRECT
- Zero average gain (all losses): RSI = 0 -- CORRECT
- Both zero (flat prices): RSI = 100 -- DEBATABLE (see ISSUE-4)
- Insufficient data: returns None -- CORRECT

---

## 7. Regime Detection: VERIFIED CORRECT

- Bullish: RSI_4H >= 55 -- CORRECT (uses >= per spec)
- Bearish: RSI_4H <= 45 -- CORRECT (uses <= per spec)
- Neutral: 45 < RSI_4H < 55 -- CORRECT
- Transition detection correctly identifies regime changes
- None values in series correctly break the transition chain

---

## 8. Signal Detection: VERIFIED CORRECT

- Long setup: Bullish regime + RSI_1H in [40, 48] -- CORRECT
- Long trigger: RSI_1H >= 50 (reclaim) -- CORRECT
- Short setup: Bearish regime + RSI_1H in [52, 60] -- CORRECT
- Short trigger: RSI_1H <= 50 (loses) -- CORRECT
- 15M confirmation: bullish candle for longs, bearish for shorts -- CORRECT
- Regime change resets detector state -- CORRECT
- Setup expiry after max_setup_bars -- CORRECT
- Signal strength scoring: depth + speed weighted 0.6/0.4 -- CORRECT

---

## 9. Exit Logic: VERIFIED CORRECT (in isolation)

- Hard stop checked first (highest priority) -- CORRECT
- Time stop at configurable max hold hours -- CORRECT
- Partial exit at 1.5R with 50% close -- CORRECT
- BE stop move at 1.0R -- CORRECT
- Trailing RSI exit (15M cross below 50 for longs, above 50 for shorts) -- CORRECT
- Trailing exit only activates after partial or BE move -- CORRECT

Note: The exit logic module itself is correct, but the backtester does not properly consume partial exit actions (see BUG-2).

---

## 10. Recommendations

### Immediate (Before Production)

1. **Fix BUG-1:** Change `False` to `None` in backtester line 372 to prevent crash on open positions.
2. **Fix BUG-2:** Implement partial exit handling in the backtester. This is essential for accurate backtest results.
3. **Fix BUG-3:** Add `CANCELED` to the OMS ACCEPTED state transitions.

### Short-Term (Before Live Trading)

4. **Add test coverage** for exit_logic, risk_manager, websocket_client, and oms modules. Current coverage has significant gaps.
5. **Fix ISSUE-4:** Handle the flat-prices edge case in `_rsi_from_averages` to return 50 instead of 100.
6. **Fix ISSUE-5:** Use strict less-than comparison in 4H bar alignment to prevent look-ahead bias.

### Medium-Term (Quality Improvement)

7. **Add integration tests** that run the full pipeline: RSI -> regime -> signal -> position -> exit -> PnL, with known expected outcomes.
8. **Add property-based tests** for the RSI engine (e.g., RSI always in [0, 100], monotonic prices produce monotonic RSI).
9. **Add logging/metrics** to the risk manager for when exposure caps are applied.
10. **Fix FINDING-6:** Cancel old ping tasks before creating new ones in WebSocket reconnect.

### Missing Test Files

The following modules have zero test coverage:
- `backend/app/core/exit_logic.py` -- critical for position management
- `backend/app/core/risk_manager.py` -- critical for capital safety
- `backend/app/data/websocket_client.py` -- critical for live data
- `backend/app/execution/oms.py` -- critical for order lifecycle
- `backend/app/data/candle_builder.py` -- used for data aggregation

