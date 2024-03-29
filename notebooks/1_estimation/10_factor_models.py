# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     custom_cell_magics: kql
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.11.2
#   kernelspec:
#     display_name: .venv
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Factor models estimation & residuals
# This notebook contains:
# - monthly factor model estimation for:
#     - returns
#     - log variance
#
# ## Imports

# %%
# %load_ext autoreload
# %autoreload 2

# %%
import datetime as dt
import numpy as np

import pandas as pd
from dateutil.relativedelta import relativedelta

from euraculus.data.map import DataMap
from euraculus.models.factor import (
    CAPM,
    Carhart4FactorModel,
    FactorModel,
    FamaFrench3FactorModel,
    FamaFrench5FactorModel,
    Q5FactorModel,
    SPY1FactorModel,
    SPYVariance1FactorModel,
)
from euraculus.models.estimate import prepare_log_data
from euraculus.models.factor import estimate_models, predict_factor_returns
from euraculus.utils.utils import months_difference
from euraculus.settings import (
    DATA_DIR,
    LAST_SAMPLING_DATE,
    TIME_STEP,
    FORECAST_WINDOWS,
    FIRST_ESTIMATION_DATE,
    SPLIT_DATE,
)

# %% [markdown]
# ## Set up
# ### Data

# %%
data = DataMap(DATA_DIR)
df_rf = data.load_rf()

# %% [markdown]
# ### Models

# %%
ret_models = {
    # "spy_capm": SPY1FactorModel(data),
    "capm": CAPM(data),
    "ff3": FamaFrench3FactorModel(data),
    "c4": Carhart4FactorModel(data),
    "ff5": FamaFrench5FactorModel(data),
    "q5": Q5FactorModel(data),
    "ew": FactorModel(data.read(DATA_DIR / "analysis/df_daily_indices.pkl")["ret_ew"])
}

# %%
var_models = {
    # "logvar_capm": SPYVariance1FactorModel(data),
}

# %% [markdown]
# ## Standard Factor Models

# %% [markdown]
# ### Backward part

# %%
# %%time
sampling_date = FIRST_ESTIMATION_DATE
while sampling_date <= LAST_SAMPLING_DATE:
    # get excess return samples
    df_historic = data.load_historic(sampling_date=sampling_date, column="retadj")
    df_historic -= df_rf.loc[df_historic.index].values

    # estimate models backwards
    df_estimates, df_residuals = estimate_models(ret_models, df_historic)

    # predict future values from future factors
    if sampling_date < LAST_SAMPLING_DATE:
        df_future = data.load_future(sampling_date=sampling_date, column="retadj")
        df_future -= df_rf.loc[df_future.index].values
        df_errors = predict_factor_returns(ret_models, df_future)

    # store
    data.store(
        data=df_residuals, path=f"samples/{sampling_date:%Y-%m-%d}/historic_daily.csv"
    )
    data.store(
        data=df_estimates, path=f"samples/{sampling_date:%Y-%m-%d}/asset_estimates.csv"
    )
    if sampling_date < LAST_SAMPLING_DATE:
        data.store(
            data=df_errors,
            path=f"samples/{sampling_date:%Y-%m-%d}/future_daily.csv",
        )

    # increment monthly end of month
    print(
        f"Completed historic return factor model estimation at {sampling_date:%Y-%m-%d}"
    )
    sampling_date += TIME_STEP

# %% [markdown]
# ### Forward part as expanding window

