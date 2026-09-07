# Prediction-Markets-Statistical-Arbitrage-Engine
A live systematic trading engine for identifying and executing pricing inefficiencies in crypto prediction markets.

The system combines two sources of trading edge:
- Structural arbitrage - identifying cross-market and vertical pricing inconsistencies implied by contract payoff relationships.
- Probability-based relative value - comparing prediction-market prices with event probabilities estimated from crypto options-implied distributions.

Opportunities are evaluated at executable prices after fees and transaction costs, then passed through position sizing, risk, execution, inventory management, and portfolio accounting.

Currently focused on BTC and ETH price-event contracts.

## Live Trading
```
Live since:             2026-08-14
Strategy trades:        4
Executed orders:        8
Fills:                  8
Net P&L:                -0.03%
Max Drawdown:           -1.33%
```

Strategy trade:
- One independent trading opportunity / position.
- A multi-leg arbitrage is counted as one strategy trade, with each contract treated as a separate leg.

Results shown are from live trading and are not backtested. 

The strategy is actively under development, with ongoing evaluation of execution, probability calibration, and risk management.

## System Overview
A live systematic trading system that identifies and executes pricing inefficiencies in crypto prediction markets.

The system attempts to identify pricing discrepancies large enough to survive transaction costs, execution friction, model uncertainty, and position risk.

```
                 Prediction Markets
                         │
                         ▼
                   Market Scanner
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
    Probability RV Engine     Arbitrage Engine
              │                     │
              ▼                     ├── Cross-Market
       Model Probability            │
              │                     └── Vertical
              ▼
       Market Comparison
              │
              └──────────┬──────────┘
                         ▼
                  Fee-Adjusted EV
                         │
                         ▼
                  Trade Selection
                         │
                         ▼
                     Execution
```

## Trading Framework
The trading engine currently evaluates two primary forms of opportunity:

### 1. Arbitrage
### a. Cross-Market Arbitrage
The scanner also searches for arbitrage between prediction-market contracts representing the same underlying event structure.

For contracts with equivalent payoff conditions, the system compares the cost of constructing complementary outcomes across two markets.

For example:
```
BUY YES on Market A
        +
BUY NO on Market B
        ↓
Total Cost < $1
        ↓
Theoretical Locked-In Profit
```

If both positions collectively guarantee a $1 payout while their fee-adjusted acquisition cost is below $1:
```
Theoretical locked-in profit = Guaranteed Settlement Value - Total Cost
```

Realized P&L can differ because the theoretical arbitrage depends on successfully executing all required legs.

The scanner evaluates both directions:
```
YES(A) + NO(B)
YES(B) + NO(A)
```
after incorporating the applicable trading fees.

This allows the system to detect pricing inconsistencies across contracts without requiring a directional view on BTC or ETH.

### b. Vertical Arbitrage
The scanner also evaluates the logical ordering of contracts with different strikes.

For an upward barrier event, a lower strike should be at least as likely to be reached as a higher strike:
```
P(S touches K_lower) ≥ P(S touches K_higher)
```
Therefore, for two contracts with:
```
K_lower < K_higher
```

the system searches for situations where:
```
YES(K_lower) + NO(K_higher) < $1
```

after fees.

The resulting payoff is bounded such that at least one of the two contracts must resolve YES.
```
Lower Strike YES
        +
Higher Strike NO
        ↓
Theoretical Locked-In Profit
```

For downward events, the direction is reversed:
```
Lower Strike NO
        +
Higher Strike YES
```
The scanner evaluates adjacent strikes across the available contract surface and records opportunities where the combined executable cost is below the guaranteed payout.

This effectively treats the prediction-market contract set as a discrete option surface and searches for violations of monotonicity / no-arbitrage relationships.

### 2. Probability-Based Relative Value
External crypto derivatives markets are used to estimate the probability of prediction-market events.

```
    BTC / ETH Options
            │
            ▼
    Volatility Surface
            │
            ▼
Risk-Neutral Distribution
            │
            ▼
Touch / Expiry Probability
            │
            ▼
 Prediction Market Price
            │
            ▼
Fee-Adjusted Expected Value
            │
            ▼
     Position Sizing
```
A pricing discrepancy is not necessarily a trading opportunity.

The strategy does not trade simply because the options market and prediction market disagree.

The estimated probability must produce sufficient expected value at the executable bid/ask price after fees.


## Edge Decomposition
The strategy's edge can therefore be decomposed into two distinct mechanisms:
```
                 Trading Edge
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
 Probability Relative    Structural Arbitrage
        Value                     │
          │                       │
  P_model - P_market      Payoff Inequality
          │                       │
          ▼                       ▼
   Expected Value     Theoretical Locked-In Profit
          │                       │
          └───────────┬───────────┘
                      ▼
              Transaction Costs
                      │
                      ▼
                Realizable Edge
```
For probability-based trades, the key uncertainty is model probability error.

For arbitrage trades, the key risks are primarily execution, liquidity, settlement interpretation, and synchronization across legs.

The system therefore treats the two strategies differently rather than forcing arbitrage opportunities through the probability model.

