# Prediction-Market Statistical Arbitrage Engine
Research Findings, Live Results & Next Steps - 17 September 2026

## 1. Executive Summary
I built and deployed a live systematic trading engine for BTC and ETH prediction markets, with the objective of testing whether pricing inefficiencies can be identified, quantified and executed after realistic transaction costs and portfolio constraints.

The system investigates two distinct sources of edge:
#### Probability-based relative value
Estimating event probabilities from BTC and ETH options markets and comparing calibrated estimates with executable prediction-market prices.

#### Structural arbitrage
Identifying deterministic pricing relationships across equivalent contracts and across contracts whose payoffs impose monotonicity or other no-arbitrage constraints.

The research and trading architecture deliberately separates signal generation from execution. Opportunities are evaluated using executable bid/ask prices, fees, liquidity, position sizing, inventory constraints and portfolio-level capital allocation rather than relying on midpoint prices or theoretical spreads alone.

The engine has been live since 14 August 2026. The current live sample contains 4 strategy trades, 8 executed orders and 8 fills. Live P&L remains a very small sample and is therefore not treated as evidence of a persistent trading edge. The current results are primarily useful as validation of the research, execution and portfolio-management pipeline.

The research has produced several findings.

First, the options-derived probability signal contains information about the relative likelihood of crypto price-touch events: higher predicted probabilities have generally corresponded to higher realized event frequencies. However, the raw probabilities are not fully calibrated, meaning that the model output cannot be directly interpreted as an unbiased physical probability. This makes probability calibration, particularly in the low-probability tail relevant to trading, a central research problem.

Second, model-market dislocations exist, but a difference between model probability and prediction-market price is not sufficient to establish mispricing. The discrepancy can reflect model error, risk-neutral versus physical probability differences, risk premia, liquidity or execution costs. The next stage is therefore focused on determining whether calibrated dislocations have predictive and economically meaningful subsequent behavior.

Third, the structural arbitrage engine identified a live cross-market BTC opportunity involving two contracts representing the same $150,000 price-touch event. The observed executable combination had a post-fee cost of approximately $0.9989 against a $1.00 settlement value, implying approximately 11.2 basis points of theoretical edge per matched pair. The available size was approximately 113 pairs, corresponding to roughly $0.13 of theoretical profit.

The important finding was not simply that the engine detected the discrepancy. Because existing capital was already committed to another structural arbitrage position, reallocating capital to the new opportunity was not attractive relative to the opportunity cost of closing or displacing the existing position. I therefore treated the opportunity as a detected theoretical/executable dislocation rather than automatically deploying capital into it.

This highlighted a broader principle in the system:

A positive arbitrage spread is not necessarily a positive portfolio decision.

For structural arbitrage, the relevant progression is:
```
     Pricing Dislocation
              ↓
        Post-Fee Edge
              ↓
       Executable Size
              ↓
       Execution Risk
              ↓
     Capital Requirement
              ↓
       Opportunity Cost
              ↓
Portfolio-Level Expected Return
```
This has changed the research question from:
```
Can the engine find pricing discrepancies?
```

to:
```

Can the engine identify discrepancies whose expected realized return
remains attractive after transaction costs, execution constraints, capital utilization and model uncertainty?

```
The main research priorities are now:
- Probability calibration: establish a genuinely out-of-sample mapping from options-derived risk-neutral signals to physical event probabilities.
- Tail validation: evaluate calibration specifically in the low-probability regions where the strategy is most likely to trade.
- Model decomposition: distinguish risk-neutral/physical probability effects from first-passage and volatility-model misspecification.
- Dislocation testing: measure whether calibrated model-market differences subsequently converge, persist or widen.
- Arbitrage economics: quantify the gap between theoretical and executable arbitrage through liquidity, fill probability, legging risk, capital duration and opportunity cost.
- P&L attribution: decompose realized performance into signal, structural arbitrage, fees, spread, slippage, execution and inventory effects.

The project has therefore evolved from building an opportunity scanner into testing a complete systematic trading hypothesis.

The current objective is not to maximize the apparent backtested or short-term live return. 

It is to establish whether each source of edge survives the full chain from market observation → statistical hypothesis → out-of-sample validation → executable trade → portfolio allocation → realized P&L.

At the current stage, the evidence supports continuing the research and measurement process, but is insufficient to establish a persistent trading edge.

## 2. Research Objectives and Hypotheses
The project investigates two distinct sources of trading edge in crypto prediction markets:
- probability-based relative value
- structural arbitrage

