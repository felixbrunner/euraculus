# %% [markdown]
# # 01 - Data Sampling & Preparation
# This notebook serves to perform the sampling of the largest companies by market capitalization at the end of each month.

# %% [markdown]
# ## Imports

# %%
# %load_ext autoreload
# %autoreload 2

# %%
import pandas as pd
import numpy as np
import datetime as dt
from dateutil.relativedelta import relativedelta
from euraculus.data import DataMap
from euraculus.sampling import LargeCapSampler

# %% [markdown]
# ## Set up

# %% [markdown]
# ### Sampler

# %%
data = DataMap("../data")
sampler = LargeCapSampler(datamap=data, n_assets=100, back_offset=12, forward_offset=12)

# %% [markdown]
# ### Timeframe

# %%
first_sampling_date = dt.datetime(year=1994, month=1, day=31)
last_sampling_date = dt.datetime(year=2021, month=12, day=31)

# %% [markdown]
# ## Conduct monthly sampling

# %%
# perform monthly sampling and store samples locally
sampling_date = first_sampling_date
while sampling_date <= last_sampling_date:
    # get sample
    df_historic, df_future, df_summary = sampler.sample(sampling_date)

    # dump
    data.store(
        df_historic,
        "samples/{:%Y-%m-%d}/historic_daily.csv".format(sampling_date),
    )
    data.store(
        df_future,
        "samples/{:%Y-%m-%d}/future_daily.csv".format(sampling_date),
    )
    data.store(
        df_summary,
        "samples/{:%Y-%m-%d}/selection_summary.csv".format(sampling_date),
    )
    data.store(
        df_summary.loc[df_historic.index.get_level_values("permno").unique()],
        "samples/{:%Y-%m-%d}/asset_estimates.csv".format(sampling_date),
    )

    # increment monthly end of month
    sampling_date += relativedelta(months=1, day=31)
    if sampling_date.month == 12:
        print("Done sampling year {}.".format(sampling_date.year))