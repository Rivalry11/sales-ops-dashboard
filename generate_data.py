"""
generate_data.py
Creates realistic synthetic sales data with seasonality, trend, and noise.
Run once: python generate_data.py
Output: data/sales_data.csv
"""
import numpy as np
import pandas as pd
import os
from datetime import datetime, timedelta

np.random.seed(42)

# ---- CONFIG ----
START_DATE = datetime(2024, 4, 1)
END_DATE = datetime(2025, 3, 31)
REGIONS = ["North America", "LATAM", "EMEA", "APAC"]
PRODUCT_CATEGORIES = ["Electronics", "Home & Garden", "Apparel", "Beauty", "Sports"]
CHANNELS = ["Online", "Retail Store", "Partner", "Marketplace"]

# Regional weights (relative market size)
REGION_WEIGHTS = {"North America": 0.40, "LATAM": 0.18, "EMEA": 0.28, "APAC": 0.14}

# Category base prices (USD)
CATEGORY_PRICES = {
    "Electronics": (80, 600),
    "Home & Garden": (25, 200),
    "Apparel": (20, 120),
    "Beauty": (15, 80),
    "Sports": (30, 250),
}

# Channel multipliers
CHANNEL_MULT = {"Online": 1.0, "Retail Store": 1.1, "Partner": 0.9, "Marketplace": 0.85}


def generate_daily_volume(date, region):
    """Realistic daily volume with trend, seasonality, and weekday effects."""
    day_of_year = date.timetuple().tm_yday
    days_since_start = (date - START_DATE).days

    # Base volume per region
    base = {"North America": 450, "LATAM": 200, "EMEA": 320, "APAC": 160}[region]

    # Annual seasonality (sine wave: peak in Nov-Dec for holidays)
    seasonal = 1 + 0.35 * np.sin(2 * np.pi * (day_of_year - 80) / 365)

    # Q4 holiday boost (Nov-Dec)
    if date.month in [11, 12]:
        seasonal *= 1.4

    # Weekend bump for online behavior
    weekday_mult = 1.15 if date.weekday() >= 5 else 1.0

    # Growth trend (5% over the year)
    trend = 1 + 0.05 * (days_since_start / 365)

    # Random noise
    noise = np.random.normal(1.0, 0.08)

    volume = base * seasonal * weekday_mult * trend * noise
    return max(int(volume), 10)


def generate_forecast(actual_volume):
    """Forecast = actual with realistic operational error (~8-12% MAPE)."""
    # Real ops forecasts achieve ~88-92% accuracy → MAPE of 8-12%
    # Use tight gaussian noise; occasional misses simulate real-world anomalies
    base_error = np.random.normal(1.0, 0.06)
    # 5% chance of a larger miss (promo, stockout, external event)
    if np.random.random() < 0.05:
        base_error *= np.random.choice([0.75, 1.25])
    return max(int(actual_volume * base_error), 10)


def main():
    os.makedirs("data", exist_ok=True)

    rows = []
    current = START_DATE
    while current <= END_DATE:
        for region in REGIONS:
            total_volume = generate_daily_volume(current, region)
            forecast_volume = generate_forecast(total_volume)

            # Distribute volume across categories & channels
            for _ in range(total_volume):
                category = np.random.choice(PRODUCT_CATEGORIES)
                channel = np.random.choice(CHANNELS, p=[0.55, 0.25, 0.10, 0.10])

                price_min, price_max = CATEGORY_PRICES[category]
                base_price = np.random.uniform(price_min, price_max)
                final_price = base_price * CHANNEL_MULT[channel]

                # Occasional discount
                if np.random.random() < 0.15:
                    final_price *= np.random.uniform(0.7, 0.9)

                quantity = np.random.choice([1, 1, 1, 2, 2, 3], p=[0.4, 0.2, 0.15, 0.1, 0.1, 0.05])
                revenue = final_price * quantity

                # Fulfillment time (operations metric)
                if channel == "Online":
                    fulfillment_hours = np.random.gamma(2, 12)
                elif channel == "Retail Store":
                    fulfillment_hours = np.random.uniform(0.1, 2)
                else:
                    fulfillment_hours = np.random.gamma(2, 18)

                rows.append({
                    "date": current.strftime("%Y-%m-%d"),
                    "region": region,
                    "category": category,
                    "channel": channel,
                    "unit_price": round(final_price, 2),
                    "quantity": quantity,
                    "revenue": round(revenue, 2),
                    "fulfillment_hours": round(fulfillment_hours, 2),
                    "forecast_volume": forecast_volume,
                })

        current += timedelta(days=1)

    df = pd.DataFrame(rows)
    output_path = "data/sales_data.csv"
    df.to_csv(output_path, index=False)

    print(f"✓ Generated {len(df):,} transactions")
    print(f"✓ Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"✓ Total revenue: ${df['revenue'].sum():,.0f}")
    print(f"✓ Saved to: {output_path}")


if __name__ == "__main__":
    main()