I separated each strategy into explicit research hypotheses so that the underlying assumptions could be tested independently.

### 2.1. Probability-Based Relative Value
#### 2.1.1. Hypothesis 1 - Probability Estimation
```

Can an options-implied risk-neutral distribution be transformed into a useful
estimate of the physical probability of a crypto price touching a specified barrier before expiry?

```
I first focused on the probability problem rather than immediately looking for trading opportunities.

I extracted information from BTC and ETH option surfaces and used it to estimate risk-neutral touch probabilities. I then evaluated these estimates against realized first-passage events using synthetic contracts.

The initial calibration analysis showed that the model contained useful information about relative event likelihood: higher predicted probabilities generally corresponded to higher realized touch frequencies.

However, the raw probabilities were not perfectly calibrated.

This led me to distinguish between ranking power and probability calibration. The model output appears useful as a probability signal, but it cannot automatically be interpreted as the true physical probability.

The research therefore treats the options-derived probability as:
```
  Risk-Neutral Probability
              ↓
      Probability Signal
              ↓
         Calibration
              ↓
Estimated Physical Probability
```
rather than assuming:
```
Risk-Neutral Probability = Physical Probability
```
This distinction became an important focus of the subsequent research.

#### 2.1.2. Hypothesis 2 - Market Dislocation
```

Does the prediction-market price differ sufficiently from the
estimated physical probability to create positive expected value after transaction costs?

```

Once I had established that the options-derived signal contained information about event likelihood, I considered the separate question of whether that information could be converted into a trading opportunity.

For each contract, I compared the calibrated physical probability:
```
P̂_P(YES)
```
with the executable prediction-market price.
```
P_market(YES)
```

For a YES position:
```
EV_YES = P̂_P(YES) - P_market(YES) - Fees - Expected Trading Costs
```

and analogously for NO:
```
EV_NO = P̂_P(NO) - P_market(NO) - Fees - Expected Trading Costs
```
The strategy only considers entering when the estimated expected value exceeds the minimum trading threshold.

This creates an important separation between model disagreement and tradable edge.

The system does not trade simply because:
```
P̂_P(YES) ≠ P_market(YES)
```
Instead, the discrepancy must be sufficiently large to compensate for transaction costs and the uncertainty in the probability estimate.

The resulting research pipeline is:
```
       Options Market
              ↓
  Risk-Neutral Probability
              ↓
         Calibration
              ↓
Physical Probability Estimate
              ↓
   Prediction-Market Price
              ↓
 Fee-Adjusted Expected Value
              ↓
       Trade / No Trade
```

### 2.2. Structural Arbitrage
The second strategy class does not depend on forecasting the probability of the underlying event.

Instead, it tests whether prediction-market prices violate deterministic relationships implied by contract definitions and payoff structures.

#### 2.2.1. Hypothesis 3 - Cross-Market Arbitrage
```

Do equivalent prediction-market contracts trade at sufficiently different
executable prices to create arbitrage opportunities after fees and execution costs?

```

The scanner searches for contracts across different markets that represent equivalent underlying events.

If two contracts have equivalent payoffs, their complementary YES/NO combinations should satisfy a no-arbitrage relationship.

For example:
```
BUY YES on Market A + BUY NO on Market B
```

If the two contracts are genuinely equivalent and the combined executable cost is less than the guaranteed settlement value:
```
Total Executable Cost < $1
```

then the theoretical minimum profit is:
```
Theoretical Profit = Guaranteed Settlement Value − Total Executable Cost
```

The scanner evaluates both directions:
```
YES(A) + NO(B)

YES(B) + NO(A)
```
after incorporating applicable trading fees.

The key research question, however, is not whether a theoretical price inequality exists.

It is whether the inequality remains executable after accounting for:
- available liquidity
- order-book depth
- partial fills
- legging risk
- stale quotes
- execution synchronization
- transaction costs
- capital constraints
- contract equivalence and settlement rules.

Therefore, the hypothesis distinguishes:
```
Theoretical Arbitrage
        ↓
Executable Arbitrage
        ↓
Realized Profit
```

rather than treating a displayed pricing discrepancy as automatically realizable P&L.

#### 2.2.2. Hypothesis 4 - Vertical Arbitrage
```

Do prediction-market contracts at different strikes violate
the monotonicity relationships implied by their underlying event structure?

```

For an upward barrier event, touching a higher strike necessarily implies touching every lower strike first.

Therefore, for:
```
K_lower < K_higher
```

