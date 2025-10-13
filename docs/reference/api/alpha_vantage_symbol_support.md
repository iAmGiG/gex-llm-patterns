# Alpha Vantage Options Symbol Support Analysis

**Date**: September 12, 2025  
**API Tier**: Premium (1000 calls/min)  
**Test Results**: Comprehensive symbol support testing

## Executive Summary

Alpha Vantage **does NOT support index options** (SPX, NDX, XND) but **does support ETF options** (SPY, QQQ, IWM). For GEX analysis of S&P 500 and Nasdaq 100, we must use ETF proxies.

## Supported Symbols ✅

| Symbol | Name | Contracts Available | Status |
|--------|------|-------------------|---------|
| **SPY** | SPDR S&P 500 ETF | Full option chains available | ✅ **ACTIVE** |
| **QQQ** | Invesco QQQ Trust (Nasdaq 100) | Full option chains available | ✅ **ACTIVE** |
| **IWM** | iShares Russell 2000 ETF | Available | ✅ **ACTIVE** |
| **DIA** | SPDR Dow Jones Industrial Average ETF | Available | ✅ **ACTIVE** |
| **GLD** | SPDR Gold Shares | Available | ✅ **ACTIVE** |
| **TLT** | iShares 20+ Year Treasury Bond ETF | Available | ✅ **ACTIVE** |

## Unsupported Symbols ❌

| Symbol | Name | Error Response | Reason |
|--------|------|----------------|---------|
| **SPX** | S&P 500 Index | No 'data' field returned | Index options not supported |
| **NDX** | Nasdaq 100 Index | No 'data' field returned | Index options not supported |
| **NDXP** | Nasdaq 100 Index (PM settled) | Invalid API call | Symbol not recognized |
| **XND** | Nasdaq 100 Micro Index | Invalid API call | Symbol not recognized |
| **NQX** | Nasdaq 100 Reduced Value Index | Invalid API call | Symbol not recognized |

## Index Mapping Strategy

Since Alpha Vantage doesn't support index options, use these ETF proxies:

### S&P 500 Analysis

- **Target**: SPX (S&P 500 Index) options
- **Alpha Vantage Proxy**: **SPY** (SPDR S&P 500 ETF)
- **Relationship**: SPY tracks SPX with ~99.9% correlation
- **GEX Implications**: SPY options reflect S&P 500 sentiment and gamma positioning

### Nasdaq 100 Analysis  

- **Target**: NDX (Nasdaq 100 Index) options
- **Alpha Vantage Proxy**: **QQQ** (Invesco QQQ Trust)
- **Relationship**: QQQ tracks NDX with ~99.9% correlation
- **GEX Implications**: QQQ options reflect Nasdaq 100 tech sector sentiment

## Technical Details

### Data Quality

- **SPY Options**: Full option chains with complete Greeks data
- **QQQ Options**: Full option chains with complete Greeks data
- **Columns Available**: 24 fields including IV, Delta, Gamma, Theta, Vega, Rho

### API Response Analysis

```
Index Options (SPX, NDX): 
- Response: 200 OK
- Data Field: Missing (empty response)
- Conclusion: Alpha Vantage doesn't provide index options data

ETF Options (SPY, QQQ):
- Response: 200 OK  
- Data Field: Present with full option chain
- Conclusion: Full options data available
```

### Rate Limits

- **Premium Tier**: 1000 calls/minute
- **Caching Strategy**: Unified cache management prevents redundant API calls
- **Storage**: Local caching system for efficient data access

## Recommendations

### ✅ Use These Symbols for GEX Analysis

1. **SPY** - Primary S&P 500 proxy (most liquid)
2. **QQQ** - Primary Nasdaq 100 proxy (tech sector)
3. **IWM** - Russell 2000 small caps
4. **DIA** - Dow Jones proxy (30 industrials)

### ❌ Cannot Use These Symbols

- **SPX, NDX, XND** - Not supported by Alpha Vantage
- **NDXP, NQX** - Invalid symbols

### 🔄 Alternative Data Sources (If Needed)

If index options are critical:

- **CBOE DataShop** - Direct index options data (paid)
- **Polygon.io** - Options data (may include indices)
- **Interactive Brokers API** - Full market data access
- **Yahoo Finance** - Limited free options data

## Impact on GEX Analysis

### Positive Aspects ✅

- **High liquidity**: SPY and QQQ are extremely liquid ETFs
- **Strong correlation**: 99.9+ correlation with underlying indices
- **Full Greeks**: Complete options data with IV, Delta, Gamma
- **Comprehensive coverage**: Full option chains provide extensive analysis capabilities

### Limitations ⚠️

- **Settlement differences**: ETFs are physically settled, indices are cash settled
- **Tracking error**: Small deviations from index performance
- **Options vs futures**: Missing pure index exposure (but ETFs are close proxy)

## Implementation Status

### Currently Working

- ✅ SPY GEX analysis operational
- ✅ QQQ data available and cached
- ✅ Premium API tier active (1000/min)
- ✅ Full Greeks data pipeline working

### Ready to Implement

- 🔄 **QQQ GEX Analysis**: Add to pattern detection pipeline
- 🔄 **Multi-Symbol Comparison**: SPY vs QQQ regime differences  
- 🔄 **Sector Analysis**: Tech (QQQ) vs Broad Market (SPY) gamma patterns
- 🔄 **Cross-Market Validation**: Test patterns across symbols

## Next Steps

1. **Add QQQ to GEX Pipeline**: Include Nasdaq 100 analysis alongside SPY
2. **Cross-Symbol Analysis**: Compare gamma patterns between SPY and QQQ
3. **Enhanced Testing**: Run Experiment 002 (Multi-Symbol Validation) with SPY+QQQ
4. **Documentation Update**: Update all references to use ETF proxies instead of indices

---

## Conclusion

**Alpha Vantage supports ETF options but NOT index options.** For comprehensive GEX analysis:

- **Use SPY** for S&P 500 analysis (instead of SPX)
- **Use QQQ** for Nasdaq 100 analysis (instead of NDX)
- **Both provide excellent liquidity and correlation** for gamma exposure analysis
- **Current system already has the infrastructure** to handle multiple symbols

The lack of pure index options is not a significant limitation given the high correlation and liquidity of the ETF proxies.
