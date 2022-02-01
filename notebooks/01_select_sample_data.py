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
# ## Set up Sampler

# %%
data = DataMap("../data")
sampler = LargeCapSampler(datamap=data, n_assets=100, back_offset=12, forward_offset=12)

# %% [markdown]
# ## Conduct monthly sampling

# %%
# define timeframe
first_sampling_date = dt.datetime(year=1994, month=1, day=31)
last_sampling_date = dt.datetime(year=2021, month=12, day=31)

# %%
# perform monthly sampling and store samples locally
sampling_date = first_sampling_date
while sampling_date <= last_sampling_date:
    # get sample
    df_back, df_forward, df_summary = sampler.sample(sampling_date)

    # dump
    data.store(
        df_back,
        "samples/{0}{1:0=2d}/df_back.csv".format(sampling_date.year, sampling_date.month),
    )
    data.store(
        df_forward,
        "samples/{0}{1:0=2d}/df_forward.csv".format(sampling_date.year, sampling_date.month),
    )
    data.store(
        df_summary,
        "samples/{0}{1:0=2d}/df_summary.csv".format(sampling_date.year, sampling_date.month),
    )

    # increment monthly end of month
    sampling_date += relativedelta(months=1, day=31)
    
    if sampling_date.month == 12:
        print("Done sampling year {}.".format(sampling_date.year))

# %%