the event probabilities must satisfy:
```
P(touch K_lower) ≥ P(touch K_higher)
```

This creates a structural relationship between the corresponding prediction-market contracts.

For example:
```
BUY YES $5,500 + BUY NO $6,000
```
If touching $6,000 necessarily implies touching $5,500, the combination has a minimum settlement value of $1 per matched pair, subject to the exact contract definitions and settlement rules.

The scanner therefore searches for situations where:
```
YES(K_lower) + NO(K_higher) < $1
```
after fees and at executable prices.

For downward barriers, the relationship is reversed. The scanner applies the corresponding payoff inequality to identify violations in the opposite direction.

The strategy effectively treats the set of related prediction-market contracts as a discrete option-like surface and searches for violations of monotonicity and other no-arbitrage constraints.

As with cross-market arbitrage, the research distinguishes between the theoretical payoff relationship and the ability to execute the required legs at sufficient size.

## 3. Strategy Architecture
The four hypotheses are implemented through two strategy components.

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
             Inventory Management
                      ↓
             Portfolio Accounting
                      ↓
                Realized P&L
```
The separation is deliberate.

| Hypothesis | Strategy                   | Source of Edge                             | Primary Risk                              |
|------------|----------------------------|--------------------------------------------|-------------------------------------------|
| H1         | Probability Relative Value | Options information → event probability	   | Model and calibration error               |
| H2         | Probability Relative Value	| Model probability vs market price	         | Mispricing vs. model/risk-premium effects |
| H3         | Structural arbitrage	      | Equivalent-contract pricing inconsistency	 | Execution, liquidity and settlement	     | 
| H4         | Structural arbitrage	      | Strike/payoff relationships                | Execution / liquidity                     |

The probability-based strategy is exposed primarily to probability-model error, while structural arbitrage is exposed primarily to execution, liquidity and settlement risk.

This decomposition also makes the research process more falsifiable: each hypothesis can be tested independently rather than treating the overall strategy as a single source of alpha.

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

## 5. Current Portfolio
The current portfolio contains both probability-based and structural positions.

#### Probability Relative Value
| Asset	| Contract	  | Outcome | Size	| Entry  |
|-------|-------------|---------|-------|--------|
| BTC	  | Touch $200k | NO	    | 4.87	| 98.23¢ |
| ETH	  | Touch $4.5k | NO	    | 4.95	| 96.27¢ |
| ETH	  | Touch $5.5k | NO	    | 4.91	| 97.11¢ |

These positions depend on the calibrated probability estimate and current executable market price.

#### Structural Arbitrage
| Asset	| Structure	             | Size	| Entry          |
|-------|------------------------|------|----------------|
| ETH   | $5.5k YES + $6k NO     | 	86	| 99.58¢ / pair  |

The structural position is evaluated primarily through its payoff relationship, executable liquidation value, remaining capital requirement and opportunity cost.

## 6. Live Trading Results
```
Live since:             2026-08-14
Strategy trades:        4
Executed orders:        8
Fills:                  8
Net P&L:                +0.08%
Max Drawdown:           -1.33%
```

These results are from live trading and are not backtested.

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

## 7. Empirical Findings
### 7.1 H1 - The Probability Signal Contains Information but Is Not Fully Calibrated
I tested the options-derived touch probabilities against realized first-passage events by grouping predictions into probability buckets and comparing average predicted probability with realized touch frequency.

#### BTC model calibration curve
<img width="400" height="800" alt="BTC_model_calibration" src="https://github.com/Briansim74/Prediction-Markets-Statistical-Arbitrage-Engine/blob/main/BTC_model_calibration.png"/>

#### ETH model calibration curve
<img width="400" height="800" alt="ETH_model_calibration" src="https://github.com/Briansim74/Prediction-Markets-Statistical-Arbitrage-Engine/blob/main/ETH_model_calibration.png"/>

The results indicate that higher predicted probabilities generally correspond to higher realized event frequencies.

This suggests that the model contains useful information about relative event likelihood.

However, the absolute probability levels are not fully calibrated.

For example:
```
BTC predictions around 85% corresponded to approximately 78% realized touch frequency;

