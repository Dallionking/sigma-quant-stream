"""Sample SMA crossover strategy for testing the backtest runner."""

import pandas as pd


class Strategy:
    name = "SMA_Crossover_Demo"

    def __init__(self, params=None):
        self.params = params or self.default_params()

    def default_params(self):
        return {
            "fast_period": 10,
            "slow_period": 30,
            "atr_period": 14,
            "atr_multiplier": 2.0,
        }

    def indicators(self, df):
        p = self.params
        df["sma_fast"] = df["close"].rolling(p["fast_period"]).mean()
        df["sma_slow"] = df["close"].rolling(p["slow_period"]).mean()
        # ATR for stop-loss reference
        tr = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - df["close"].shift(1)).abs(),
                (df["low"] - df["close"].shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        df["atr"] = tr.rolling(p["atr_period"]).mean()
        return df

    def signals(self, df):
        df["signal"] = 0
        df.loc[df["sma_fast"] > df["sma_slow"], "signal"] = 1
        df.loc[df["sma_fast"] < df["sma_slow"], "signal"] = -1
        return df
