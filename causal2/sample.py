import pandas as pd
import numpy as np

np.random.seed(42)
n = 100

df = pd.DataFrame({
    "FedRate": np.random.normal(2, 0.5, n),
    "GDP": np.random.normal(20000, 500, n),
    "CPI": np.random.normal(250, 10, n),
    "UNRATE": np.random.normal(5, 1, n),
    "SP500": np.random.normal(3000, 100, n)
})

# Save as Parquet
df.to_parquet("sample_for_causal.parquet")
print("Sample file saved as sample_for_causal.parquet")