ETH predictions around 65% corresponded to approximately 55% realized touch frequency.
```

The important distinction is therefore:

#### Discrimination
```
Can the model distinguish more likely events from less likely events?
```
vs.

#### Calibration
```
Does a predicted probability correspond to the correct empirical frequency?
```
The current evidence is more supportive of the first property than the second.

This matters directly for trading because a model can rank opportunities effectively while still producing biased estimates of expected value.

#### 7.1.1. Why the Probability Model May Be Miscalibrated
I do not currently attribute the observed calibration error to a single cause.

Several mechanisms are plausible.

#### 7.1.2. Risk-Neutral vs Physical Probability
Options markets provide information under the risk-neutral measure Q, whereas realized BTC and ETH paths occur under the physical measure P.

Therefore:
```
P_Q(touch) ≠ P_P(touch)
```
in general.

The options-derived probability should therefore initially be interpreted as a risk-neutral-derived trading signal, rather than assumed to be an unbiased physical probability.

The calibration results alone are not sufficient to determine how much of the observed error comes from this distinction.

#### 7.1.3. Model Misspecification
The conversion from an options surface into a touch probability introduces additional assumptions.

A simplified diffusion model may not fully capture:
- volatility clustering
- stochastic volatility
- jumps
- fat tails
- changing volatility regimes
- volatility skew
- volatility term structure

These effects are particularly relevant for touch events because they are path-dependent.

A model can therefore produce a reasonable terminal distribution while still generating inaccurate first-passage probabilities.

#### 7.1.4. Surface-to-Touch Transformation
The model does not directly observe a traded market probability for touching a barrier.

Instead, it performs a sequence of transformations:
```
      Option Prices
            ↓
Implied Volatility Surface
            ↓
       Distribution
            ↓
  Dynamic Assumptions
            ↓
First-Passage Probability
```
Each transformation introduces potential model risk.

This is likely to be particularly important for far-out-of-the-money barriers, where tail assumptions can have a large impact on estimated touch probabilities.

### 7.2. H2 - Model-Market Dislocations
The second research question was whether the probability signal identifies sufficiently large differences from prediction-market prices to generate positive expected value after costs.

#### Convergence Check
<img width="700" height="1200" alt="edge_vs_move" src="https://github.com/Briansim74/Prediction-Markets-Statistical-Arbitrage-Engine/blob/main/edge_vs_move.png"/>


The strategy therefore evaluates:
```
Calibrated Probability
        ↓
Executable Market Price
        ↓
Fee-Adjusted EV
        ↓
Trade / No Trade
```

A persistent model-market difference is not automatically interpreted as prediction-market mispricing.

Possible explanations include:
- probability-model misspecification
- risk-neutral versus physical probability differences
- risk premia
- prediction-market liquidity
- market-maker compensation
- execution costs
- differences in contract interpretation

The next research stage is therefore to determine whether model-market dislocations remain economically meaningful after probability calibration and out-of-sample validation.

### 7.3. H3 - Cross-Market Arbitrage Identified a Positive Post-Fee Pricing Dislocation
The cross-market arbitrage engine identified a live BTC opportunity involving two contracts representing the same underlying event:
```
Market A: “Will Bitcoin reach $150,000 by December 31, 2026?” - NO at approximately $0.977

Market B: “Will Bitcoin hit $150k by December 31, 2026?” - YES at approximately $0.019
```

The contracts appeared to represent equivalent payoff conditions. The engine therefore evaluated the complementary combination:

| Asset	| Structure	              | Size	 | Entry          |
|-------|-------------------------|--------|----------------|
| BTC   | $150,000 NO + $150k YES | 113.32 | 99.89¢ / pair  |

This produced a theoretical post-fee profit of approximately:
```
$0.001122 per pair
```

The observed opportunity supported the core H3 hypothesis that equivalent prediction-market contracts can temporarily trade at inconsistent executable prices.

However, the opportunity also exposed an important distinction between positive unit economics and attractive portfolio economics.

The maximum immediately executable size observed by the scanner was approximately 113.32 pairs, implying a theoretical gross profit of approximately $0.127 if both legs could be fully executed at the quoted prices.

At the time of detection, however, capital was already committed to an existing structural arbitrage position. Closing or reallocating that capital would have introduced an opportunity cost that was not justified by the relatively small incremental arbitrage return available from the new opportunity.

I therefore did not treat the detected discrepancy as automatically tradable.

This produced a more complete hierarchy for evaluating structural arbitrage:
```
  Quoted Pricing Dislocation
               ↓
   Post-Fee Theoretical Edge
               ↓
        Executable Size
               ↓
        Execution Risk
               ↓
      Capital Requirement
               ↓
        Opportunity Cost
               ↓
