# Deployment Guide - Combined News Filter Strategy

## Quick Start

### 1. Deploy to Paper Trading
```bash
python scripts/deploy_live_strategy.py --mode paper
```

### 2. Monitor Performance
```bash
python scripts/monitor_performance.py --mode paper
```

### 3. Generate Reports
```bash
python scripts/monitor_performance.py --mode paper --plot --export report.html
```

---

## Deployment Configuration

### Strategy Parameters (Validated on Test Set)
- **Filter Type:** Combined (bullish OR bearish)
- **Bearish Threshold:** net_sentiment < -0.1
- **Bullish Threshold:** net_sentiment > 0.3
- **Min Headlines:** 5 per trade
- **Trading Hours:** 13:00 - 16:00 UTC (New York overlap)
- **SuperTrend:** Period 10, Multiplier 3.6

### Expected Performance (from Backtest)
- **Trades per Month:** 6.7
- **Profit Factor:** 1.355
- **Win Rate:** 45%
- **Avg Pips per Trade:** 41.40
- **Annual Expected:** ~80 trades, ~3,300 pips

### Risk Management
- **Max Position Size:** 0.01 lots (start small!)
- **Max Daily Trades:** 3
- **Max Daily Loss:** 500 pips
- **Max Acceptable Drawdown:** 2,500 pips

---

## Pre-Deployment Checklist

### ✅ Data Quality
- [x] Look-ahead bias removed (7.35% future headlines eliminated)
- [x] Clean dataset: 38,700 headlines, all timestamped before trades
- [x] Sentiment analysis validated on test set

### ✅ Backtest Validation
- [x] Test period: Jan 2024 - Oct 2025 (21 months)
- [x] 140 trades executed
- [x] PF 1.355 (passes 1.25 gate ✅)
- [x] WR 45% (passes 38% gate ✅)
- [x] All deployment gates passed

### ✅ Code Verification
- [x] Strategy script supports combined filter
- [x] News sentiment pipeline working
- [x] SuperTrend signals validated
- [x] Both-sides trading enabled

### 📋 Before Going Live
- [ ] Run validation on most recent 90 days
- [ ] Set up broker API connection
- [ ] Test with minimum position size (0.01 lots)
- [ ] Enable detailed logging
- [ ] Set up monitoring alerts

---

## Step-by-Step Deployment

### Phase 1: Paper Trading (Week 1-2)

**Day 1: Initial Deployment**
```bash
# Deploy to paper trading
python scripts/deploy_live_strategy.py --mode paper --validate

# This will:
# 1. Validate on recent 90 days
# 2. Setup monitoring directory (results/live_paper/)
# 3. Create trades log and metrics tracker
```

**Daily Monitoring (Days 2-14):**
```bash
# Check performance daily
python scripts/monitor_performance.py --mode paper

# Weekly reports
python scripts/monitor_performance.py --mode paper --plot --export weekly_report.html
```

**What to Watch:**
- Trade frequency: Expect ~0.3-0.4 trades/day (6.7/month)
- Win rate: Should stay above 35%
- Profit factor: Target >1.20
- Drawdown: Alert if >2,500 pips

### Phase 2: Live Trading (Week 3+)

**Pre-Live Checks:**
```bash
# Review paper trading results
python scripts/monitor_performance.py --mode paper

# Should see:
# - At least 10-15 trades
# - PF >1.20
# - WR >35%
# - No major alerts
```

**Go Live:**
```bash
# Deploy to live (REAL MONEY!)
python scripts/deploy_live_strategy.py --mode live

# Confirm with 'YES' when prompted
```

**Risk Controls:**
- Start with **0.01 lots** only
- Increase to 0.02 lots after 20 profitable trades
- Maximum 0.1 lots per trade
- Stop trading if daily loss >500 pips

---

## Monitoring & Alerts

### Daily Checklist
- [ ] Check trade count (expect ~0.3-0.4 per day)
- [ ] Review win rate (target >40%)
- [ ] Monitor cumulative P&L
- [ ] Check for alert thresholds

### Weekly Review
- [ ] Calculate weekly PF (target >1.25)
- [ ] Review drawdown (max 2,500 pips)
- [ ] Analyze filter breakdown (bullish vs bearish)
- [ ] Generate equity curve plot
- [ ] Export HTML report for records

### Monthly Revalidation
- [ ] Run backtest on rolling 90-day window
- [ ] Compare live vs backtest performance
- [ ] Check if strategy still passes deployment gates
- [ ] Refresh GDELT data and re-run sentiment analysis
- [ ] Adjust thresholds if needed

### Alert Thresholds

**🚨 STOP TRADING if:**
- Profit Factor drops below 1.0 (losing strategy)
- Max drawdown exceeds 3,000 pips
- Win rate falls below 30% for 20+ trades
- Daily loss exceeds 500 pips

**⚠️ WARNING if:**
- Profit Factor <1.20 for 20+ trades
- Win rate <35% for 20+ trades
- Drawdown >2,500 pips
- Trade frequency <4/month or >10/month