# %%
# %%time
sampling_date = FIRST_ESTIMATION_DATE
while sampling_date < LAST_SAMPLING_DATE:
    # get excess return samples
    df_future = data.load_future(sampling_date=sampling_date, column="retadj")
    df_future -= df_rf.loc[df_future.index].values

    # slice expanding window
    df_expanding_estimates = pd.DataFrame(index=df_future.columns)
    df_expanding_residuals = pd.DataFrame(index=df_future.stack().index)
    for window_length in FORECAST_WINDOWS:
        if (
            months_difference(end_date=LAST_SAMPLING_DATE, start_date=sampling_date)
            >= window_length
        ):
            end_date = sampling_date + relativedelta(months=window_length, day=31)
            df_window = df_future[df_future.index <= end_date]

            # estimate models in window
            df_estimates, df_residuals = estimate_models(ret_models, df_window)

            # collect
            df_estimates = df_estimates.add_suffix(f"_next{window_length}M")
            df_expanding_estimates = df_expanding_estimates.join(df_estimates)
            if window_length in [1, 12]:
                df_residuals = df_residuals.add_suffix(f"_next{window_length}M")
                df_expanding_residuals = df_expanding_residuals.join(
                    df_residuals, how="outer"
                )

    # store
    data.store(
        data=df_expanding_estimates,
        path=f"samples/{sampling_date:%Y-%m-%d}/asset_estimates.csv",
    )
    data.store(
        data=df_expanding_residuals,
        path=f"samples/{sampling_date:%Y-%m-%d}/future_daily.csv",
    )

    # increment monthly end of month
    print(
        f"Completed future return factor model estimation at {sampling_date:%Y-%m-%d}"
    )
    sampling_date += TIME_STEP

# %% [markdown]
# ## Variance Factor Models

# %% [markdown]
# ### Backward part

# %%
# %%time
sampling_date = FIRST_ESTIMATION_DATE
while sampling_date <= LAST_SAMPLING_DATE:
    # get excess return samples
    df_var = data.load_historic(sampling_date=sampling_date, column="var")
    df_noisevar = data.load_historic(sampling_date=sampling_date, column="noisevar")
    df_historic = prepare_log_data(df_data=df_var, df_fill=df_noisevar)

    # estimate models backwards
    df_estimates, df_residuals = estimate_models(var_models, df_historic)

    # store
    data.store(
        data=df_residuals,
        path=f"samples/{sampling_date:%Y-%m-%d}/historic_daily.csv",
    )
    data.store(
        data=df_estimates,
        path=f"samples/{sampling_date:%Y-%m-%d}/asset_estimates.csv",
    )

    # increment monthly end of month
    print(
        f"Completed historic variance factor model estimation at {sampling_date:%Y-%m-%d}"
    )
    sampling_date += TIME_STEP

# %% [markdown]
# ### Forward part as expanding window

# %%
# %%time
sampling_date = FIRST_ESTIMATION_DATE
while sampling_date < LAST_SAMPLING_DATE:
    # get excess return samples
    df_var = data.load_future(sampling_date=sampling_date, column="var")
    df_noisevar = data.load_future(sampling_date=sampling_date, column="noisevar")
    df_future = prepare_log_data(df_data=df_var, df_fill=df_noisevar)

    # slice expanding window
    df_expanding_estimates = pd.DataFrame(index=df_future.columns)
    for window_length in FORECAST_WINDOWS:
        if (
            months_difference(end_date=LAST_SAMPLING_DATE, start_date=sampling_date)
            >= window_length
        ):
            end_date = sampling_date + relativedelta(months=window_length, day=31)
            df_window = df_future[df_future.index <= end_date]

            # estimate models in window
            df_estimates, df_residuals = estimate_models(var_models, df_window)

            # collect
            df_estimates = df_estimates.add_suffix(f"_next{window_length}M")
            df_expanding_estimates = df_expanding_estimates.join(df_estimates)

    # store
    data.store(
        data=df_expanding_estimates,
        path=f"samples/{sampling_date:%Y-%m-%d}/asset_estimates.csv",
    )
    data.store(
        data=df_residuals,
        path=f"samples/{sampling_date:%Y-%m-%d}/future_daily.csv",
    )

    # increment monthly end of month
    print(
        f"Completed future variance factor model estimation at {sampling_date:%Y-%m-%d}"
    )
    sampling_date += TIME_STEP
