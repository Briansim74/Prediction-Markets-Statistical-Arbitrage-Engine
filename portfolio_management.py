import os
import uuid
import numpy as np
import pandas as pd
from collections import deque
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

class Portfolio():

    def sync_fills(self, api, fills_df):

        def get_all_trades(api):
            all_trades = []
            next_cursor = None

            while True:
                response = api.trades(next_cursor=next_cursor)

                trades = response.get("trades", [])
                all_trades.extend(trades)

                next_cursor = response.get("next_cursor")

                # Stop if no trades
                if not trades:
                    break

                # "LTE=" is the terminal cursor returned by this API
                if not next_cursor or next_cursor == "LTE=":
                    break

            return all_trades

        new_fills = []
        all_trades = get_all_trades(api)

        for trade in all_trades:
            # print(trade)

            fill_id = trade["id"]

            if fill_id in fills_df["fill_id"].values:
                continue

            new_fills.append({
                "fill_id": fill_id,
                "order_id": trade["taker_order_id"] if trade["trader_side"] == "TAKER" else trade["maker_orders"][0]["order_id"],
                "condition_id": trade["market"],
                "token_id": trade["asset_id"],
                "outcome": trade["outcome"],
                "side": trade["side"],
                "price": float(trade["price"]),
                "shares": float(trade["size"]),
                "fee": float(trade["fee"]),
                "timestamp": pd.to_datetime(int(trade["match_time"]), unit="s", utc=True),
            })

        # Nothing new
        if not new_fills:
            return fills_df

        def get_question(trade):
            return api.market_detail(trade["condition_id"])["question"]

        with ThreadPoolExecutor(max_workers=30) as executor:
            questions = list(executor.map(get_question, new_fills))

        new_fills = pd.DataFrame(new_fills)
        new_fills["question"] = questions

        # Append new rows
        fills_df = pd.concat([fills_df, new_fills], ignore_index=True)
        fills_df["timestamp"] = fills_df["timestamp"] = (pd.to_datetime(fills_df["timestamp"], utc=True).astype("datetime64[ms, UTC]"))
        fills_df = fills_df.sort_values("timestamp")

        return fills_df


    # Doesnt cancel filled orders, historical order ledger
    def sync_orders(self, api, orders_df, fills_df):

        # 1. Sync currently active orders
        api_orders = api.list_orders()

        for order in api_orders["orders"]:

            order_id = order["id"]
            mask = orders_df["order_id"] == order_id

            if not mask.any():

                order_row = {
                    "order_id": order_id,
                    "condition_id": order.get("market"),
                    "token_id": order.get("asset_id"),
                    "outcome": None,
                    "side": order.get("side"),
                    "price": order.get("price"),
                    "requested_size": order.get("original_size"),
                    "filled_size": float(order.get("size_matched", 0)),
                    "remaining_size": (
                        float(order.get("original_size", 0))
                        - float(order.get("size_matched", 0))
                    ),
                    "status": order.get("status"),
                    "created_at": order.get("created_at"),
                    "cancelled_at": None,
                }

                orders_df = pd.concat(
                    [orders_df, pd.DataFrame([order_row])],
                    ignore_index=True
                )

            else:
                idx = orders_df.index[mask][0]

                orders_df.loc[idx, "status"] = order.get("status")
                orders_df.loc[idx, "filled_size"] = float(
                    order.get("size_matched", 0)
                )
                orders_df.loc[idx, "remaining_size"] = (
                    float(order.get("original_size", 0))
                    - float(order.get("size_matched", 0))
                )

        # ---------------------------------------------------------
        # 2. Reconcile fills BY ORDER ID
        # ---------------------------------------------------------
        fills_by_order = (fills_df.groupby("order_id")["shares"].sum())

        for order_id, filled_size in fills_by_order.items():

            mask = orders_df["order_id"] == order_id

            # Fill belongs to an order we don't currently have locally
            if not mask.any():
                print(f"Warning: fill for unknown order {order_id}")
                continue

            idx = orders_df.index[mask][0]

            filled_size = float(filled_size)

            orders_df.loc[idx, "filled_size"] = filled_size

            requested_size = orders_df.loc[idx, "requested_size"]

            if pd.notna(requested_size):

                requested_size = float(requested_size)

                orders_df.loc[idx, "remaining_size"] = max(requested_size - filled_size, 0)

                if filled_size >= requested_size:
                    orders_df.loc[idx, "status"] = "FILLED"

                elif filled_size > 0:
                    orders_df.loc[idx, "status"] = "PARTIALLY_FILLED"

        return orders_df
    

    #FIFO matching
    def reconstruct_positions_fifo(self, fills_df):
        """
        Reconstruct current Polymarket positions using FIFO.

        Expected fills_df columns:
            trade_id
            order_id
            condition_id
            token_id
            outcome
            side
            price
            shares
            fee
            timestamp

        Returns:
            positions_df:
                Current open positions with FIFO cost basis.

            realized_df:
                Realized P&L from SELL trades.
        """

        positions = []

        # Process each token independently.
        for token_id, trades in fills_df.groupby("token_id", sort=False):

            # FIFO queue of open BUY lots.
            # Each lot contains:
            #   remaining shares
            #   price
            #   fee_per_share
            buy_lots = deque()

            realized_pnl = 0.0
            realized_shares = 0.0
            realized_fees = 0.0

            # Very important: process chronologically.
            trades = trades.sort_values("timestamp")

            for _, trade in trades.iterrows():

                side = trade["side"]
                shares = float(trade["shares"])
                price = float(trade["price"])
                fee = float(trade["fee"])

                if side == "BUY":

                    # Store this BUY as a FIFO lot.
                    fee_per_share = fee / shares

                    buy_lots.append({
                        "shares": shares,
                        "price": price,
                        "fee_per_share": fee_per_share,
                    })

                elif side == "SELL":

                    remaining_to_sell = shares
                    sell_fee_per_share = fee / shares

                    while remaining_to_sell > 0:

                        if not buy_lots:
                            print(f"SELL exceeds available position for token_id={token_id}")
                            raise ValueError(f"SELL exceeds available position for token_id={token_id}")

                        lot = buy_lots[0]

                        matched_shares = min(remaining_to_sell, lot["shares"])

                        # Cost of the shares being sold.
                        buy_cost = (matched_shares * lot["price"])

                        # Allocate the original BUY fee
                        # to the shares being sold.
                        buy_fee = (matched_shares * lot["fee_per_share"])

                        # Proceeds from the SELL.
                        sell_proceeds = (matched_shares * price)

                        # Allocate SELL fee to this FIFO match.
                        sell_fee = (matched_shares * sell_fee_per_share)

                        # Realized P&L.
                        pnl = (sell_proceeds - sell_fee - buy_cost - buy_fee)

                        realized_pnl += pnl
                        realized_shares += matched_shares
                        realized_fees += buy_fee + sell_fee

                        # Reduce the FIFO lot.
                        lot["shares"] -= matched_shares
                        remaining_to_sell -= matched_shares

                        # Remove empty lot.
                        if lot["shares"] <= 1e-12:
                            buy_lots.popleft()

            # --------------------------------------------------
            # Remaining BUY lots = current position
            # --------------------------------------------------
            remaining_shares = sum(lot["shares"] for lot in buy_lots)

            if remaining_shares <= 0:
                continue

            remaining_cost = sum(lot["shares"] * (lot["price"] + lot["fee_per_share"]) for lot in buy_lots)

            avg_entry_price = (remaining_cost / remaining_shares)

            # Use the first trade for metadata.
            first_trade = trades.iloc[0]

            positions.append({
                "question": first_trade["question"],
                "condition_id": first_trade["condition_id"],
                "token_id": token_id,
                "outcome": first_trade.get("outcome"),
                "shares": remaining_shares,
                "cost_basis": remaining_cost,
                "avg_entry_price": avg_entry_price,
                "realized_pnl": realized_pnl,
                "realized_shares": realized_shares,
                "realized_fees": realized_fees,
            })

        positions_df = pd.DataFrame(positions)

        return positions_df


    def reconcile_positions(self, api, positions_df):

        def check_position(row):
            token_id = row["token_id"]

            balance = api.balance(
                asset_type="conditional",
                token_id=token_id
            )

            live_shares = float(balance["balance"])
            recorded_shares = float(row["shares"])

            return {
                "token_id": token_id,
                "live_shares": live_shares,
                "recorded_shares": recorded_shares,
                "synced": abs(live_shares - recorded_shares) <= 0.001,
            }

        rows = positions_df.to_dict("records")

        with ThreadPoolExecutor(max_workers=30) as executor:
            results = list(executor.map(check_position, rows))

        for result in results:
            if not result["synced"]:
                print(
                    f"POSITION MISMATCH: {result['token_id']} "
                    f"recorded={result['recorded_shares']}, "
                    f"live={result['live_shares']}"
                )
            else:
                print(f"POSITION SYNCED: {result['token_id']}")


    def fee(self, price, fee_rate):
        #fee = C × feeRate × p × (1 - p)
        #Where C = number of shares traded and p = price of the shares.
        return fee_rate * price * (1 - price)


    def manage_open_orders(self, api, orders_df, markets_df, ENTRY_EV_THRESHOLD, EXIT_EV_THRESHOLD):

        api_orders = api.list_orders()

        for order in api_orders["orders"]:

            # Example:
            # cancel if the order is too old
            # cancel if the price is no longer competitive
            # cancel if the EV has disappeared
            # cancel if the market has changed
            # cancel if position/inventory limits have changed

            side = order["side"]
            token_id = order["asset_id"]

            row = markets_df[(markets_df["yes_token"] == token_id) | (markets_df["no_token"] == token_id)].iloc[0]

            # fee_rate = float(api.fee_rate(token_id)["fee_rate"])
            fee_rate = row["feeSchedule"]["rate"]
            condition_id = api.orderbook(token_id)["market"]
            market_detail = api.market_detail(condition_id)

            token_info = next(token for token in market_detail["tokens"] if str(token["token_id"]) == token_id)
            is_yes = token_info["outcome"] == "Yes"

            p_yes = row["model_prob"]
            p_no = 1 - p_yes

            if side == "BUY":
                print("buy")
                if is_yes:
                    buy_yes_cost = order["price"] + self.fee(order["price"], fee_rate)
                
                    profit_if_yes = 1 - buy_yes_cost
                    cost_if_no = buy_yes_cost
        
                    # EV: profit if yes - cost if no
                    buy_yes_ev = p_yes * profit_if_yes - p_no * cost_if_no

                    should_cancel = buy_yes_ev < ENTRY_EV_THRESHOLD

                    print("buy_yes_ev:", buy_yes_ev, "ENTRY_EV_THRESHOLD:", ENTRY_EV_THRESHOLD)

                else:
                    buy_no_cost =  order["price"] + self.fee( order["price"], fee_rate)
                    
                    profit_if_no = 1 - buy_no_cost
                    cost_if_yes = buy_no_cost
        
                    buy_no_ev = p_no * profit_if_no - p_yes * cost_if_yes

                    should_cancel = buy_no_ev < ENTRY_EV_THRESHOLD

                    print("buy_no_ev:", buy_no_ev, "ENTRY_EV_THRESHOLD:", ENTRY_EV_THRESHOLD)


            elif side == "SELL":
                print("sell")
                if is_yes:
                    hold_ev = p_yes
                    exit_ev = order["price"] - self.fee(order["price"], fee_rate)

                else:
                    hold_ev = p_no
                    exit_ev = order["price"] - self.fee(order["price"], fee_rate)

                should_cancel = (exit_ev - hold_ev) < EXIT_EV_THRESHOLD

                print("exit_ev - hold_ev:", exit_ev - hold_ev, "EXIT_EV_THRESHOLD", EXIT_EV_THRESHOLD)


            print("should_cancel:", should_cancel)

            if should_cancel:

                confirm_order = (input("Place this order? Type YES to confirm: ") == "YES")

                if confirm_order == True:
                    try:
                        api.cancel_order(order["order_id"])

                        orders_df.loc[orders_df["order_id"] == order["order_id"], "status"] = "CANCELLED"
                        orders_df.loc[orders_df["order_id"] == order["order_id"], "cancelled_at"] = datetime.now(timezone.utc)

                        orders_df["cancelled_at"] = pd.to_datetime(orders_df["cancelled_at"], utc=True)

                        print("\nCANCEL ORDER SUBMITTED\n\n")

                    except Exception as e:
                        print(f"ORDER CANCELLATION ERROR: {e}")

                else:
                    print("skipping cancel order")

        return orders_df


    def mark_positions_to_market(self, api, positions_df):
        """
        Add current market prices and unrealized PnL to open positions.

        positions_df columns:
            token_id
            shares
            avg_entry_price

        markets_df columns:
            token_id
            price

        Returns:
            positions_df with:
                current_price
                market_value
                cost_basis
                unrealized_pnl
                unrealized_return
        """

        positions_df = positions_df.copy()

        if positions_df.empty:
            print("positions_df is empty, returning mtm")
            return positions_df

        def fee(price, fee_rate):
            #fee = C × feeRate × p × (1 - p)
            #Where C = number of shares traded and p = price of the shares.
            return fee_rate * price * (1 - price)

        # def get_position_price(token_id):

        #     bids = api.orderbook(token_id).get("bids", [])

        #     return (max(float(x["price"]) for x in bids) if bids else None)

        def get_position_data(token_id):
            bids = api.orderbook(token_id).get("bids", [])
            current_price = max(float(x["price"]) for x in bids) if bids else None

            fee_rate = float(api.fee_rate(token_id)["fee_rate"])

            return current_price, fee_rate

        # # Get current price for every position
        # with ThreadPoolExecutor(max_workers=30) as executor:
        #     positions_df["current_price"] = list(executor.map(get_position_price, positions_df["token_id"]))

        with ThreadPoolExecutor(max_workers=30) as executor:
            results = list( executor.map(get_position_data, positions_df["token_id"]))

        # Unpack results
        positions_df["current_price"] = [x[0] for x in results]
        positions_df["fee_rate"] = [x[1] for x in results]

        # Current market value
        positions_df["market_value"] = (positions_df["shares"] * positions_df["current_price"])
        positions_df["market_value_after_fees"] = (positions_df["shares"] * 
            (positions_df["current_price"] - fee(positions_df["current_price"], positions_df["fee_rate"])))

        # Original cost
        positions_df["cost_basis"] = (positions_df["shares"] * positions_df["avg_entry_price"])

        # Unrealized PnL
        positions_df["unrealized_pnl"] = (positions_df["market_value"] - positions_df["cost_basis"])

        # Unrealized PnL
        positions_df["unrealized_pnl_after_fees"] = (positions_df["market_value_after_fees"] - positions_df["cost_basis"])

        # Return
        positions_df["unrealized_return"] = (positions_df["unrealized_pnl"] / positions_df["cost_basis"])

        return positions_df

    
    def calculate_equity(self, api, positions_df, equity_df):
        """
        Calculate the current account equity and P&L.

        Uses the last row of equity_df to determine
        previous_equity and previous_timestamp.
        """

        # ---------------------------------------------------------
        # 0. Get previous equity snapshot
        # ---------------------------------------------------------
        if equity_df.empty:
            previous_equity = None
        else:
            previous_row = equity_df.iloc[-1]
            previous_equity = float(previous_row["equity"])

        # ---------------------------------------------------------
        # 1. Get current cash
        # ---------------------------------------------------------
        cash = float(api.balance()["balance"])

        # ---------------------------------------------------------
        # 2. Market value of open positions
        # ---------------------------------------------------------
        if positions_df.empty:
            market_value = 0.0
            unrealized_pnl = 0.0

        else:
            if "market_value" in positions_df.columns:
                market_value = positions_df["market_value"].sum()
            else:
                market_value = (positions_df["shares"] * positions_df["current_price"]).sum()

            if "unrealized_pnl" in positions_df.columns:
                unrealized_pnl = positions_df["unrealized_pnl"].sum()

            else:
                unrealized_pnl = (positions_df["shares"] * (
                    positions_df["current_price"] - positions_df["avg_entry_price"])).sum()

        # ---------------------------------------------------------
        # 3. Realized P&L
        # ---------------------------------------------------------
        if positions_df.empty:
            realized_pnl = 0.0
        else:
            realized_pnl = positions_df["realized_pnl"].sum()

        # ---------------------------------------------------------
        # 4. Total equity
        # ---------------------------------------------------------
        equity = cash + market_value

        # ---------------------------------------------------------
        # 5. Return
        # ---------------------------------------------------------
        if previous_equity is None or previous_equity == 0:
            period_return = None
        else:
            period_return = equity / previous_equity - 1

        # ---------------------------------------------------------
        # 6. Return new row
        # ---------------------------------------------------------
        equity_row = {
            "timestamp": datetime.now(timezone.utc),
            "cash": cash,
            "market_value": market_value,
            "equity": equity,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "period_return": period_return,
        }

        equity_df = pd.concat([equity_df, pd.DataFrame([equity_row])], ignore_index=True)
        equity_df["timestamp"] = pd.to_datetime(equity_df["timestamp"], utc=True)
        
        # ---------------------------------------------------------
        # 7. Calculate Sharpe / Sortino / Max Drawdown
        # ---------------------------------------------------------
        returns = equity_df["period_return"].dropna()

        if len(returns) >= 2:

            # Sharpe
            volatility = returns.std(ddof=1)

            if volatility > 0:
                sharpe = returns.mean() / volatility
            else:
                sharpe = np.nan

            # Sortino
            # downside_returns = returns[returns < 0]
            downside_returns = np.minimum(returns, 0) # new sortino
            downside_deviation = np.sqrt(np.mean(downside_returns ** 2))
            sortino = returns.mean() / downside_deviation

            if len(downside_returns) > 0:
                downside_deviation = np.sqrt((downside_returns ** 2).mean())

                sortino = returns.mean() / downside_deviation

            else:
                sortino = np.nan

        else:
            sharpe = np.nan
            sortino = np.nan

        
        equity_copy = equity_df["equity"].copy().dropna()
        running_peak = equity_copy.cummax()

        drawdown = equity_copy / running_peak - 1
        max_drawdown = drawdown.min()

        # ---------------------------------------------------------
        # 8. Store metrics
        # ---------------------------------------------------------
        equity_df.loc[equity_df.index[-1], "sharpe"] = sharpe
        equity_df.loc[equity_df.index[-1], "sortino"] = sortino
        equity_df.loc[equity_df.index[-1], "max_drawdown"] = max_drawdown

        # ---------------------------------------------------------
        # 9. Print
        # ---------------------------------------------------------
        print(f"Equity:  {equity:,.2f}")
        print(f"Return:  {period_return:.4%}" if pd.notna(period_return) else "Return: N/A")
        print(f"Sharpe:  {sharpe:.4f}" if pd.notna(sharpe) else "Sharpe: N/A")
        print(f"Sortino: {sortino:.4f}" if pd.notna(sortino) else "Sortino: N/A")
        print(f"Max Drawdown: {max_drawdown:.2%}" if pd.notna(max_drawdown) else "Max Drawdown: N/A")

        return equity_df


    def format_signal_exit(self, best_action, market, pos, current_bid,
                client_oid, hold_ev, exit_ev, fee_rate, EXIT_EV_THRESHOLD):

        p_yes = market["model_prob"]
        p_no = 1 - p_yes

        rows = [
            ("Market", market["question"]),
            ("Outcome", pos["outcome"]),
            ("Direction", market["direction"]),
            ("Event Type", market["event_type"]),
            ("Best Action", best_action),
            ("Current Bid", current_bid),
            ("Current Shares", pos["shares"]),
            ("P Yes", p_yes),
            ("P No", p_no),
            ("Exit EV", exit_ev),
            ("Hold EV", hold_ev),
            ("Fee Rate", fee_rate),
            ("Unrealized Pnl", pos["unrealized_pnl"]),
            ("Unrealized Return", pos["unrealized_return"]),
            ("Exit EV threshold", EXIT_EV_THRESHOLD),
        ]

        print("=" * 70)
        print(f"{best_action + ' SIGNAL':^70}")
        print("=" * 70)

        for label, value in rows:
            print(f"{label:<25} : {value}")

        print("=" * 70)
        print(f"{'VARIABLES IN REQUEST':^70}")
        
        rows = [
            ("tokenId", pos["token_id"]),
            ("orderPrice", current_bid),
            ("orderSize", pos["shares"]),
            ("clientOrderId", client_oid)
        ]

        for label, value in rows:
            print(f"{label:<25} : {value}")

        print("=" * 70)


    # Inventory Management Step
    def run_risk_management(self, api, positions_df, markets_df, orders_df, EXIT_EV_THRESHOLD):

        for _, pos in positions_df.iterrows():

            condition_id = pos["condition_id"]
            market = markets_df.loc[markets_df["conditionId"] == condition_id].iloc[0]

            print("pos:", pos)
            print("market:", market)

            fee_rate = market["feeSchedule"]["rate"]

            p_yes = market["model_prob"]
            p_no = 1 - p_yes

            if pos["outcome"] == "Yes": # no shorting in polymarket
                current_bid = market["yes_bid"]
                hold_ev = p_yes
                exit_ev = current_bid - self.fee(current_bid, fee_rate)

            elif pos["outcome"] == "No":
                current_bid = market["no_bid"]
                hold_ev = p_no
                exit_ev = current_bid - self.fee(current_bid, fee_rate)

            if (exit_ev - hold_ev) > EXIT_EV_THRESHOLD:
                best_action = "EXIT"

            else:
                best_action = "HOLD"

            client_oid = str(uuid.uuid4())

            self.format_signal_exit(best_action, market, pos, current_bid,
                        client_oid, hold_ev, exit_ev, fee_rate, EXIT_EV_THRESHOLD)

            if best_action == "EXIT":
                confirm_order = (input("Place this order? Type YES to confirm: ") == "YES")

                if confirm_order == True:

                    price_tick = float(api.tick_size(pos["token_id"])["tick_size"])
                    price = api.round_to_tick(current_bid, price_tick)
                    normalized_size = api.normalize_size(pos["shares"])
                    
                    try:
                        order = api.place_limit_order(
                            token_id=pos["token_id"],
                            side="sell",
                            price=price,
                            size=normalized_size,
                            order_type="GTC",
                        )
                
                        print("\nLIMIT ORDER SUBMITTED\n\n")
                        print(order)
                
                        order_row = {
                            "question": pos["question"],
                            "order_id": order["clob_order_id"],
                            "condition_id": condition_id,
                            "token_id": pos["token_id"],
                            "outcome": pos["outcome"],
                            "side": "SELL",
                            "price": float(price),
                            "requested_size": normalized_size,
                            "order_type": "GTC",
                            "status": "OPEN",
                            "created_at": datetime.now(timezone.utc),
                            "cancelled_at": None,
                        }

                        orders_df = pd.concat([orders_df, pd.DataFrame([order_row])], ignore_index=True)
                        orders_df["created_at"] = pd.to_datetime(orders_df["created_at"], utc=True)
                        orders_df["cancelled_at"] = pd.to_datetime(orders_df["cancelled_at"], utc=True)
                
                        print("\nLIMIT ORDER RECORDED\n\n")
            
                    except Exception as e:
                        print("\nLIMIT ORDER ERROR\n\n")
                        print(e)
                        break

                else:
                    print("\nSKIPPING LIMIT ORDER\n\n")

        return orders_df


    def format_signal_entry(self, trade, outcome, best_action, kelly, 
                            normalized_size, current_ask, token_id, 
                            client_oid, ev, cash, current_size, 
                            ENTRY_EV_THRESHOLD, FRACTION, MAX_POSITION):

        print("=" * 70)
        print("BUY SIGNAL")
        print("=" * 70)

        p_yes = trade["model_prob"]
        p_no = 1 - p_yes

        rows = [
            ("Market", trade["question"]),
            ("Outcome", outcome),
            ("Direction", trade["direction"]),
            ("Event Type", trade["event_type"]),
            ("Best Action", best_action),
            ("Kelly Size x Fraction", FRACTION * kelly),
            ("Recommended Size", normalized_size),
            ("Current Ask", current_ask),
            ("P Yes", p_yes),
            ("P No", p_no),
            ("Buy Yes EV", trade["buy_yes_ev"]),
            ("Sell No EV", trade["sell_no_ev"]),
            ("Buy No EV", trade["buy_no_ev"]),
            ("Sell Yes EV", trade["sell_yes_ev"]),
            ("Unrealized Pnl", normalized_size * ev),
            ("Cash", cash),
            ("Current Shares", current_size),
            ("Fee Rate", trade["feeSchedule"]["rate"]),
            ("ENTRY EV THRESHOLD", ENTRY_EV_THRESHOLD),
            ("MAX POSITION THRESHOLD", MAX_POSITION),
        ]

        for label, value in rows:
            print(f"{label:<25} : {value}")

        print("=" * 70)
        print(f"{'VARIABLES IN REQUEST':^70}")

        rows = [
            ("tokenId", token_id),
            ("orderPrice", current_ask),
            ("orderSize", normalized_size),
            ("clientOrderId", client_oid)
        ]

        for label, value in rows:
            print(f"{label:<25} : {value}")

        print("=" * 70)


    # New Opportunities Step
    def run_new_opportunities(self, api, opportunities_df, orders_df, 
                              ENTRY_EV_THRESHOLD=0.02, MAX_POSITION=0.05, FRACTION=0.1):
            
        for _, trade in opportunities_df.iterrows():

            cash = float(api.balance()["balance"])
    
            if trade["best_ev"] < ENTRY_EV_THRESHOLD:
                print(f"Current trade is less than required ev ({ENTRY_EV_THRESHOLD}), skipping")
                continue
    
            # usually cannot short, this only happens when im closing positions
            if trade["best_action"] == "buy_yes_ev" or trade["best_action"] == "sell_no_ev":
                best_action = "buy_yes_ev"
                ev = trade["buy_yes_ev"]
                token_id = trade["yes_token"]
                outcome = "Yes"
                kelly = trade["buy_yes_kelly"]
                current_ask = trade["yes_ask"]
    
            elif trade["best_action"] == "buy_no_ev" or trade["best_action"] == "sell_yes_ev":
                best_action = "buy_no_ev"
                ev = trade["buy_no_ev"]
                token_id = trade["no_token"]
                outcome = "No"
                kelly = trade["buy_no_kelly"]
                current_ask = trade["no_ask"]
    
            current_size = float(api.balance(asset_type="conditional", token_id=token_id)["balance"])
            print("current balance size:", current_size)
    
            max_position_value = cash * MAX_POSITION
            current_position_value = current_size * current_ask
            remaining_capacity = max(0.0, max_position_value - current_position_value)
    
            if remaining_capacity == 0:
                print(f"No more dollars to allocate for this trade position, skipping, remaining_capacity: {remaining_capacity}")
                continue
    
            kelly_dollars = cash * FRACTION * kelly
    
            dollars = min(kelly_dollars, remaining_capacity)
    
            if dollars < 1.0:
                print(f"Order too small after position cap, skipping, dollars: {dollars}")
                continue
    
            print(f"dollars: {dollars}")
    
            size = dollars / current_ask
            normalized_size = api.normalize_size(size)
            
            client_oid = str(uuid.uuid4())
    
            self.format_signal_entry(trade, outcome, best_action, kelly, 
                                            normalized_size, current_ask, token_id, 
                                            client_oid, ev, cash, current_size, 
                                            ENTRY_EV_THRESHOLD, FRACTION, MAX_POSITION)
    
            confirm_order = (input("Place this order? Type YES to confirm: ") == "YES")
            
            if confirm_order == True:
    
                price_tick = float(api.tick_size(token_id)["tick_size"])
                price = api.round_to_tick(current_ask, price_tick)
    
                try:
                    order = api.place_limit_order(
                        token_id=token_id,
                        side="buy",
                        price=price,
                        size=normalized_size,
                        order_type="GTC",
                        client_order_id=client_oid
                    )
            
                    print("\nLIMIT ORDER SUBMITTED\n\n")
                    print(order)
    
                    order_row = {
                        "question": trade["question"],
                        "order_id": order["clob_order_id"],
                        "condition_id": trade["conditionId"],
                        "token_id": token_id,
                        "outcome": outcome,
                        "side": "BUY",
                        "price": float(price),
                        "requested_size": normalized_size,
                        "order_type": "GTC",
                        "status": "OPEN",
                        "created_at": datetime.now(timezone.utc),
                        "cancelled_at": None,
                    }
            
                    orders_df = pd.concat([orders_df, pd.DataFrame([order_row])], ignore_index=True)
                    orders_df["created_at"] = pd.to_datetime(orders_df["created_at"], utc=True)
                    orders_df["cancelled_at"] = pd.to_datetime(orders_df["cancelled_at"], utc=True)
            
                    print("\nLIMIT ORDER RECORDED\n\n")
    
                except Exception as e:
                    print("\nLIMIT ORDER ERROR\n\n")
                    print(e)
                    break
    
            else:
                print("\nLIMIT SKIPPING ORDER\n\n")
    
        return orders_df


    def format_arbitrage_entry(self, api, trade, cash):

        leg_1_question = trade["lower_question"] if "lower_question" in trade else trade["A_question"]
        leg_1_token_id = trade["lower_token_id"] if "lower_token_id" in trade else trade["A_token_id"]
        leg_1_ask = trade["lower_price"] if "lower_price" in trade else trade["A_price"]
        leg_1_outcome = trade["lower_outcome"] if "lower_outcome" in trade else trade["A_outcome"]
        leg_1_condition_id = trade["lower_condition_id"] if "lower_condition_id" in trade else trade["A_condition_id"]

        leg_2_question = trade["higher_question"] if "higher_question" in trade else trade["B_question"]
        leg_2_token_id = trade["higher_token_id"] if "higher_token_id" in trade else trade["B_token_id"]
        leg_2_ask = trade["higher_price"] if "higher_price" in trade else trade["B_price"]
        leg_2_outcome = trade["higher_outcome"] if "higher_outcome" in trade else trade["B_outcome"]
        leg_2_condition_id = trade["higher_condition_id"] if "higher_condition_id" in trade else trade["B_condition_id"]

        leg_1_client_oid = str(uuid.uuid4())
        leg_2_client_oid = str(uuid.uuid4())

        enter_all = (cash - trade["total_cost"] > 0)
        executable_normalized_size = api.normalize_size(trade["max_size"]) if enter_all else api.normalize_size(cash / trade["cost_per_unit"])
        executable_total_cost = executable_normalized_size * trade["cost_per_unit"]
        executable_guaranteed_profit = executable_normalized_size * trade["guaranteed_profit_per_unit"]
        print("=" * 70)
        print("ENTRY ARBITRAGE SIGNAL")
        print("=" * 70)

        rows = [
            ("Event Type", trade["event_type"]),
            ("Direction", trade["direction"]),
            ("Expiry / Resolution Date", trade["expiry"]),
            (""),
            ("Leg 1 Market", trade["lower_question"] if "lower_question" in trade else trade["A_question"]),
            ("Leg 1 Strike", trade["lower_strike"] if "lower_strike" in trade else trade["A_strike"]),
            ("Leg 1 Outcome", leg_1_outcome),
            ("Leg 1 Current Ask", leg_1_ask),
            (""),
            ("Leg 2 Market", trade["higher_question"] if "higher_question" in trade else trade["B_question"]),
            ("Leg 2 Strike", trade["higher_strike"] if "higher_strike" in trade else trade["B_strike"]),
            ("Leg 2 Outcome", leg_2_outcome),
            ("Leg 2 Current Ask", leg_2_ask),
            (""),
            ("Enter All Positions",enter_all),
            ("Max Size", trade["max_size"]),
            ("Executable Normalized Size", executable_normalized_size),
            ("Executable Total Cost", executable_total_cost),
            ("Executable Total Guaranteed Profit", executable_guaranteed_profit),
            ("Total Guaranteed Profit", trade["total_guaranteed_profit"]),
            ("Cash", cash),
        ]

        for label, value in rows:
            print(f"{label:<25} : {value}")

        print("=" * 70)
        print(f"{'VARIABLES IN REQUEST':^70}")

        rows = [
            ("Leg 1 tokenId", leg_1_token_id),
            ("Leg 1 orderPrice", leg_1_ask),
            ("Leg 1 orderSize", executable_normalized_size),
            ("Leg 1 clientOrderId", leg_1_client_oid),
            ("Leg 1 Action", "BUY"),
            (""),
            ("Leg 2 tokenId", leg_2_token_id),
            ("Leg 2 orderPrice", leg_2_ask),
            ("Leg 2 orderSize", executable_normalized_size),
            ("Leg 2 clientOrderId", leg_2_client_oid),
            ("Leg 2 Action", "BUY"),
        ]

        for label, value in rows:
            print(f"{label:<25} : {value}")

        print("=" * 70)

        return {
            "leg_1_question" : leg_1_question,
            "leg_2_question" : leg_2_question,
            "leg_1_token_id" : leg_1_token_id,
            "leg_2_token_id" : leg_2_token_id,
            "leg_1_ask" : leg_1_ask,
            "leg_2_ask" : leg_2_ask,
            "leg_1_outcome" : leg_1_outcome,
            "leg_2_outcome" : leg_2_outcome,
            "leg_1_condition_id" : leg_1_condition_id,
            "leg_2_condition_id" : leg_2_condition_id
        }


    def run_arbitrage_opportunities(self, api, arbitrage_df, orders_df):
    
        for _, trade in arbitrage_df.iterrows():

            cash = float(api.balance()["balance"])

            remaining_capacity = cash
    
            if remaining_capacity == 0:
                print(f"No more dollars to allocate for this trade position, skipping, remaining_capacity: {remaining_capacity}")
                continue
    
            dollars = remaining_capacity
    
            if dollars < 1.0:
                print(f"Order too small after position cap, skipping, dollars: {dollars}")
                continue
    
            print(f"dollars: {dollars}")
    
            params = self.format_arbitrage_entry(api, trade, cash)
    
            confirm_order = (input("Place this order? Type YES to confirm: ") == "YES")
            
            if confirm_order == True:

                try:
                    print("")
                    order_1 = api.place_limit_order_test(
                        token_id=params["leg_1_token_id"],
                        side="buy",
                        price=params["leg_1_ask"],
                        size=params["normalized_size"],
                        order_type="GTC",
                        client_order_id=params["leg_1_client_oid"]
                    )
            
                    print("\nLEG 1 LIMIT ORDER SUBMITTED\n\n")
                    print(order_1)

                    order_2 = api.place_limit_order_test(
                        token_id=params["leg_2_token_id"],
                        side="buy",
                        price=params["leg_2_ask"],
                        size=params["normalized_size"],
                        order_type="GTC",
                        client_order_id=params["leg_2_client_oid"]
                    )
            
                    print("\nLEG 2 LIMIT ORDER SUBMITTED\n\n")
                    print(order_2)
    
                    order_row = {
                        "question": params["leg_1_question"],
                        "order_id": order_1["clob_order_id"],
                        "condition_id": params["leg_1_condition_id"],
                        "token_id": params["leg_1_token_id"],
                        "outcome": params["leg_1_outcome"],
                        "side": "BUY",
                        "price": float(params["leg_1_ask"]),
                        "requested_size": params["normalized_size"],
                        "order_type": "GTC",
                        "status": "OPEN",
                        "created_at": datetime.now(timezone.utc),
                        "cancelled_at": None,
                    }
            
                    orders_df = pd.concat([orders_df, pd.DataFrame([order_row])], ignore_index=True)
                    print("\nLEG 1 LIMIT ORDER RECORDED\n\n")

                    order_row = {
                        "question": params["leg_2_question"],
                        "order_id": order_2["clob_order_id"],
                        "condition_id": params["leg_2_condition_id"],
                        "token_id": params["leg_2_token_id"],
                        "outcome": params["leg_2_outcome"],
                        "side": "BUY",
                        "price": float(params["leg_2_ask"]),
                        "requested_size": params["normalized_size"],
                        "order_type": "GTC",
                        "status": "OPEN",
                        "created_at": datetime.now(timezone.utc),
                        "cancelled_at": None,
                    }
            
                    orders_df = pd.concat([orders_df, pd.DataFrame([order_row])], ignore_index=True)
                    orders_df["created_at"] = pd.to_datetime(orders_df["created_at"], utc=True)
                    orders_df["cancelled_at"] = pd.to_datetime(orders_df["cancelled_at"], utc=True)
            
                    print("\nLEG 2 LIMIT ORDER RECORDED\n\n")
    
                except Exception as e:
                    print("\nLIMIT ORDER ERROR\n\n")
                    print(e)
                    break
    
            else:
                print("\nLIMIT SKIPPING ORDER\n\n")
    
        return orders_df


    def format_arbitrage_exit(self, api, leg_1, leg_2):

        def fee(price, fee_rate):
            #fee = C × feeRate × p × (1 - p)
            #Where C = number of shares traded and p = price of the shares.
            return fee_rate * price * (1 - price)

        fee_rate = float(api.fee_rate(leg_1["token_id"])["fee_rate"])
        
        leg_1_current_size = leg_1["shares"]
        leg_2_current_size = leg_2["shares"]
        max_current_size = min(leg_1_current_size, leg_2_current_size)
        
        leg_1_book = api.orderbook(leg_1["token_id"])
        leg_2_book = api.orderbook(leg_2["token_id"])

        leg_1_bids = leg_1_book.get("bids", [])
        leg_2_bids = leg_2_book.get("bids", [])

        leg_1_best_bid = max(leg_1_bids, key=lambda x: float(x["price"])) if leg_1_bids else None
        leg_2_best_bid = max(leg_2_bids, key=lambda x: float(x["price"])) if leg_2_bids else None

        leg_1_bid = float(leg_1_best_bid["price"]) if leg_1_best_bid else None
        leg_1_bid_size = float(leg_1_best_bid["size"]) if leg_1_best_bid else None

        leg_2_bid = float(leg_2_best_bid["price"]) if leg_2_best_bid else None
        leg_2_bid_size = float(leg_2_best_bid["size"]) if leg_2_best_bid else None

        max_size = min(leg_1_bid_size, leg_2_bid_size)
        remaining_size = max_current_size if (max_size - max_current_size > 0) else max_current_size - max_size
        close_all = (max_size - max_current_size > 0)

        avg_realized_pnl = (leg_1_bid - fee(leg_1_bid, fee_rate) - leg_1["avg_entry_price"]) + (leg_2_bid - fee(leg_2_bid, fee_rate) - leg_2["avg_entry_price"])
        executable_total_realized_pnl = avg_realized_pnl * remaining_size
        expected_total_realized_pnl = avg_realized_pnl * max_current_size
        
        normalized_size = api.normalize_size(remaining_size)
        
        leg_1_client_oid = str(uuid.uuid4())
        leg_2_client_oid = str(uuid.uuid4())
    
        print("=" * 70)
        print("EXIT ARBITRAGE SIGNAL")
        print("=" * 70)

        rows = [
            ("Leg 1 Market", leg_1["question"]),
            ("Leg 1 Outcome", leg_1["outcome"]),
            ("Leg 1 Size", leg_1["shares"]),
            ("Leg 1 Avg Entry Price", leg_1["avg_entry_price"]),
            ("", ""),
            ("Leg 2 Market", leg_2["question"]),
            ("Leg 2 Outcome", leg_2["outcome"]),
            ("Leg 2 Size", leg_2["shares"]),
            ("Leg 2 Avg Entry Price", leg_2["avg_entry_price"]),
            ("", ""),
            ("Close All Positions", close_all),
            ("Max Size", max_size),
            ("Normalized Max Size", normalized_size),
            ("Remaining Size", remaining_size),
            ("Avg Realized PnL", avg_realized_pnl),
            ("Executable Total Realized PnL", executable_total_realized_pnl),
            ("Expected Total Realized PnL", expected_total_realized_pnl)
        ]

        for label, value in rows:
            print(f"{label:<25} : {value}")

        print("=" * 70)
        print(f"{'VARIABLES IN REQUEST':^70}")

        rows = [
            ("Leg 1 tokenId", leg_1["token_id"]),
            ("Leg 1 orderPrice", leg_1_bid),
            ("Leg 1 orderSize", normalized_size),
            ("Leg 1 clientOrderId", leg_1_client_oid),
            ("Leg 1 Action", "SELL"),
            ("", ""),
            ("Leg 2 tokenId", leg_2["token_id"]),
            ("Leg 2 orderPrice", leg_2_bid),
            ("Leg 2 orderSize", normalized_size),
            ("Leg 2 clientOrderId", leg_2_client_oid),
            ("Leg 2 Action", "SELL"),
        ]

        for label, value in rows:
            print(f"{label:<25} : {value}")

        print("=" * 70)

        return {
            "normalized_size" : normalized_size,
            "leg_1_token_id": leg_1["token_id"],
            "leg_2_token_id": leg_2["token_id"],
            "leg_1_bid" : leg_1_bid,
            "leg_2_bid" : leg_2_bid,
            "leg_1_client_oid" : leg_1_client_oid,
            "leg_2_client_oid" : leg_2_client_oid
        }


    def close_arbitrage_positions(self, api, positions_df, orders_df, 
                                  question_1, outcome_1, question_2, outcome_2):

        leg_1 = positions_df[
            (positions_df["question"] == question_1) &
            (positions_df["outcome"] == outcome_1)
            ].iloc[0]

        leg_2 = positions_df[
            (positions_df["question"] == question_2) &
            (positions_df["outcome"] == outcome_2)
            ].iloc[0]

        params = self.format_arbitrage_exit(api, leg_1, leg_2)

        confirm_order = (input("Place this order? Type YES to confirm: ") == "YES")
        
        if confirm_order == True:

            try:
                print("")
                order_1 = api.place_limit_order_test(
                    token_id=params["leg_1_token_id"],
                    side="sell",
                    price=params["leg_1_bid"],
                    size=params["normalized_size"],
                    order_type="GTC",
                    client_order_id=params["leg_1_client_oid"]
                )
        
                print("\nLEG 1 LIMIT ORDER SUBMITTED\n\n")
                print(order_1)

                order_2 = api.place_limit_order_test(
                    token_id=params["leg_2_token_id"],
                    side="sell",
                    price=params["leg_2_bid"],
                    size=params["normalized_size"],
                    order_type="GTC",
                    client_order_id=params["leg_2_client_oid"]
                )
        
                print("\nLEG 2 LIMIT ORDER SUBMITTED\n\n")
                print(order_2)

                order_row = {
                    "question": question_1,
                    "order_id": order_1["clob_order_id"],
                    "condition_id": leg_1["condition_id"],
                    "token_id": leg_1["token_id"],
                    "outcome": leg_1["outcome"],
                    "side": "BUY",
                    "price": float(params["leg_1_bid"]),
                    "requested_size": params["normalized_size"],
                    "order_type": "GTC",
                    "status": "OPEN",
                    "created_at": datetime.now(timezone.utc),
                    "cancelled_at": None,
                }
        
                orders_df = pd.concat([orders_df, pd.DataFrame([order_row])], ignore_index=True)

                order_row = {
                    "question": question_2,
                    "order_id": order_2["clob_order_id"],
                    "condition_id": leg_1["condition_id"],
                    "token_id": leg_2["token_id"],
                    "outcome": leg_2["outcome"],
                    "side": "BUY",
                    "price": float(params["leg_2_bid"]),
                    "requested_size": params["normalized_size"],
                    "order_type": "GTC",
                    "status": "OPEN",
                    "created_at": datetime.now(timezone.utc),
                    "cancelled_at": None,
                }
        
                orders_df = pd.concat([orders_df, pd.DataFrame([order_row])], ignore_index=True)
                orders_df["created_at"] = pd.to_datetime(orders_df["created_at"], utc=True)
                orders_df["cancelled_at"] = pd.to_datetime(orders_df["cancelled_at"], utc=True)
        
                print("\nLIMIT ORDER RECORDED\n\n")

            except Exception as e:
                print("\nLIMIT ORDER ERROR\n\n")
                print(e)
    
        return orders_df


    def save_snapshots(self, DATA_DIR, df, df_name):

        date = datetime.now().strftime("%Y%m%d")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        os.makedirs(f"{DATA_DIR}/{date}", exist_ok=True)
        filename = f"{DATA_DIR}/{date}/{df_name}_{timestamp}.parquet"

        COLS = [
            "id",
            "question",
            "slug",
            "conditionId",

            "currency",
            "strike",
            "expiry",
            "direction",
            "event_type",
            "expiry_dt",
            "T",

            "yes_token",
            "no_token",

            "volume",
            "liquidity",
            "volume24hr",
            "volume1wk",
            "volume1mo",

            "lastTradePrice",
            "bestBid",
            "bestAsk",
            "spread",

            "yes_bid",
            "yes_ask",
            "no_bid",
            "no_ask",

            "iv",
            "model_prob",

            "buy_yes_fee",
            "sell_yes_fee",
            "buy_no_fee",
            "sell_no_fee",

            "buy_yes_ev",
            "sell_yes_ev",
            "buy_no_ev",
            "sell_no_ev",

            "buy_yes_kelly",
            "sell_yes_kelly",
            "buy_no_kelly",
            "sell_no_kelly",

            "best_ev",
            "best_action",
        ]

        df = df[COLS].copy()

        df.to_parquet(filename, engine="fastparquet", index=False)

        print("save_snapshots df saved at:", filename)


    def save(self, DATA_DIR, df, df_name):

        os.makedirs(DATA_DIR, exist_ok=True)
        filename = f"{DATA_DIR}/{df_name}.parquet"

        df.to_parquet(filename, engine="fastparquet", index=False)

        print('save df saved at: ', filename)