**✅ GOOD if:**
- PF >1.25
- WR >40%
- Drawdown <2,000 pips
- Frequency 5-8 trades/month

---

## Logging & Record Keeping

### Trade Log Format
Each trade logged in `results/live_{mode}/live_trades.csv`:
```csv
entry_time,side,entry_price,exit_price,pips,headline_count,net_sentiment,filter_type
2025-11-12 14:30:00,BUY,2650.50,2655.80,53.0,8,0.35,strong_bullish
```

### Metrics History
Tracked in `results/live_{mode}/live_metrics.json`:
```json
{
  "total_trades": 15,
  "win_rate": 0.4667,
  "profit_factor": 1.42,
  "avg_pips": 38.5,
  "total_pips": 577.5,
  "max_drawdown": 485.2,
  "last_updated": "2025-11-12T15:30:00"
}
```

### Reports Generated
- **Daily:** Console summary via `monitor_performance.py`
- **Weekly:** HTML report + equity curve chart
- **Monthly:** Full performance review + revalidation

---

## Troubleshooting

### Issue: No trades being executed
**Possible causes:**
- No SuperTrend signals during 13-16 UTC
- News sentiment doesn't meet thresholds
- Headline count <5

**Solution:**
- Check if market is open (Mon-Fri)
- Verify GDELT data is updating
- Review sentiment thresholds (may need adjustment)

### Issue: Win rate dropping
**Possible causes:**
- Market regime change
- News sentiment losing predictive power
- SuperTrend parameters no longer optimal

**Solution:**
- Run 90-day rolling backtest
- Check if recent performance deviates >20% from backtest
- Consider retraining on recent data

### Issue: Drawdown exceeding limits
**Possible causes:**
- Unfavorable market conditions
- Position sizing too large
- Consecutive losses (normal variance)

**Solution:**
- Reduce position size by 50%
- Take a break if DD >2,500 pips
- Wait for drawdown to recover before resuming

---

## Performance Comparison

### Backtest (Test Set: Jan 2024 - Oct 2025)
| Metric | Value |
|--------|-------|
| Trades | 140 |
| Frequency | 6.7/month |
| PF | 1.355 |
| WR | 45% |
| Avg Pips | 41.40 |
| Total Pips | +5,797 |
| Max DD | -2,079 |

### Live Target (First Month)
| Metric | Target |
|--------|--------|
| Trades | 5-8 |
| PF | >1.20 |
| WR | >35% |
| Total Pips | >200 |
| Max DD | <1,000 |

---

## Next Steps After Deployment

### Short Term (Month 1-3)
1. Build confidence in paper trading
2. Validate performance matches backtest
3. Transition to live with minimal risk
4. Establish monitoring routine

### Medium Term (Month 4-6)
1. Scale position size gradually
2. Optimize thresholds based on live data
3. Begin Phase 4 research (ML Entry System)
4. Test multi-timeframe expansion (5m, 15m)

### Long Term (Month 7-12)
1. Deploy ML-enhanced entry system
2. Expand to 24-hour trading (not just 13-16 UTC)
3. Add multi-instrument support (EURUSD, GBPUSD)
4. Target 10-20 trades/month with PF >1.30

---

## Command Reference

### Deployment
```bash
# Paper trading
python scripts/deploy_live_strategy.py --mode paper

# Live trading (with validation)
python scripts/deploy_live_strategy.py --mode live --validate
```

### Monitoring
```bash
# Daily check
python scripts/monitor_performance.py --mode paper

# With charts
python scripts/monitor_performance.py --mode paper --plot

# Export report
python scripts/monitor_performance.py --mode paper --export report.html
```

### Backtest Validation
```bash
# Last 90 days
python scripts/strategy_with_news_filter.py \
  --use-news-filter \
  --filter-type combined \
  --both-sides \
  --entry-hours 13-16 \
  --date-start 2025-08-15

# Full test set
python scripts/strategy_with_news_filter.py \
  --use-news-filter \
  --filter-type combined \
  --both-sides \
  --entry-hours 13-16 \
  --date-start 2024-01-10
```

---

## Support & Maintenance

### Weekly Tasks
- Monitor performance dashboard
- Check for alerts
- Generate weekly report
- Review equity curve

### Monthly Tasks
- Revalidate on rolling 90 days
- Update GDELT headlines
- Re-run sentiment analysis
- Check deployment gates still pass

### Quarterly Tasks
- Comprehensive performance review
- Re-optimize thresholds if needed
- Backtest on full recent year
- Update documentation

---

## Contact & Escalation

### When to Seek Help
- PF drops below 1.0 for 30+ trades
- Win rate <30% sustained
- Technical issues with data feeds
- Broker API problems

### Resources
- Documentation: `docs/` folder
- Backtest results: `results/combined/`
- Strategy code: `scripts/strategy_with_news_filter.py`
- Monitoring: `scripts/monitor_performance.py`

---

**Ready to Deploy!** 🚀

Start with paper trading, monitor closely, and scale gradually to live trading once confidence is established.