## Signal Generation
The system uses external crypto derivatives data to construct a volatility surface for BTC and ETH.

Current market inputs include:
- Deribit
- OKX
- Bybit

The volatility surface is used to estimate the probability distribution of the underlying asset at different strikes and expiries.
```
     BTC / ETH Options
             │
             ▼
   Volatility Observations
             │
             ▼
    Volatility Surface
             │
             ▼
IV at Market Strike / Expiry
             │
             ▼
      Probability Model
             │
             ▼
Prediction Market Fair Value
```

The key idea is that the prediction market and crypto derivatives markets contain different pieces of information.

The prediction market provides the contract price.

The options market provides information about the distribution of future prices.

The trading strategy attempts to exploit discrepancies between the two.

## Fair Value Estimation
The system currently distinguishes between two types of crypto prediction contracts.

### Touch Events
Contracts where the underlying asset needs to reach a particular level at any point before expiry. Behaves like a synthetic binary barrier touch option.

Examples:
```
Will BTC reach $120,000 before December 25?

Will ETH fall to $2,500 before expiry?
```
The system estimates:
```
P(touch)
```

using the underlying price, volatility and time to expiry.

### Expiry Events
Contracts where the underlying must finish above or below a strike at expiry. Behaves like a synthetic European vanilla call/put option.

Examples:
```
Will BTC be above $120,000 on December 25?

Will ETH finish below $3,000?
```
The system estimates:

```
P(S_T > K)
```
or
```
P(S_T < K)
```
depending on the contract direction.

### Probability → Price
A prediction-market YES contract can be interpreted approximately as:
```
P_market = P_P(YES)
```

For example:
```
YES ask = $0.38
```
implies a physical market probability of approximately:
```
P_P(YES) = 38%
```

If the model estimates:
```
P(YES) = 48%
```

there is potentially a meaningful pricing discrepancy.

But the system does not trade on probability difference alone.

It calculates the actual expected value of the executable trade.

## Signal Calibration
The probability layer is treated as a trading signal rather than an assumption of perfect physical probabilities.

Options-implied probabilities are risk-neutral quantities and are not assumed to equal physical probabilities. The system therefore treats the options-derived probability as a trading signal and applies calibration before using it for fair-value estimation.

Calibration analysis showed that higher model probabilities corresponded to higher realized event frequencies, while raw probabilities were not perfectly calibrated.

Therefore, the strategy distinguishes between:
```
   Risk-Neutral Probability
              ↓
       Probability Signal
              ↓
         Calibration
              ↓
Estimated Physical Probability
```

## Trade Selection
Once a probability estimate is available, the strategy evaluates whether the prediction market is sufficiently mispriced to trade.

For a YES position:
```
P_model(YES)
        -
Executable YES Price
        -
Trading Costs
        =
Expected Value
```

For a NO position:
```
P_model(NO)
        -
Executable NO Price
        -
Trading Costs
        =
Expected Value
```
The system only considers entering when the estimated edge exceeds the minimum trading threshold.

This separates the probability problem from the trade-selection problem:
```
Probability Estimation
        ↓
Market Comparison
        ↓
Fee-Adjusted EV
        ↓
Trade / No Trade
```

## Entry Logic
The current strategy requires:
```
ENTRY_EV_THRESHOLD = 0.01
```
meaning the system requires approximately 1% expected value per contract before considering a new position.

Conceptually:
```
  Model Probability
          │
          ▼
Executable Market Price
          │
          ▼
   Fee-Adjusted EV
          │
          ▼
EV > Entry Threshold?
         / \
       NO   YES
       │     │
     SKIP   TRADE
```
This prevents the system from deploying capital into marginal opportunities.

## Fractional Kelly Position Sizing & Risk
Position sizing is based on Kelly sizing with a conservative fractional allocation.

Current configuration:
```
FRACTION = 0.25
```

The system calculates a Kelly allocation from expected value and then uses only a fraction of the theoretical Kelly position.

This provides a balance between:
- maximizing capital efficiency
- controlling model uncertainty
- avoiding excessive concentration
- surviving probability-estimation errors

The resulting allocation is additionally constrained by a maximum position limit.

## Execution
Once a trade passes the relevant opportunity and risk checks, the system converts the desired allocation into contracts:
```
     Dollar Allocation
             │
             ▼
      Contract Price
             │
             ▼
      Number of Shares
             │
             ▼
Exchange Size Normalization
             │
             ▼
     Tick-Size Rounding
             │
             ▼
        Limit Order
```

Orders are currently submitted as:
- BUY
- GTC
- LIMIT

The system records the resulting order ID and maintains an internal order ledger.

For multi-leg arbitrage, execution risk becomes particularly important.

A theoretical arbitrage is only realizable if both legs can be acquired at the assumed prices and sizes.

Therefore, the scanner treats the displayed arbitrage opportunity as a candidate and the execution layer is responsible for:
- available liquidity
- executable size
- order synchronization
- partial fills
- stale quotes
- legging risk
- capital availability

This distinction prevents a quoted theoretical arbitrage from being treated as automatically realizable P&L.

