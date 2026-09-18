# Prediction-Market Statistical Arbitrage Engine
Research Findings, Live Results & Next Steps - 17 September 2026

## 1. Executive Summary
#### Strategy Status
The engine has been live since 14 August 2026. The current live sample contains 4 strategy trades, 8 executed orders and 8 fills, with +0.08% net P&L and -1.33% maximum drawdown. The live sample is too small to draw conclusions about persistent profitability; its primary value is validating the research and execution pipeline in live markets.

### 1.1. Objective
I built and deployed a live systematic trading engine for BTC and ETH prediction markets to test whether pricing inefficiencies can be identified and converted into executable trades after fees, liquidity, execution constraints and portfolio risk.

The research investigates two sources of edge:
#### a. Probability-based relative value
```
Estimating event probabilities from BTC and ETH options markets and
comparing calibrated estimates with executable prediction-market prices.
```

#### b. Structural arbitrage
```
Identifying deterministic pricing relationships across equivalent
contracts and across contracts whose payoffs impose monotonicity or other no-arbitrage constraints.
```
The research and trading architecture deliberately separates signal generation from execution. Opportunities are evaluated using executable bid/ask prices, fees, liquidity, position sizing, inventory constraints and portfolio-level capital allocation rather than relying on midpoint prices or theoretical spreads alone.

### 1.2. Key Research Findings
#### H1 - The probability signal contains information, but is not fully calibrated.
Options-derived touch probabilities generally preserve the ordering of event likelihood: higher predicted probabilities have tended to correspond to higher realized touch frequencies. However, the probability levels are not sufficiently calibrated to be interpreted directly as physical probabilities.

This led me to separate signal quality from probability calibration and treat the options-derived output as a risk-neutral-derived signal requiring calibration before being used for expected-value calculations.

#### H2 - Raw model-market dislocations have not demonstrated a stable predictive relationship.
I tested whether the magnitude of the model-market edge predicted subsequent prediction-market price movements over 1h, 4h, 24h, 72h and 1-week horizons.

The relationship was weak and non-monotonic across the tested horizons. Larger initial edges did not consistently produce larger subsequent moves in the expected direction.

I therefore do not currently treat raw model-market disagreement as standalone alpha. The next test is whether calibrated dislocations converge and generate positive executable returns after fees, spreads and slippage.

#### H3 - Cross-market arbitrage opportunities exist, but capital and execution constraints matter.
The engine identified a live BTC opportunity across two contracts representing the same $150,000 touch event. The post-fee executable cost was approximately $0.9989 against a $1.00 settlement value, implying approximately 11.2 bps theoretical edge across approximately 113 available pairs.

The opportunity was not deployed because capital was already committed elsewhere. This highlighted that theoretical arbitrage must be evaluated against execution probability, capital utilization and opportunity cost, not simply the quoted spread.

#### H4 - Vertical arbitrage produced a live position.
The engine identified a pricing inconsistency between ETH $5,500 and $6,000 touch contracts. Since touching $6,000 necessarily implies touching $5,500, YES $5,500 + NO $6,000 has a minimum settlement value of $1, subject to contract definitions and settlement rules.

The strategy entered 86 pairs at approximately $0.9958, creating an ex-ante theoretical edge of approximately 42 bps per pair. The remaining research is focused on realized settlement economics, liquidity, capital duration and execution risk.

### 1.3. What I Learned
The main lesson is:
```
A signal is not automatically an edge.
```

The project initially focused on whether I could identify pricing discrepancies. Live deployment shifted the research question toward whether those discrepancies survive the full trading process.

I now separate the strategy into three sources of uncertainty:
- Model: Is the probability estimate correct?
- Market: Is the price difference genuine relative value or explained by risk premia, liquidity or market structure?
- Execution: Can the theoretical edge actually be captured at the required price and size?

This has made the research more falsifiable and changed how I evaluate opportunities.

### 1.4. Current Research Priorities
1. Calibrate the probability signal
2. Re-test H2 out of sample
3. Improve structural arbitrage execution-realization modelling
4. Improve P&L attribution
5. Establish deployment criteria

The objective is not to maximize the current backtest or small live P&L sample. It is to establish whether each source of edge survives the full research chain:
```
       Hypothesis
            ↓
       Measurement
            ↓
Out-of-Sample Validation
            ↓
        Execution
            ↓
           Risk
            ↓
       Realized P&L
```

## 2. Research Objectives and Hypotheses
I separated the strategy into four hypotheses so that the underlying assumptions could be tested independently.

```
                 Trading Edge
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
 Probability-Based RV       Structural Arbitrage
          │                       │
     ┌────┴────┐             ┌────┴────┐
     │         │             │         │
    H1        H2             H3        H4
     │         │             │         │
Probability  Market       Cross-     Vertical
Estimation  Dislocation   Market     Arbitrage
     │         │             │         │
     └────┬────┘             └────┬────┘
          │                       │
          └───────────┬───────────┘
                      ↓
             Opportunity Filter
                      ↓
               Position Sizing
                      ↓
                  Execution
                      ↓
                     Risk
                      ↓
                Realized P&L
```