Expected Portfolio-Level Return
```

The key finding is that an arbitrage opportunity can satisfy the local no-arbitrage condition while still failing the portfolio-level trade-selection criterion.

This is particularly relevant in prediction markets because positions can remain capital-intensive until settlement. A strategy that evaluates only the profit per matched pair can therefore overstate the attractiveness of opportunities by ignoring capital duration and competing uses of balance-sheet capacity.

The H3 research question has consequently evolved from:
```
Can equivalent contracts be identified with prices below their guaranteed settlement value?
```

to:

```
Can equivalent-contract dislocations be executed at sufficient size and capital efficiency to produce attractive portfolio-level returns?
```

The current result provides evidence for the first question, while the second remains an open empirical question requiring further measurement of fill probability, capital utilization, holding period, legging risk and realized return on committed capital.

### 7.4. H4 - Structural arbitrage engine identified opportunities arising from relationships between related contracts.
One example is the vertical relationship between ETH $5,500 and $6,000 touch contracts.

Because touching $6,000 necessarily implies touching $5,500:
```
P(touch $5,500) ≥ P(touch $6,000)
```

A corresponding combination of:
```
YES $5,500 + NO $6,000
```
can have a minimum settlement value of $1 per matched pair, subject to contract definitions and settlement rules.

The key finding is that the theoretical payoff relationship and the executable trading opportunity are separate problems.

The theoretical structure may imply a guaranteed settlement value, but realizing the theoretical edge requires successfully acquiring the required legs at sufficient size.

The practical risks include:
- order-book depth
- partial fills
- legging
- stale quotes
- synchronization
- fees
- capital utilization
- settlement interpretation

The system therefore treats structural arbitrage signals as candidate opportunities, rather than assuming that every detected theoretical discrepancy represents realizable P&L.

## 9. What I Learned
The most important lesson from the project is:
```
A signal is not automatically an edge.
```

Instead, the full trading chain is:
```
     Signal
        ↓
   Probability
        ↓
   Calibration
        ↓
Market Discrepancy
        ↓
  Expected Value
        ↓
    Execution
        ↓
      Risk
        ↓
  Realized P&L
```

An error at any stage can turn an apparently attractive opportunity into a negative-expectancy trade.

I have therefore learned to separate three different sources of uncertainty:

#### 9.1. Model uncertainty
Is the estimated probability correct?

#### 9.2. Market uncertainty
Does the prediction-market price actually represent a mispricing, or is the discrepancy explained by risk premia, liquidity or other market structure?

#### 9.3. Execution uncertainty
Can the theoretical opportunity actually be captured at the required price and size?

This decomposition has made the research more falsifiable.

The initial question:
```
Can I find prediction-market mispricing using options information?
```

has evolved into three more precise questions:
```
Can the options surface provide useful information about event probabilities?

Can that signal be transformed into a calibrated physical probability?

Does the resulting probability identify executable opportunities with positive expected value after realistic costs?
```

## 10. Key Failure Case: Probability Calibration
The most important failure case identified so far is probability calibration.

The initial model output could not simply be interpreted as a physical probability.

The calibration analysis showed that predicted probabilities contained useful information about event likelihood, but the probability levels were systematically biased across parts of the distribution.

This means that:
```
Raw Model Probability - Prediction-Market Price
```
can overstate or understate the true expected value.

This is particularly important because the current strategy frequently evaluates very low touch probabilities.

Therefore, aggregate calibration across the full probability range is insufficient.

The next stage needs to establish calibration specifically in the region where the strategy actually trades, particularly approximately:
```
0-1%
1-2%
2-5%
5-10%
```
with appropriate confidence intervals and sufficient sample sizes.

## 11. Next Steps
#### 11.1. Out-of-Sample Calibration
The immediate priority is to construct an explicit calibration layer:
```
Risk-Neutral Probability
          ↓
Calibration Function
          ↓
