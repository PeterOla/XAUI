"""
News sentiment extraction for gold trading (XAUUSD).
Captures pre-trade news sentiment from multiple sources during London/NY sessions.

Key news sources for gold:
- Federal Reserve announcements (interest rates, QE, inflation commentary)
- US economic data (NFP, CPI, GDP, jobless claims)
- Geopolitical events (conflicts, trade tensions)
- Central bank policy (ECB, BOE, SNB)
- USD strength indicators
- Risk-on/risk-off sentiment

News timing windows:
- 0-30 minutes before trade: immediate sentiment
- 30-60 minutes before: recent sentiment
- 1-3 hours before: session sentiment
- Same day pre-market: daily context

Sentiment scoring:
- Bullish for gold: +1 (USD weakness, rate cuts, risk-off, inflation fears)
- Neutral: 0
- Bearish for gold: -1 (USD strength, rate hikes, risk-on, deflation)

Data sources (priority order):
1. Economic calendar CSV (if available)
2. News headlines CSV (requires external data)
3. Manual event coding (major events like 2008 crisis, COVID, etc.)
"""
import argparse
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Major gold-moving events (manually researched historical analysis 2015-2025)
# Format: (date, hour_utc, sentiment, impact_level, description)
# Sentiment: +1 bullish gold, -1 bearish gold, 0 neutral/mixed
# Impact: 1=low, 2=medium, 3=high, 4=extreme
MAJOR_EVENTS = [
    # === 2015 ===
    ("2015-01-15", 9, 1, 4, "SNB removes Swiss franc cap - massive currency shock"),
    ("2015-01-29", 19, -1, 3, "Fed keeps rates near zero but signals hikes coming"),
    ("2015-03-18", 18, -1, 3, "Fed removes 'patient' language - rate hike imminent"),
    ("2015-06-17", 18, -1, 3, "Fed signals September rate hike likely"),
    ("2015-07-05", 13, 1, 3, "Greek referendum votes NO - Eurozone crisis"),
    ("2015-08-11", 9, 1, 4, "China devalues yuan 3 days straight - global panic"),
    ("2015-08-24", 9, 1, 4, "Black Monday - China fears crash global markets"),
    ("2015-09-17", 18, 1, 2, "Fed delays rate hike - global growth concerns"),
    ("2015-10-28", 18, 1, 2, "Fed keeps rates at zero - dovish tone"),
    ("2015-12-16", 19, -1, 4, "Fed first rate hike since 2006 - 25bp to 0.25-0.50%"),
    
    # === 2016 ===
    ("2016-01-04", 9, 1, 3, "China circuit breaker chaos - markets plunge"),
    ("2016-01-27", 19, 1, 2, "Fed holds rates - concerned about China/oil"),
    ("2016-02-11", 13, 1, 3, "Oil crashes to $26 - deflation fears"),
    ("2016-03-16", 18, 1, 3, "Fed turns dovish - only 2 hikes expected vs 4"),
    ("2016-04-27", 18, 1, 2, "Fed signals no rush to raise rates"),
    ("2016-06-23", 21, 1, 4, "Brexit referendum - UK votes to leave EU"),
    ("2016-06-24", 7, 1, 4, "Brexit aftermath - pound crashes, gold surges"),
    ("2016-07-27", 18, 1, 2, "Fed holds - Brexit uncertainty"),
    ("2016-09-21", 18, 1, 2, "Fed holds rates - divided committee"),
    ("2016-11-02", 13, 1, 3, "FBI reopens Clinton email probe - election uncertainty"),
    ("2016-11-08", 13, -1, 3, "Trump election night - initial shock then USD rally"),
    ("2016-11-09", 13, -1, 3, "Trump victory confirmed - reflation trade begins"),
    ("2016-12-14", 19, -1, 3, "Fed hikes 25bp + hawkish 2017 outlook"),
    
    # === 2017 ===
    ("2017-03-15", 18, -1, 3, "Fed hikes 25bp to 0.75-1.00% - confident tone"),
    ("2017-06-14", 18, -1, 3, "Fed hikes 25bp to 1.00-1.25% + balance sheet runoff plan"),
    ("2017-09-20", 18, -1, 2, "Fed announces balance sheet normalization start"),
    ("2017-12-13", 19, -1, 3, "Fed hikes 25bp to 1.25-1.50% + 3 hikes forecast 2018"),
    
    # === 2018 ===
    ("2018-01-31", 19, -1, 2, "Fed holds but signals March hike coming"),
    ("2018-02-05", 14, 1, 3, "Dow plunges 1,175 points - VIX explosion"),
    ("2018-03-21", 18, -1, 3, "Fed hikes 25bp to 1.50-1.75% - 6th hike of cycle"),
    ("2018-06-13", 18, -1, 3, "Fed hikes 25bp to 1.75-2.00% - 7th hike"),
    ("2018-09-26", 18, -1, 3, "Fed hikes 25bp to 2.00-2.25% - 8th hike, removes 'accommodative'"),
    ("2018-10-10", 13, 1, 3, "Stock market correction - Dow falls 1,300 points in 2 days"),
    ("2018-12-19", 19, -1, 3, "Fed hikes 25bp to 2.25-2.50% - 9th hike but dovish dot plot"),
    ("2018-12-24", 13, 1, 3, "Christmas Eve massacre - S&P 500 down 20% from peak"),
    
    # === 2019 ===
    ("2019-01-30", 19, 1, 3, "Fed turns patient - no more rate hikes"),
    ("2019-03-20", 18, 1, 3, "Fed dovish pivot - no hikes in 2019, QT ends soon"),
    ("2019-05-05", 13, 1, 3, "Trump escalates China trade war - tariff threats"),
    ("2019-06-19", 18, 1, 3, "Fed signals rate cuts coming - insurance cuts"),
    ("2019-07-31", 18, 1, 4, "Fed cuts rates 25bp - first cut since 2008"),
    ("2019-08-05", 9, 1, 3, "China lets yuan weaken past 7.0 - trade war escalates"),
    ("2019-08-23", 13, 1, 3, "Trump announces more China tariffs - markets tumble"),
    ("2019-09-18", 18, 1, 3, "Fed cuts 25bp again - insurance against slowdown"),
    ("2019-10-30", 18, 1, 2, "Fed cuts 25bp third time - mid-cycle adjustment complete"),
    
    # === 2020 ===
    ("2020-01-27", 13, 1, 3, "Coronavirus fears escalate - Wuhan lockdown"),
    ("2020-02-24", 13, 1, 3, "Italy COVID outbreak - Europe panic begins"),
    ("2020-02-27", 13, 1, 3, "Dow falls 1,191 points - worst day since 2018"),
    ("2020-03-03", 14, 1, 4, "Fed emergency 50bp rate cut - COVID panic mode"),
    ("2020-03-09", 13, 1, 4, "Oil price war + COVID - Black Monday, circuit breakers"),
    ("2020-03-12", 13, 1, 4, "Black Thursday - Dow falls 2,352 points, circuit breakers"),
    ("2020-03-15", 21, 1, 4, "Fed emergency cuts rates to zero + $700B QE"),
    ("2020-03-16", 13, 1, 4, "Markets plunge despite Fed - worst day since 1987"),
    ("2020-03-18", 13, 1, 4, "Global deleveraging - everything selling off"),
    ("2020-03-23", 13, 1, 4, "Fed announces unlimited QE - 'whatever it takes'"),
    ("2020-04-29", 18, 1, 2, "Fed holds rates at zero - recession confirmed"),
    ("2020-06-10", 18, 1, 2, "Fed extends emergency programs - no rate hikes through 2022"),
    ("2020-08-27", 13, 1, 3, "Powell announces average inflation targeting - dovish"),
    ("2020-11-03", 13, 1, 2, "Election day uncertainty - Biden vs Trump"),
    ("2020-11-09", 13, -1, 2, "Pfizer vaccine 90% effective - risk-on surge"),
    ("2020-12-16", 19, 1, 2, "Fed commits to QE until substantial progress - ultra dovish"),
    
    # === 2021 ===
    ("2021-01-06", 18, 1, 3, "Georgia runoff gives Democrats Senate - stimulus hopes"),
    ("2021-01-27", 19, 1, 2, "Fed holds - inflation not a concern yet"),
    ("2021-03-17", 18, 1, 2, "Fed sees rates near zero through 2023"),
    ("2021-04-28", 18, 1, 2, "Fed sees inflation as transitory"),
    ("2021-06-16", 18, 1, 3, "Fed hawkish surprise - dot plot shows 2023 hikes"),
    ("2021-07-28", 18, 1, 2, "Fed holds but acknowledges Delta variant risks"),
    ("2021-09-22", 18, 1, 3, "Fed signals taper coming soon - November likely"),
    ("2021-11-03", 18, 1, 3, "Fed announces $15B/month taper starting mid-November"),
    ("2021-12-15", 19, -1, 3, "Fed doubles taper to $30B/month - 3 hikes in 2022"),
    
    # === 2022 ===
    ("2022-01-26", 19, -1, 3, "Fed signals March hike + balance sheet runoff"),
    ("2022-02-24", 8, 1, 4, "Russia invades Ukraine - safe haven surge"),
    ("2022-03-16", 18, -1, 4, "Fed starts tightening cycle - 25bp hike, QT coming"),
    ("2022-04-11", 13, -1, 3, "CPI hits 8.5% - highest since 1981"),
    ("2022-05-04", 18, -1, 4, "Fed hikes 50bp - first half-point hike since 2000"),
    ("2022-06-10", 13, -1, 3, "CPI hits 8.6% - new 40-year high"),
    ("2022-06-15", 18, -1, 4, "Fed hikes 75bp - largest since 1994, hawkish shock"),
    ("2022-07-13", 13, -1, 3, "CPI 9.1% - highest inflation in 40 years"),
    ("2022-07-27", 18, -1, 3, "Fed hikes 75bp again - recession fears grow"),
    ("2022-09-13", 13, -1, 3, "CPI still hot at 8.3% - core accelerates"),
    ("2022-09-21", 18, -1, 4, "Fed hikes 75bp third time - terminal rate now 4.6%"),
    ("2022-11-02", 18, -1, 4, "Fed hikes 75bp fourth consecutive - most aggressive cycle ever"),
    ("2022-11-10", 13, -1, 3, "CPI cools to 7.7% - first sign of peak"),
    ("2022-12-13", 13, -1, 2, "CPI 7.1% - inflation clearly cooling"),
    ("2022-12-14", 19, -1, 3, "Fed hikes 50bp - slowing pace but higher terminal rate 5.1%"),
    
    # === 2023 ===
    ("2023-02-01", 19, -1, 3, "Fed hikes 25bp to 4.50-4.75% - inflation still elevated"),
    ("2023-02-14", 13, -1, 2, "CPI 6.4% - sticky inflation"),
    ("2023-03-08", 13, 1, 3, "SVB shuts down - banking stress emerging"),
    ("2023-03-10", 13, 1, 4, "Silicon Valley Bank fails - biggest bank collapse since 2008"),
    ("2023-03-12", 13, 1, 4, "Signature Bank seized - contagion fears"),
    ("2023-03-13", 13, 1, 4, "Fed/Treasury emergency measures - backstop all deposits"),
    ("2023-03-15", 13, 1, 3, "Credit Suisse crisis - AT1 bonds wiped out"),
    ("2023-03-19", 13, 1, 3, "UBS forced to rescue Credit Suisse"),
    ("2023-03-22", 18, 1, 4, "Fed hikes 25bp despite banking crisis - inflation priority"),
    ("2023-05-03", 18, 1, 3, "Fed hikes 25bp to 5.00-5.25% but hints at pause"),
    ("2023-05-24", 13, 1, 2, "Debt ceiling crisis escalates"),
    ("2023-06-14", 18, 1, 3, "Fed pauses rate hikes - first since March 2022"),
    ("2023-07-26", 18, -1, 3, "Fed hikes 25bp to 5.25-5.50% - 22-year high"),
    ("2023-09-20", 18, 1, 2, "Fed holds rates - higher for longer message"),
    ("2023-10-07", 13, 1, 4, "Hamas attacks Israel - geopolitical shock"),
    ("2023-11-01", 18, 1, 2, "Fed holds at 5.25-5.50% - inflation easing"),
    ("2023-12-13", 19, 1, 3, "Fed holds but signals 75bp cuts in 2024 - dovish pivot"),
    
    # === 2024 ===
    ("2024-01-31", 19, 1, 2, "Fed holds - no rush to cut despite progress"),
    ("2024-03-20", 18, 1, 3, "Fed holds but still sees 3 cuts in 2024"),
    ("2024-05-01", 18, 1, 2, "Fed holds - inflation progress stalled"),
    ("2024-06-12", 18, 1, 2, "Fed holds - only 1 cut now expected in 2024"),
    ("2024-07-31", 18, 1, 2, "Fed holds - cutting in September likely"),
    ("2024-09-18", 18, 1, 4, "Fed cuts 50bp - first cut since 2020, larger than expected"),
    ("2024-11-05", 13, -1, 3, "Trump wins presidency again - reflation trade 2.0"),
    ("2024-11-07", 19, -1, 3, "Fed cuts 25bp but Powell notes Trump policy uncertainty"),
    
    # === 2025 ===
    ("2025-01-29", 19, 1, 2, "Fed holds rates - cautious on tariff inflation"),
    ("2025-03-19", 18, 1, 3, "Fed cuts 25bp despite tariff concerns"),
]