| Hypothesis | Strategy                   | Question                                                                  | Primary Risk                                |
|------------|----------------------------|---------------------------------------------------------------------------|---------------------------------------------|
| H1         | Probability Relative Value | Can options information provide useful estimates of event probabilities?  | Model and calibration error                 |
| H2         | Probability Relative Value	| Do model-market dislocations contain economically useful information?	    | Mispricing vs. model / risk-premium effects |
| H3         | Structural arbitrage	      | Do equivalent contracts trade at inconsistent executable prices?	        | Execution, liquidity and settlement	        | 
| H4         | Structural arbitrage	      | Do related contracts violate payoff-implied monotonicity?                 | Execution / liquidity                       |

This separation allows each source of edge to be evaluated independently rather than treating the overall strategy as a single alpha signal.

## 3. Current Portfolio & Live Trading Results

```
Live since:             2026-08-14
Strategy trades:        4
Executed orders:        8
Fills:                  8
Net P&L:                +0.08%
Max Drawdown:           -1.33%
```

A strategy trade represents one independent trading opportunity; multi-leg arbitrage positions are counted as one strategy trade, with each contract treated as a separate execution leg.

These results are from live trading and are not backtested. The live sample is too small to infer persistent profitability. Its primary purpose is to test whether the research assumptions survive executable prices, actual fills, fees, inventory and capital constraints.

The current portfolio contains both probability-based and structural positions.

#### Probability Relative Value
| Asset	| Contract	  | Outcome | Size	| Entry  |
|-------|-------------|---------|-------|--------|
| BTC	  | Touch $200k | NO	    | 4.87	| 98.23¢ |
| ETH	  | Touch $4.5k | NO	    | 4.95	| 96.27¢ |
| ETH	  | Touch $5.5k | NO	    | 4.91	| 97.11¢ |

These positions depend on the calibrated probability estimate and current executable market price.

#### Structural Arbitrage
| Asset	| Structure	                         | Size	| Entry          |
|-------|------------------------------------|------|----------------|
| ETH   | $5.5k Touch YES + $6k Touch NO     | 	86	| 99.58¢ / pair  |

The structural position is evaluated primarily through its payoff relationship, executable liquidation value, remaining capital requirement and opportunity cost.

#### Live equity / P&L curve
<img width="700" height="1300" alt="Equity Curve" src="https://github.com/Briansim74/Prediction-Markets-Statistical-Arbitrage-Engine/blob/main/equity_curve.png"/>

The sample is currently too small to infer long-term profitability or statistical significance.

I therefore do not interpret the current P&L as evidence either for or against a persistent trading edge.

Instead, live deployment has provided a test of whether the research assumptions survive contact with:
- executable prices
- actual fills
- fees
- inventory
- capital constraints
- order management
- portfolio accounting
- real-time market conditions

## 4. Dynamic Capital Allocation
I treat open positions as dynamic capital allocations rather than static trades.

Once a position has been entered, the entry price is no longer the primary decision variable.

The relevant question becomes:
```
Given the information available today, is holding the position
more valuable than liquidating it and redeploying the capital elsewhere?
```

Conceptually:
```
Value of holding > Value of liquidation + Value of best alternative use of capital
```

This prevents the strategy from becoming anchored to the original entry price.

The framework is particularly relevant for structural arbitrage, where the theoretical payoff may be attractive but capital can remain locked until settlement.

Therefore, expected return must be considered alongside:
- remaining time to expiry
- executable liquidation value
- liquidity
- capital utilization
- alternative opportunities

This converts position management from a simple profit/loss rule into a marginal capital-allocation problem.

## 5. Empirical Findings
### 5.1 H1 - The Probability Signal Contains Information but Is Not Fully Calibrated
The first research question was whether an options-implied risk-neutral distribution could provide useful information about the probability of a BTC or ETH price touching a specified barrier before expiry.

I constructed touch probabilities from the BTC and ETH options surfaces and evaluated them against realized first-passage events.

#### BTC model calibration curve
<img width="400" height="800" alt="BTC_model_calibration" src="https://github.com/Briansim74/Prediction-Markets-Statistical-Arbitrage-Engine/blob/main/BTC_model_calibration.png"/>

#### ETH model calibration curve
<img width="400" height="800" alt="ETH_model_calibration" src="https://github.com/Briansim74/Prediction-Markets-Statistical-Arbitrage-Engine/blob/main/ETH_model_calibration.png"/>

The model showed useful discrimination: higher predicted probabilities generally corresponded to higher realized touch frequencies.