### Inventory & Exit Management
Open probability-based positions are continuously re-evaluated.
```
   Current Position
           │
           ▼
  Current Market Price
           │
           ▼
Recalculate Probability
           │
           ▼
Recalculate Expected Value
           │
           ▼
     Hold or Exit
```

Current exit threshold:
```
EXIT_EV_THRESHOLD = -0.02
```
If the expected value of continuing to hold the position deteriorates sufficiently, the system generates an exit signal.

The relevant question is not:
```
Did I buy this at a good price?
```
It is:
```
Given current information, is holding this position still better than exiting?
```
This allows capital to be recycled toward stronger opportunities.

### Arbitrage vs. Directional Positions
The system deliberately separates structural arbitrage from probability-based directional positions.

| Strategy                   | Source of Edge                             | Probability Model Required	   | Primary Risk           |
|----------------------------|--------------------------------------------|--------------------------------|------------------------|
| Probability Relative Value | Model probability vs market price	        | Yes	                           | Model error            |
| Cross-Market Arbitrage	   | Equivalent-contract pricing inconsistency	| No	                           | Execution / liquidity  |
| Vertical Arbitrage	       | Strike/payoff ordering inconsistency	      | No                             | Execution / settlement |
| Inventory Management	     | Dynamic repricing                          |	Yes for model-driven positions | Opportunity cost       |

This separation is important because the strategies have fundamentally different risk profiles.

A probability trade can be wrong because the estimated probability is wrong.

A structural arbitrage trade can have a positive theoretical payoff without knowing the probability of the underlying event, but can still fail to realize the theoretical edge because of execution, liquidity, partial fills, or incorrect assumptions about contract equivalence.


## P&L & Position Accounting
Executed trades are stored as fills rather than treating API positions as the complete source of truth.

The system reconstructs positions from the historical fill ledger.
```
       Trades
          │
          ▼
Chronological Ordering
          │
          ▼
   FIFO Matching
          │
          ├── Open Lots
          │
          └── Closed Lots
                  │
                  ▼
              Realized P&L
```
For every token, BUY lots are maintained in a FIFO queue.

SELL executions consume those lots sequentially.

This produces:
- current position
- cost basis
- average entry
- realized P&L
- realized shares
- realized fees

This makes portfolio accounting independent of the current exchange position snapshot.

## Mark-to-Market
Open positions are continuously marked against current executable bids.

For each position:
```
Market_Value = Shares * Current_Bid
```

and:
```
Unrealized_PnL = Market_Value − Cost_Basis
```

The portfolio therefore maintains both:
```
Realized_PnL + Unrealized_PnL
```

rather than relying only on settled trades.

## Portfolio Monitoring
Portfolio equity is calculated as:
```
Equity = Cash + Market_Value
```

The system records periodic equity snapshots containing:
- timestamp
- cash
- market value
- equity
- realized PnL
- unrealized PnL
- daily return
- max drawdown

This creates a persistent performance history for evaluating the trading strategy.

## Trading Philosophy
The project is built around several principles:

#### Probability first
The system attempts to quantify the probability of the event rather than trade purely on market momentum.

#### Trade the discrepancy
The objective is not to predict the market in isolation.

It is to identify:
```
P_model ≠ P_market
```

with enough margin to justify taking risk.

#### Exploit structural relationships

Related prediction contracts can contain arbitrage opportunities even without forecasting the underlying asset.

#### Price execution matters
The strategy evaluates executable bid/ask prices rather than relying exclusively on midpoints.

#### Fees are part of the signal
An edge that disappears after fees is not an edge.

#### Guaranteed does not mean executable
An arbitrage relationship may guarantee a payoff theoretically, but the realized trade still depends on liquidity, order-book depth, fill synchronization, and contract interpretation.

#### Position sizing matters
A good forecast with excessive sizing can still produce a bad trading strategy.

#### Inventory is dynamic
Existing positions are continuously reevaluated as market prices, volatility and time-to-expiry change.

#### Capital should move toward the best opportunities
The portfolio is treated as a dynamic allocation problem rather than a collection of independent bets.

## Complete Trading Loop
The live trading workflow is:
```
1. Load Portfolio State
        │
2. Build Volatility Surface
        │
3. Pull Prediction Markets
        │
4. Scan Crypto Contracts
        │
5. Pull Order Books
        │
6. Estimate IV
        │
7. Estimate Event Probability
        │
8. Calculate Fee-Adjusted EV
        │
9. Scan Cross-Market Arbitrage
        │
10. Scan Vertical Arbitrage
        │
11. Synchronize Fills
        │
12. Reconstruct Portfolio
        │
13. Synchronize Orders
        │
14. Manage Existing Orders
        │
15. Mark Positions to Market
        │
16. Calculate Equity
        │
17. Manage Existing Inventory
        │
18. Rank New Opportunities
        │
19. Submit Orders
        │
20. Persist Trading State
        │
21. Repeat
```

The system is designed as a closed-loop trading process: market data generates opportunities, opportunities are filtered through execution and risk constraints, trades update portfolio state, and portfolio state feeds back into subsequent decisions.