# US economic calendar - high impact events (time in UTC)
ECONOMIC_CALENDAR_EVENTS = {
    # NFP (Non-Farm Payrolls) - First Friday of month at 13:30 UTC
    "NFP": {"time": "13:30", "impact": "high", "days": [5]},  # Friday (dow=4)
    
    # CPI (Consumer Price Index) - Mid-month around 13:30 UTC
    "CPI": {"time": "13:30", "impact": "high"},
    
    # FOMC meetings - 8 times per year, decision at 18:00 UTC, presser at 18:30 UTC
    "FOMC": {"time": "18:00", "impact": "extreme"},
    
    # GDP releases - Quarterly at 13:30 UTC
    "GDP": {"time": "13:30", "impact": "high"},
    
    # Unemployment claims - Thursday at 13:30 UTC
    "CLAIMS": {"time": "13:30", "impact": "medium", "days": [3]},  # Thursday (dow=3)
}

def parse_date(date_str):
    """Parse date string to datetime.date."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def get_news_sentiment_features(entry_time: pd.Timestamp, use_major_events=True, use_calendar=False):
    """
    Extract news sentiment features for a given entry time.
    
    Returns dict with:
    - sentiment_0_30min: immediate pre-trade sentiment (-1 to +1)
    - sentiment_30_60min: recent sentiment
    - sentiment_1_3hr: session sentiment
    - sentiment_today: daily sentiment
    - event_impact: magnitude (0=none, 1=low, 2=medium, 3=high, 4=extreme)
    - minutes_since_event: time since last major event
    """
    entry_date = entry_time.date()
    entry_hour = entry_time.hour
    entry_minute = entry_time.minute
    
    features = {
        "sentiment_0_30min": 0,
        "sentiment_30_60min": 0,
        "sentiment_1_3hr": 0,
        "sentiment_today": 0,
        "event_impact": 0,
        "minutes_since_event": np.nan,
        "has_event_nearby": 0,
    }
    
    # Check major events
    if use_major_events:
        recent_events = []
        
        for event_date_str, event_hour, sentiment, impact, description in MAJOR_EVENTS:
            event_date = parse_date(event_date_str)
            event_dt = datetime.combine(event_date, datetime.min.time()).replace(hour=event_hour)
            entry_dt = entry_time.to_pydatetime().replace(tzinfo=None)
            
            time_diff_minutes = (entry_dt - event_dt).total_seconds() / 60
            
            # Event is in the past and within relevant window
            if 0 <= time_diff_minutes <= 180:  # 0-3 hours ago
                impact_decay = np.exp(-time_diff_minutes / 90)  # Exponential decay with 1.5hr half-life (faster for gold)
                weighted_sentiment = sentiment * impact_decay
                
                recent_events.append({
                    "minutes_ago": time_diff_minutes,
                    "sentiment": sentiment,
                    "weighted_sentiment": weighted_sentiment,
                    "impact": impact,  # 1=low, 2=medium, 3=high, 4=extreme
                    "description": description
                })
        
        # Aggregate sentiments by time window
        if recent_events:
            # 0-30 minutes
            events_0_30 = [e for e in recent_events if e["minutes_ago"] <= 30]
            if events_0_30:
                features["sentiment_0_30min"] = np.mean([e["weighted_sentiment"] for e in events_0_30])
                features["event_impact"] = max([e["impact"] for e in events_0_30])
                features["minutes_since_event"] = min([e["minutes_ago"] for e in events_0_30])
                features["has_event_nearby"] = 1
            
            # 30-60 minutes
            events_30_60 = [e for e in recent_events if 30 < e["minutes_ago"] <= 60]
            if events_30_60:
                features["sentiment_30_60min"] = np.mean([e["weighted_sentiment"] for e in events_30_60])
                if features["event_impact"] == 0:  # No closer event found
                    features["event_impact"] = max([e["impact"] for e in events_30_60])
                    features["minutes_since_event"] = min([e["minutes_ago"] for e in events_30_60])
                    features["has_event_nearby"] = 1
            
            # 1-3 hours
            events_1_3hr = [e for e in recent_events if 60 < e["minutes_ago"] <= 180]
            if events_1_3hr:
                features["sentiment_1_3hr"] = np.mean([e["weighted_sentiment"] for e in events_1_3hr])
                if features["event_impact"] == 0:  # No closer event found
                    features["event_impact"] = max([e["impact"] for e in events_1_3hr])
                    features["minutes_since_event"] = min([e["minutes_ago"] for e in events_1_3hr])
                    features["has_event_nearby"] = 1
            
            # Today aggregate
            features["sentiment_today"] = np.mean([e["weighted_sentiment"] for e in recent_events])
    
    # Check economic calendar patterns (heuristic - would need actual calendar data for precision)
    if use_calendar:
        dow = entry_time.dayofweek
        
        # NFP Friday pattern (first Friday of month, 13:30 UTC)
        if dow == 4 and entry_hour >= 13:  # Friday afternoon
            day_of_month = entry_time.day
            if 1 <= day_of_month <= 7:  # First week of month
                # Likely NFP day
                if entry_hour == 13 and entry_minute >= 30:
                    features["has_event_nearby"] = 1
                    features["event_impact"] = 3  # High impact
                    features["minutes_since_event"] = (entry_hour - 13) * 60 + (entry_minute - 30)
        
        # Jobless claims Thursday pattern (13:30 UTC)
        if dow == 3 and entry_hour >= 13:  # Thursday afternoon
            if entry_hour == 13 and entry_minute >= 30:
                features["has_event_nearby"] = 1
                features["event_impact"] = 2  # Medium impact
                features["minutes_since_event"] = (entry_hour - 13) * 60 + (entry_minute - 30)
    
    return features

def extract_news_features_for_trades(trades_csv: str, out_parquet: str):
    """
    Extract news sentiment features for all trades.
    """
    print("Loading trades...")
    trades = pd.read_csv(trades_csv)
    trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
    
    print(f"Extracting news sentiment for {len(trades)} trades...")
    print("Using major events database (2015-2025)")
    print(f"Events: {len(MAJOR_EVENTS)} major gold-moving events coded")
    
    feature_rows = []
    
    for idx, trade in trades.iterrows():
        entry_ts = trade["entry_time"]
        
        # Get news sentiment features
        news_features = get_news_sentiment_features(entry_ts, use_major_events=True, use_calendar=True)
        
        # Add trade info
        row = {
            "entry_time": entry_ts,
            "side": trade.get("side", "long"),
            **news_features,
            "pips": trade.get("pips", 0),
            "label_win": int(trade.get("pips", 0) > 0),
        }
        
        feature_rows.append(row)
        
        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1} / {len(trades)} trades...")
    
    df_features = pd.DataFrame(feature_rows)
    
    # Save to parquet
    Path(os.path.dirname(out_parquet)).mkdir(parents=True, exist_ok=True)
    df_features.to_parquet(out_parquet, index=False)
    
    # Save metadata
    feature_cols = [c for c in df_features.columns if c not in ["entry_time", "side", "pips", "label_win"]]
    meta = {
        "feature_columns": feature_cols,
        "n_features": len(feature_cols),
        "n_trades": len(df_features),
        "major_events_count": len(MAJOR_EVENTS),
        "description": "News sentiment features: major events (2015-2025), economic calendar patterns, time-decayed sentiment in multiple windows",
    }
    
    meta_path = out_parquet.replace(".parquet", "_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    
    print(f"\n✅ News sentiment features extracted for {len(df_features)} trades")
    print(f"   Features saved: {out_parquet}")
    print(f"   Feature columns: {len(feature_cols)}")
    print(f"   Trades with nearby events: {(df_features['has_event_nearby'] == 1).sum()}")
    
    # Statistics
    nearby_mask = df_features['has_event_nearby'] == 1
    if nearby_mask.any():
        print(f"\n📊 Trades near major events:")
        print(f"   Count: {nearby_mask.sum()}")
        print(f"   Win rate: {df_features[nearby_mask]['label_win'].mean():.2%}")
        print(f"   Avg pips: {df_features[nearby_mask]['pips'].mean():.2f}")
        print(f"   Compare to all trades: {df_features['label_win'].mean():.2%} WR, {df_features['pips'].mean():.2f} pips")
    
    return df_features

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades-csv", required=True, help="Path to trades CSV")
    ap.add_argument("--out-parquet", required=True, help="Output parquet path")
    args = ap.parse_args()
    
    extract_news_features_for_trades(args.trades_csv, args.out_parquet)

if __name__ == "__main__":
    main()