However, the probabilities were not fully calibrated. For example, BTC predictions around 85% corresponded to approximately 78% realized frequency, while ETH predictions around 65% corresponded to approximately 55%.

This distinction is important:
#### Discrimination
```
Can the model distinguish more likely events from less likely events?
```
vs.

#### Calibration
```
Does a predicted probability correspond to the correct empirical frequency?
```
The current evidence is more supportive of the former than the latter.

The main potential sources of calibration error are:
- risk-neutral versus physical probability
- volatility-surface assumptions
- first-passage model misspecification
- stochastic volatility and jumps
- tail behaviour

The key research change was therefore to treat the options-derived probability as a probability signal, rather than assuming it is already a calibrated physical probability.

### 5.2. H2 - Market Dislocation
Once I had a probability signal, I asked whether the difference between the model and prediction-market price contained information about future market behaviour.

I defined:
```
Edge_t = P^_t - P_market_t
```
and grouped observations into ten edge buckets.

I then measured subsequent prediction-market price movement over 1h, 4h, 24h, 72h and 1-week horizons.

#### Convergence Check
<img width="700" height="1200" alt="edge_vs_move" src="https://github.com/Briansim74/Prediction-Markets-Statistical-Arbitrage-Engine/blob/main/edge_vs_move.png"/>

The current results do not show a stable monotonic relationship between initial edge and subsequent price movement.

At shorter horizons, average movements are generally close to zero. At longer horizons, some positive average movements appear, but larger initial edges do not consistently correspond to larger subsequent moves.

The current conclusion is therefore:
```
Raw model-market dislocation has not yet demonstrated
a stable predictive relationship with subsequent prediction-market price movement.
```
This does not establish that probability-based trading has no economic value. The current test uses raw probabilities and price movement rather than calibrated probabilities and executable trading returns.

The next test is therefore to distinguish:
```
Price Prediction
```
from:
```
Relative-Value Convergence
```
and ultimately from:
```
Executable Trading Return
```

### 5.3. H3 - Cross-Market Arbitrage
The cross-market arbitrage engine identified a live BTC opportunity involving two contracts representing the same underlying event:
```
Market A: “Will Bitcoin reach $150,000 by December 31, 2026?” — NO at approximately $0.977

Market B: “Will Bitcoin hit $150k by December 31, 2026?” — YES at approximately $0.019
```
The contracts appeared to represent equivalent payoff conditions. The engine therefore evaluated the complementary combination:

| Asset | Structure	                          | Size   | Entry          |
|-------|-------------------------------------|--------|----------------|
| BTC   | $150,000 Touch NO + $150k Touch YES | 113.32 | 99.89¢ / pair  |

The observed executable combination had a post-fee cost of approximately $0.9989 per pair, against a $1.00 settlement value:
```
Executable edge ≈ $0.00112 per pair (~11.2 bps)
```
Approximately 113 pairs were available, implying roughly $0.13 of theoretical profit if both legs could be fully executed at the quoted prices.

The opportunity was not deployed because existing capital was already committed to another structural position.

This highlighted an important distinction:
```
Theoretical arbitrage is not automatically executable arbitrage.
```
The relevant decision must incorporate:
- executable liquidity
- fill probability
- legging risk
- capital utilization
- time to settlement
- opportunity cost

### 5.4. H4 - Vertical Arbitrage
One example is the vertical relationship between ETH $5,500 and $6,000 touch contracts.

For an upward barrier, because touching $6,000 necessarily implies touching $5,500:
```
P(touch $5,500) ≥ P(touch $6,000)
```

The corresponding structure:
```
YES $5,500 + NO $6,000
```
has a minimum settlement value of $1, subject to contract definitions and settlement rules.

The strategy entered 86 pairs at approximately $0.9958, creating an initial post-fee executable edge of approximately 42 bps per pair.

This position provides a live test of whether a deterministic payoff relationship can be converted into realized economic return.

The remaining evaluation focuses on:
- execution
- liquidity
- capital duration
- capital utilization
- settlement
- realized P&L

## 6. What I Learned
The most important lesson from the project is:
```
A signal is not automatically an edge.
```

The project initially focused on finding pricing discrepancies. Live trading shifted the focus toward whether those discrepancies survive the full trading process.

I now separate three layers of uncertainty:

#### Model uncertainty
```
Is the estimated probability correct?
```
#### Market uncertainty
```
Does the prediction-market price actually represent a mispricing,
or is the discrepancy explained by risk premia, liquidity or other market structure?
```
#### Execution uncertainty
```
Can the theoretical opportunity actually be captured at the required price and size?
```

For probability-based strategies, model uncertainty is the dominant research problem.

For structural arbitrage, the engine already handles the first layer of implementation realism by using executable prices, available liquidity and post-fee economics. The remaining challenge is dynamic execution realization: whether those conditions remain available long enough to complete the required trade.