Estimated Physical Probability
```

Candidate approaches include:
- isotonic regression
- logistic calibration
- parametric calibration
- regime-conditioned calibration

The calibration mapping will be estimated using an earlier historical period and then frozen before evaluation on a genuinely out-of-sample period.

The objective is to avoid fitting the calibration layer to the same observations used to evaluate it.

#### 11.2. Tail Calibration
Because the strategy frequently evaluates low-probability events, I will focus specifically on:
- 0-1%
- 1-2%
- 2-5%
- 5-10%

For each region I want to evaluate:
- calibration error
- confidence intervals
- sample size
- stability across time
- stability across volatility regimes

The goal is to determine whether the model remains useful in the probability region that actually generates trades.

#### 11.3. Separate Q-to-P Effects from Model Misspecification
I want to determine whether calibration error is primarily caused by:
```
Risk-Neutral → Physical Measure Difference
```

or:
```
Model / First-Passage Misspecification
```

Potential experiments include:
- using the full volatility smile
- incorporating volatility skew and term structure
- testing stochastic-volatility specifications
- testing jump-aware models
- comparing alternative first-passage formulations
- conditioning calibration on volatility regime

The objective is not to add complexity for its own sake.

Each modelling change should be evaluated based on out-of-sample improvement.

#### 11.4. Test Whether Dislocations Converge
After calibration, I want to measure the subsequent behavior of model-market discrepancies.

For each opportunity:
```
Calibrated Probability
          ↓
    Market Price
          ↓
Observed Future Price
```

I want to measure whether the discrepancy:
- converges
- persists
- widens

behaves differently across market regimes.

I would evaluate multiple holding horizons rather than assuming immediate convergence.

This should help distinguish genuine relative-value opportunities from persistent differences caused by model assumptions or market structure.

#### 11.5. Improve P&L Attribution
The live system should attribute P&L across separate sources:
- Probability Signal
- Structural Arbitrage
- Fees
- Spread
- Slippage
- Execution
- Inventory
- Model Revisions

The objective is to answer:
```
Where is the strategy actually making or losing money?
```
Aggregate P&L alone does not answer this question.

#### 11.6. Improve Execution Modelling
For structural arbitrage, I want to quantify the difference between theoretical and executable edge.

Key measurements include:
- available order-book depth
- fill probability
- time between legs
- partial-fill frequency
- adverse selection
- stale-quote frequency
- capital utilization

An opportunity should only be classified as executable arbitrage when its expected realized economics remain attractive after these constraints.

#### 11.7. Establish Deployment Criteria
Before increasing capital allocation, I want explicit criteria for moving from research to deployment.

For probability-based trades:
- calibrated out-of-sample probabilities
- positive expected value after costs
- stability across time periods
- robustness across model specifications
- controlled drawdown and tail risk

For structural arbitrage:
- verified contract equivalence
- executable liquidity
- positive post-fee edge
- acceptable legging risk
- reliable settlement interpretation

This creates a progression:
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

## 12. Falsification Criteria
A key part of the next stage is defining what evidence would cause me to reject or materially revise the current hypotheses.

#### 12.1. Probability Strategy
The hypothesis would be weakened if:
- out-of-sample calibration remains poor after reasonable calibration methods
- tail calibration remains unstable
- model-market dislocations do not show economically meaningful subsequent behavior
- apparent edge disappears after realistic fees and execution costs
- results are highly sensitive to small modelling assumptions

#### 12.2. Structural Arbitrage
The opportunity would be weakened if:
- executable liquidity is insufficient
- partial fills materially reduce realized edge
- capital utilization dominates the theoretical return
- legging risk is too large
- settlement or contract-definition risk cannot be controlled sufficiently

The purpose of these criteria is to ensure that the research process can reject the strategy rather than continuously modifying it until historical results appear attractive.

## 13. Conclusion
The project has not yet established a statistically convincing persistent trading edge. 

The current live sample is too small to support that conclusion.

It has, however, produced several useful empirical and engineering findings.

The options-derived model appears to contain information about the relative likelihood of barrier-touch events, but its raw probabilities are not fully calibrated.

Prediction-market prices can differ materially from those estimates, but a model-market discrepancy does not by itself establish mispricing.

Structural relationships between prediction-market contracts can produce theoretically attractive arbitrage opportunities, but execution, liquidity, synchronization and settlement constraints determine whether those opportunities are economically realizable.

The next stage of research is therefore focused on:
- improving probability calibration
- validating calibration out of sample
- understanding the source of calibration error
- focusing specifically on the low-probability tail relevant to trading
- testing whether calibrated model-market dislocations exhibit economically meaningful behavior
- improving execution and P&L attribution

The broader objective is not simply to produce a higher historical return.

It is to establish a research process in which a trading hypothesis can be:
```
    Hypothesized
          ↓
      Measured
          ↓
Tested Out-of-Sample
          ↓
      Executed
          ↓
      Monitored
          ↓
Falsified or Supported
```

That framework is ultimately more important than the current small live P&L sample.

It provides a disciplined process for determining whether an apparent statistical relationship represents a robust and executable source of trading edge.

## Appendix
Trading Journal