This decomposition has made the research more falsifiable.

For example:
- H1 can fail because the probability model is poorly calibrated.
- H2 can fail because model-market disagreement does not predict economically useful repricing.
- H3/H4 can fail because the observed executable edge does not survive multi-leg execution, capital constraints or settlement.

That distinction prevents a weak signal from being hidden by attractive theoretical economics, and prevents an attractive arbitrage relationship from being overstated without measuring its realized implementation cost.

## 7. Next Steps
### 7.1. Out-of-Sample Probability Calibration
Build an explicit calibration layer:
```
     Risk-Neutral Signal
              ↓
         Calibration
              ↓
Estimated Physical Probability
```

Candidate methods include isotonic, logistic and parametric calibration.

The calibration mapping will be estimated on an earlier period and frozen before out-of-sample evaluation.

### 7.2. Tail Calibration
Because the strategy often evaluates low-probability events, calibration will be tested specifically in:
```
0-1%
1-2%
2-5%
5-10%
```

I will evaluate calibration error, confidence intervals, sample size and stability across time and volatility regimes.

### 7.3. Re-test H2 After Calibration
The next H2 test will use:
```
Calibrated Edge = P^P - P_market
```

I will measure both:
```
Edge_t+h - Edge_t
```
and executable trading return.

This distinguishes whether a large initial discrepancy:
- converges
- persists
- widens
- or produces economically useful trading returns

The analysis will also normalize YES/NO direction and control for time-to-expiry, volatility, liquidity and contract type.

### 7.4. Improve Execution-Realization Modelling
The arbitrage engine already incorporates:
- executable ask prices
- available order-book liquidity
- trading fees
- maximum executable size

The next layer is to model whether the observed executable opportunity remains executable throughout the order lifecycle.

I will measure:
- quote persistence
- partial-fill frequency
- legging loss
- cancellation/replacement behaviour
- realized versus displayed liquidity
- capital duration
- return on committed capital

The goal is to move from:
```
  Theoretical Edge
          ↓
   Executable Edge
          ↓
   Realized Return
```
### 7.5. Improve P&L Attribution
Live P&L will be decomposed into:
- probability signal
- structural arbitrage
- spread
- fees
- slippage
- execution
- inventory
- model revisions
- 
This should identify where the strategy is actually creating or destroying value.

### 7.6. Establish Deployment Criteria
Before increasing capital allocation, I want explicit criteria for moving from research to deployment.

For probability-based trades:
- calibrated out-of-sample probabilities
- positive expected value after costs
- stability across time periods
- robustness across model specifications

For structural arbitrage:
- verified contract equivalence
- executable liquidity
- positive post-fee edge
- acceptable legging risk
- reliable settlement interpretation

The progression is:
```
      Research
          ↓
Historical Validation
          ↓
   Paper Trading
          ↓
Limited Live Deployment
          ↓
      Scaling
```

## 8. Falsification Criteria
The purpose of these criteria is to ensure that the research process can reject the strategy rather than continuously modifying it until historical results appear attractive.

#### 8.1. Probability Strategy
The hypothesis would be weakened if:
- out-of-sample calibration remains poor
- tail calibration is unstable
- calibrated dislocations do not converge or generate economic returns
- apparent edge disappears after realistic costs
- results are highly sensitive to modelling assumptions

#### 8.2. Structural Arbitrage
The opportunity would be weakened if:
- executable liquidity is insufficient
- partial fills materially reduce realized edge
- capital utilization dominates the theoretical return
- legging risk is too large
- settlement risk cannot be controlled

## 9. Conclusion
The project has not yet established a statistically convincing persistent trading edge. The live sample is too small to support that conclusion.

However, the research has produced several useful findings:
- The options-derived model contains information about relative event likelihood, but its raw probabilities are not fully calibrated.
- Model-market dislocations are measurable, but the current H2 analysis does not show a stable monotonic relationship between the size of the raw dislocation and subsequent prediction-market price movement.
- Structural pricing relationships can produce attractive arbitrage opportunities. The engine already evaluates these opportunities using post-fee executable prices and available liquidity, rather than theoretical midpoint prices. The remaining structural-arbitrage research question is therefore more specific: whether an opportunity that is executable in an order-book snapshot can be reliably converted into realized return once partial fills, capital duration and settlement are considered.

The next stage is therefore focused on calibration, out-of-sample validation, executable-return measurement and execution modelling.

The broader research framework is:
```
     Hypothesis
          ↓
     Measurement
          ↓
  Out-of-Sample Test
          ↓
      Execution
          ↓
        Risk
          ↓
     Realized PnL
```

The objective is not simply to find a strategy that looks profitable historically. It is to determine whether an apparent source of edge remains robust when exposed to realistic market conditions, costs and implementation constraints.
