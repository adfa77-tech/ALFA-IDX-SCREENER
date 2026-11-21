import json
import math
import os
import time
import urllib.error
import urllib.request
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="ALPHA IDX • IHSG & ISSI Screener + AI")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ISSI_REPO_FILE = os.path.join(BASE_DIR, "issi_list.txt")
ISSI_TMP_FILE = "/tmp/issi_list.txt"

CACHE_TTL = 25
_cache = {"timestamp": 0, "data": None}

DEFAULT_ISSI = {
    "AADI", "AALI", "ABMM", "ACES", "ADHI", "ADMR", "ADRO", "AGII", "AKRA", "ALDO",
    "AMFG", "AMMN", "AMRT", "ANJT", "ANTM", "APLN", "ARCI", "ARNA", "ARTO", "ASII",
    "ASRI", "ASSA", "AUTO", "AVIA", "BALI", "BANK", "BELI", "BEST", "BIRD", "BISI",
    "BKSL", "BMHS", "BMTR", "BREN", "BRIS", "BRMS", "BRPT", "BSDE", "BSSR", "BTPS",
    "BUDI", "BUKA", "BULL", "BUMI", "BWPT", "BYAN", "CAMP", "CARE", "CARS", "CEKA",
    "CENT", "CINT", "CLEO", "CMNP", "CMRY", "CPIN", "CSAP", "CTBN", "CTRA", "CUAN",
    "DCII", "DEWA", "DGNS", "DIVA", "DKFT", "DMAS", "DMMX", "DOID", "DOOH", "DRMA",
    "DSNG", "DVLA", "EAST", "ECII", "EDGE", "EKAD", "ELSA", "EMTK", "ENRG", "EPMT",
    "ERAA", "ESSA", "EXCL", "FAST", "FILM", "FIRE", "FPNI", "GEMS", "GHSI", "GJTL",
    "GLVA", "GOOD", "GOTO", "GZCO", "HALO", "HEAL", "HERO", "HOKI", "HRUM", "ICBP",
    "IFII", "IGAR", "IMAS", "INAI", "INCO", "INDF", "INDY", "INET", "INKP", "INTP",
    "IPCC", "IPCM", "IRRA", "ISAT", "ISSP", "ITMG", "JECC", "JPFA", "JRPT", "JSMR",
    "KAEF", "KBLI", "KBLM", "KEEN", "KEJU", "KIJA", "KKGI", "KLBF", "KMTR", "KPIG",
    "KRAS", "LION", "LPCK", "LPIN", "LPKR", "LPPF", "LSIP", "MAIN", "MAPA", "MAPB",
    "MAPI", "MARK", "MBAP", "MBMA", "MBSS", "MCAS", "MDKA", "MEDC", "MERK", "MIDI",
    "MIKA", "MMLP", "MNCN", "MPMX", "MPPA", "MTEL", "MTDL", "MTLA", "MYOH", "MYOR",
    "NCKL", "NFCX", "NRCA", "NSSS", "PANI", "PBID", "PEHA", "PGAS", "PGEO", "PJAA",
    "PLIN", "PNBS", "POWR", "PPRE", "PRDA", "PSAB", "PTBA", "PTPP", "PTRO", "PWON",
    "PYFA", "PZZA", "RAAM", "RAJA", "RALS", "RDTX", "RMKE", "ROTI", "SAME", "SCCO",
    "SCMA", "SGER", "SGRO", "SHIP", "SIDO", "SILO", "SIMP", "SKBM", "SLIS", "SMDR",
    "SMGR", "SMRA", "SMSM", "SOHO", "SPMA", "SRAJ", "SRTG", "SSIA", "SSMS", "STAA",
    "STTP", "TAPG", "TBIG", "TBLA", "TCPI", "TGKA", "TINS", "TKIM", "TLKM", "TMAS",
    "TOBA", "TOTL", "TOTO", "TOWR", "TPIA", "TRGU", "TSPC", "ULTJ", "UNTR", "UNVR",
    "VKTR", "VOKS", "WEGE", "WEHA", "WIFI", "WIKA", "WOOD", "WTON", "ZINC", "ZONE",
}

NON_SYARIAH_TICKERS = {
    "BBCA", "BBRI", "BMRI", "BBNI", "BBTN", "BDMN", "BNGA", "BNLI", "MEGA", "NISP",
    "PNBN", "BBKP", "BJBR", "BJTM", "BTPN", "BNII", "MAYA", "AGRO", "BBYB", "AMAR",
    "GGRM", "HMSP", "WIIM", "RMBA", "ITIC", "MLBI", "DLTA", "ADMF", "BFIN", "CFIN",
    "PNLF", "PNIN", "ASRM", "LPGI", "TUGU", "MREI", "TRIM", "PANS",
}

NON_SYARIAH_KEYWORDS = (
    "tobacco", "brewer", "distiller", "casino", "gambling", "insurance", "consumer finance"
)

FULL_COLS = [
    "name", "description", "sector", "industry", "close", "open", "high", "low",
    "change", "volume", "average_volume_10d_calc", "relative_volume_10d_calc",
    "market_cap_basic", "RSI", "RSI[1]", "Stoch.K", "Stoch.D", "MACD.macd",
    "MACD.signal", "EMA10", "EMA20", "EMA50", "EMA200", "SMA20", "SMA50", "SMA200",
    "ADX", "ADX+DI", "ADX-DI", "BB.upper", "BB.lower", "ATR", "VWAP", "VWMA",
    "Recommend.All", "Recommend.MA", "Recommend.Other", "Perf.W", "Perf.1M",
    "price_52_week_high", "price_52_week_low", "Pivot.M.Classic.S1",
    "Pivot.M.Classic.R1", "Pivot.M.Classic.R2", "price_earnings_ttm",
    "price_book_fq", "dividends_yield_current", "return_on_equity",
    "net_margin_ttm", "debt_to_equity", "total_debt", "total_assets",
]

SAFE_COLS = [
    "name", "description", "sector", "industry", "close", "open", "high", "low",
    "change", "volume", "average_volume_10d_calc", "relative_volume_10d_calc",
    "market_cap_basic", "RSI", "RSI[1]", "Stoch.K", "Stoch.D", "MACD.macd",
    "MACD.signal", "EMA10", "EMA20", "EMA50", "EMA200", "SMA20", "SMA50", "SMA200",
    "ADX", "ADX+DI", "ADX-DI", "BB.upper", "BB.lower", "ATR", "VWMA",
    "Recommend.All", "Perf.W", "Perf.1M", "price_52_week_high", "price_52_week_low",
    "Pivot.M.Classic.S1", "Pivot.M.Classic.R1", "Pivot.M.Classic.R2",
    "price_earnings_ttm", "price_book_fq",
]


def load_issi_set():
    s = set(DEFAULT_ISSI)
    for path in (ISSI_TMP_FILE, ISSI_REPO_FILE):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tokens = [t.strip().upper().replace("IDX:", "") for t in f.read().replace(",", "\n").splitlines()]
                custom = {t for t in tokens if 3 <= len(t) <= 5 and t.isalpha()}
                if custom:
                    return custom
            except Exception:
                pass
    return s


def round_fraksi_bei(price):
    if price is None or price <= 0:
        return 0
    tick = 1 if price < 200 else (2 if price < 500 else (5 if price < 2000 else (10 if price < 5000 else 25)))
    return int(round(price / tick) * tick)


def floor_fraksi_bei(price):
    if price is None or price <= 0:
        return 0
    tick = 1 if price < 200 else (2 if price < 500 else (5 if price < 2000 else (10 if price < 5000 else 25)))
    return max(50, int(math.floor(price / tick) * tick))


def safe_num(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def post_tv_scanner(columns):
    payload = {
        "filter": [
            {"left": "exchange", "operation": "equal", "right": "IDX"},
            {"left": "close", "operation": "greater", "right": 50},
            {"left": "volume", "operation": "greater", "right": 0},
        ],
        "options": {"lang": "en"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": columns,
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [0, 950],
    }
    req = urllib.request.Request(
        "https://scanner.tradingview.com/indonesia/scan",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def analyze_stock(row_dict, issi_set):
    ticker = (row_dict.get("name") or "").upper()
    close = safe_num(row_dict.get("close"), 0)
    if not ticker or close <= 0:
        return None

    open_p = safe_num(row_dict.get("open"), close)
    high_p = safe_num(row_dict.get("high"), close)
    low_p = safe_num(row_dict.get("low"), close)
    change = safe_num(row_dict.get("change"), 0)
    volume = safe_num(row_dict.get("volume"), 0)
    avg_vol = safe_num(row_dict.get("average_volume_10d_calc"), 0)
    rvol = safe_num(row_dict.get("relative_volume_10d_calc"))
    if rvol is None and avg_vol and avg_vol > 0:
        rvol = volume / avg_vol
    rvol = rvol or 1.0

    val_traded = close * volume
    mcap = safe_num(row_dict.get("market_cap_basic"), 0)

    rsi = safe_num(row_dict.get("RSI"), 50)
    rsi_prev = safe_num(row_dict.get("RSI[1]"), rsi)
    stoch_k = safe_num(row_dict.get("Stoch.K"), 50)
    stoch_d = safe_num(row_dict.get("Stoch.D"), 50)
    macd = safe_num(row_dict.get("MACD.macd"), 0)
    macd_sig = safe_num(row_dict.get("MACD.signal"), 0)
    macd_hist = macd - macd_sig

    ema10 = safe_num(row_dict.get("EMA10"), close)
    ema20 = safe_num(row_dict.get("EMA20"), close)
    ema50 = safe_num(row_dict.get("EMA50"), close)
    ema200 = safe_num(row_dict.get("EMA200"), ema50)
    sma20 = safe_num(row_dict.get("SMA20"), ema20)
    vwap = safe_num(row_dict.get("VWAP"), (high_p + low_p + close) / 3)
    vwma = safe_num(row_dict.get("VWMA"), sma20)

    adx = safe_num(row_dict.get("ADX"), 15)
    di_plus = safe_num(row_dict.get("ADX+DI"), 20)
    di_minus = safe_num(row_dict.get("ADX-DI"), 20)

    bb_up = safe_num(row_dict.get("BB.upper"), close * 1.05)
    bb_low = safe_num(row_dict.get("BB.lower"), close * 0.95)
    bbw = (bb_up - bb_low) / sma20 if sma20 > 0 else 0.15

    atr = safe_num(row_dict.get("ATR"))
    if not atr or atr <= 0:
        atr = max(close * 0.025, high_p - low_p)

    high_52w = safe_num(row_dict.get("price_52_week_high"), close)
    low_52w = safe_num(row_dict.get("price_52_week_low"), close)
    piv_s1 = safe_num(row_dict.get("Pivot.M.Classic.S1"), close * 0.95)
    piv_r1 = safe_num(row_dict.get("Pivot.M.Classic.R1"), close * 1.06)
    piv_r2 = safe_num(row_dict.get("Pivot.M.Classic.R2"), close * 1.12)

    pe = safe_num(row_dict.get("price_earnings_ttm"))
    pbv = safe_num(row_dict.get("price_book_fq"))
    roe = safe_num(row_dict.get("return_on_equity"))
    npm = safe_num(row_dict.get("net_margin_ttm"))
    div_yield = safe_num(row_dict.get("dividends_yield_current"), 0)
    tot_debt = safe_num(row_dict.get("total_debt"))
    tot_assets = safe_num(row_dict.get("total_assets"))
    tv_rec = safe_num(row_dict.get("Recommend.All"), 0)
    perf_w = safe_num(row_dict.get("Perf.W"), 0)
    perf_1m = safe_num(row_dict.get("Perf.1M"), 0)

    sector = row_dict.get("sector") or "-"
    industry = row_dict.get("industry") or "-"
    desc = row_dict.get("description") or ticker

    debt_asset_ratio = round((tot_debt / tot_assets) * 100, 1) if (tot_debt is not None and tot_assets and tot_assets > 0) else None
    ind_lower = (industry + " " + sector).lower()
    is_haram = any(k in ind_lower for k in NON_SYARIAH_KEYWORDS) or ("bank" in ind_lower and ticker not in {"BRIS", "BTPS", "PNBS", "BANK"})
    in_issi_list = ticker in issi_set
    is_issi = in_issi_list and (ticker not in NON_SYARIAH_TICKERS) and (not is_haram) and (True if debt_asset_ratio is None else debt_asset_ratio <= 45.0)

    smart_score = 0
    tags = []
    if rvol >= 2.0 and close >= open_p:
        smart_score += 12
        tags.append("Volume Spike Institusi")
    elif rvol >= 1.35 and close >= open_p:
        smart_score += 8
        tags.append("Akumulasi Volume")
    elif rvol >= 1.5 and change > -1.5 and close > (low_p + (high_p - low_p) * 0.55):
        smart_score += 7
        tags.append("Absorption")
    if close > vwap:
        smart_score += 6
    if vwma > sma20:
        smart_score += 6
        tags.append("VWMA Bullish")
    if val_traded >= 5_000_000_000:
        smart_score += 4

    trend_score = 0
    if close > ema20:
        trend_score += 6
    if ema20 > ema50:
        trend_score += 6
    if ema50 > ema200:
        trend_score += 6
    if close > ema20 > ema50 > ema200:
        tags.append("Stage-2 Golden Trend")
    if adx >= 22 and di_plus > di_minus:
        trend_score += 5
    if high_52w > 0 and close >= high_52w * 0.78:
        trend_score += 4

    mom_score = 0
    is_squeeze = bbw <= 0.12
    is_breakout = close > ema20 and rvol >= 1.3 and change > 1.2 and (is_squeeze or close >= bb_up * 0.985)
    is_rebound = (26 <= rsi <= 43) and (rsi > rsi_prev) and (stoch_k > stoch_d) and (close >= open_p)
    if is_breakout:
        mom_score += 10
        tags.append("Squeeze Breakout" if is_squeeze else "Breakout")
    elif is_rebound:
        mom_score += 9
        tags.append("Oversold Rebound")
    if 50 <= rsi <= 68:
        mom_score += 7
    elif 43 <= rsi < 50 and rsi > rsi_prev:
        mom_score += 5
    elif rsi > 76:
        mom_score -= 6
    if macd > macd_sig and macd_hist > 0:
        mom_score += 6
    elif macd > macd_sig:
        mom_score += 4
    if stoch_k > stoch_d and stoch_k < 80:
        mom_score += 2

    fund_score = 0
    if pe is not None and 0 < pe <= 15:
        fund_score += 7
        tags.append("PER Murah")
    elif pe is not None and 15 < pe <= 24:
        fund_score += 4
    if pbv is not None and 0 < pbv <= 1.8:
        fund_score += 4
    elif pbv is not None and 1.8 < pbv <= 3.0:
        fund_score += 2
    if roe is not None and roe >= 12:
        fund_score += 5
        tags.append("ROE Tinggi")
    elif roe is not None and roe >= 6:
        fund_score += 3
    if npm is not None and npm >= 8:
        fund_score += 2
    if div_yield >= 3:
        fund_score += 2

    if tv_rec >= 0.4:
        smart_score += 2
    elif tv_rec <= -0.4:
        trend_score = max(0, trend_score - 5)

    alpha_score = max(0, min(100, round(smart_score + trend_score + mom_score + fund_score)))

    risk_unit = max(atr * 1.45, close * 0.03)
    if is_rebound:
        entry_low = floor_fraksi_bei(close * 0.985)
        entry_high = round_fraksi_bei(close * 1.005)
        sl_raw = min(low_p * 0.98, close - risk_unit)
    elif is_breakout:
        entry_low = floor_fraksi_bei(max(ema20 * 0.99, close * 0.985))
        entry_high = round_fraksi_bei(close * 1.01)
        sl_raw = max(ema20 * 0.97, close - risk_unit)
    else:
        base_sup = min(ema20, vwap) if ema20 > 0 else close * 0.97
        entry_low = floor_fraksi_bei(max(base_sup, close * 0.97))
        entry_high = round_fraksi_bei(close)
        sl_raw = min(piv_s1, close - risk_unit)

    stop_loss = floor_fraksi_bei(min(sl_raw, entry_low * 0.96))
    if stop_loss >= entry_low:
        stop_loss = floor_fraksi_bei(entry_low * 0.94)

    risk_per_share = max(1, entry_high - stop_loss)
    tp1_calc = entry_high + (risk_per_share * 2.0)
    tp2_calc = entry_high + (risk_per_share * 3.5)

    tp1 = round_fraksi_bei(max(tp1_calc, piv_r1 if piv_r1 > entry_high * 1.03 else tp1_calc))
    tp2 = round_fraksi_bei(max(tp2_calc, piv_r2 if piv_r2 > tp1 * 1.03 else tp2_calc))
    rr_ratio = round((tp1 - entry_high) / risk_per_share, 2)

    if rsi >= 76 and change > 4:
        signal, signal_code = "TAKE PROFIT / SELL", "SELL"
        action_note = f"RSI Overbought ekstrem ({rsi:.1f}). Amankan profit bertahap atau Trailing Stop di EMA10 (Rp {round_fraksi_bei(ema10):,})."
    elif alpha_score >= 76 and close > ema20 and rsi < 74:
        signal, signal_code = "STRONG BUY", "STRONG_BUY"
        action_note = f"Konfluensi kuat: Skor {alpha_score}/100, aliran dana & tren Stage-2 sejalan. Akumulasi di Rp {entry_low:,}–{entry_high:,}."
    elif is_breakout and alpha_score >= 62:
        signal, signal_code = "BUY BREAKOUT", "BUY_BREAKOUT"
        action_note = f"Breakout terkonfirmasi RVOL {rvol:.2f}x. Entry di atas Rp {entry_low:,} dengan disiplin SL Rp {stop_loss:,}."
    elif is_rebound and alpha_score >= 54:
        signal, signal_code = "BUY ON WEAKNESS", "BOW"
        action_note = f"Pantulan awal dari jenuh jual (RSI {rsi:.1f}). Speculative buy dekat support menuju TP1 Rp {tp1:,}."
    elif close < ema50 and ema20 < ema50 and tv_rec < -0.15:
        signal, signal_code = "SELL / AVOID", "AVOID"
        action_note = f"Struktur masih downtrend di bawah EMA50 (Rp {round_fraksi_bei(ema50):,}). Hindari dulu atau jual saat rebound."
    elif alpha_score >= 58:
        signal, signal_code = "ACCUMULATE / WATCH", "WATCH"
        action_note = f"Struktur cukup baik (Skor {alpha_score}). Antre dekat support Rp {entry_low:,}."
    else:
        signal, signal_code = "HOLD / NEUTRAL", "NEUTRAL"
        action_note = "Momentum belum konvergen. Tunggu harga menembus EMA20 dengan volume di atas rata-rata."

    return {
        "ticker": ticker,
        "name": desc,
        "sector": sector,
        "industry": industry,
        "is_issi": is_issi,
        "in_issi_list": in_issi_list,
        "debt_asset_ratio": debt_asset_ratio,
        "close": round(close, 0),
        "change": round(change, 2),
        "volume": int(volume),
        "value_traded_b": round(val_traded / 1e9, 2),
        "mcap_t": round(mcap / 1e12, 2) if mcap else 0,
        "rvol": round(rvol, 2),
        "rsi": round(rsi, 1),
        "adx": round(adx, 1),
        "bbw": round(bbw * 100, 1),
        "ema10": round_fraksi_bei(ema10),
        "ema20": round_fraksi_bei(ema20),
        "ema50": round_fraksi_bei(ema50),
        "ema200": round_fraksi_bei(ema200),
        "vwap": round_fraksi_bei(vwap),
        "vwma_bull": vwma > sma20,
        "macd_bull": macd > macd_sig,
        "pe": round(pe, 1) if pe is not None else None,
        "pbv": round(pbv, 2) if pbv is not None else None,
        "roe": round(roe, 1) if roe is not None else None,
        "npm": round(npm, 1) if npm is not None else None,
        "div_yield": round(div_yield, 2),
        "perf_w": round(perf_w, 2),
        "perf_1m": round(perf_1m, 2),
        "high_52w": round_fraksi_bei(high_52w),
        "low_52w": round_fraksi_bei(low_52w),
        "tv_rec": round(tv_rec, 2),
        "alpha_score": alpha_score,
        "pillars": {
            "smart_money": round(smart_score),
            "trend": round(trend_score),
            "momentum": round(mom_score),
            "fundamental": round(fund_score),
        },
        "signal": signal,
        "signal_code": signal_code,
        "is_breakout": is_breakout,
        "is_rebound": is_rebound,
        "is_squeeze": is_squeeze,
        "tags": tags[:4],
        "plan": {
            "entry_low": entry_low,
            "entry_high": entry_high,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "rr": rr_ratio,
            "sl_pct": round(((stop_loss - entry_high) / entry_high) * 100, 1),
            "tp1_pct": round(((tp1 - entry_high) / entry_high) * 100, 1),
            "tp2_pct": round(((tp2 - entry_high) / entry_high) * 100, 1),
            "note": action_note,
        },
    }


def get_market_data(force=False):
    now = time.time()
    if not force and _cache["data"] is not None and (now - _cache["timestamp"] < CACHE_TTL):
        return _cache["data"]

    cols_used = FULL_COLS
    try:
        raw = post_tv_scanner(FULL_COLS)
    except urllib.error.HTTPError:
        cols_used = SAFE_COLS
        raw = post_tv_scanner(SAFE_COLS)

    issi_set = load_issi_set()
    results = []
    for item in raw.get("data", []):
        row_dict = dict(zip(cols_used, item.get("d", [])))
        analyzed = analyze_stock(row_dict, issi_set)
        if analyzed:
            results.append(analyzed)

    results.sort(key=lambda x: (x["alpha_score"], x["value_traded_b"]), reverse=True)
    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S WIB", time.gmtime(now + 7 * 3600)),
        "total_scanned": len(results),
        "total_issi": sum(1 for r in results if r["is_issi"]),
        "strong_buy_count": sum(1 for r in results if r["signal_code"] in ("STRONG_BUY", "BUY_BREAKOUT")),
        "source": "TradingView Live Scanner (IDX)",
        "stocks": results,
    }
    _cache["timestamp"] = now
    _cache["data"] = payload
    return payload


def build_quant_ai_report(s, all_stocks, question=""):
    peers = [x for x in all_stocks if x["sector"] == s["sector"] and x["value_traded_b"] >= 0.5]
    if not peers:
        peers = [s]
    peers_sorted = sorted(peers, key=lambda x: (x["alpha_score"], x["value_traded_b"]), reverse=True)
    rank = next((i + 1 for i, x in enumerate(peers_sorted) if x["ticker"] == s["ticker"]), 1)
    avg_sector_score = round(sum(x["alpha_score"] for x in peers) / len(peers), 1)
    avg_sector_chg = round(sum(x["change"] for x in peers) / len(peers), 2)
    top_peers = [
        {
            "ticker": x["ticker"],
            "close": x["close"],
            "change": x["change"],
            "alpha_score": x["alpha_score"],
            "signal": x["signal"],
            "pe": x["pe"],
            "roe": x["roe"],
        }
        for x in peers_sorted if x["ticker"] != s["ticker"]
    ][:3]

    c, e20, e50, e200 = s["close"], s["ema20"], s["ema50"], s["ema200"]
    # 1. Weinstein / Wyckoff Stage
    if c > e20 > e50 > e200:
        if s["rsi"] >= 74:
            stage = "Stage 3 • Overextended / Rawan Profit Taking"
            stage_desc = f"Harga sudah jauh di atas EMA20 (Rp {e20:,}) dengan RSI {s['rsi']}. Tren masih naik, tetapi rawan koreksi sehat jangka pendek."
        else:
            stage = "Stage 2 • Markup / Uptrend Institusi"
            stage_desc = f"Formasi sempurna: Harga (Rp {c:,}) > EMA20 ({e20:,}) > EMA50 ({e50:,}) > EMA200 ({e200:,}). Ini zona terbaik untuk mengikuti tren naik."
    elif c > e20 and e20 <= e50:
        stage = "Stage 1 → 2 • Transisi Akumulasi ke Breakout"
        stage_desc = f"Harga mulai menembus EMA20 (Rp {e20:,}) dan bersiap membalikkan tren menengah (EMA50 Rp {e50:,})."
    elif c < e50 and e20 < e50:
        if s["is_rebound"]:
            stage = "Stage 4 (Akhir) • Technical Rebound dari Jenuh Jual"
            stage_desc = f"Tren utama masih di bawah EMA50 (Rp {e50:,}), namun muncul pantulan awal dari area oversold (RSI {s['rsi']}). Cocok untuk swing cepat, bukan hold pasif."
        else:
            stage = "Stage 4 • Markdown / Downtrend"
            stage_desc = f"Harga berada di bawah EMA20 ({e20:,}) dan EMA50 ({e50:,}). Risiko tekanan jual masih dominan; tunggu base baru terbentuk."
    else:
        stage = "Stage 1 • Konsolidasi / Sideways Base"
        stage_desc = f"Harga bergerak mendatar di sekitar rata-rata EMA20–EMA50 (BB Width {s['bbw']}%). Menunggu katalis volume untuk menentukan arah."

    # 2. Order Flow & Smart Money
    vwap_diff = round(((c - s["vwap"]) / s["vwap"]) * 100, 2) if s["vwap"] else 0
    if s["rvol"] >= 1.8 and c >= s["vwap"]:
        flow = f"Akumulasi Agresif: Volume melonjak {s['rvol']}x rata-rata 10 hari dengan harga bertahan +{vwap_diff}% di atas VWAP (Rp {s['vwap']:,}). Indikasi masuknya dana besar."
    elif s["vwma_bull"] and c >= s["vwap"]:
        flow = f"Aliran Dana Positif: VWMA lebih kuat dari SMA20 dan harga di atas VWAP (Rp {s['vwap']:,}), menandakan pembeli lebih dominan daripada penjual."
    elif s["rvol"] >= 1.5 and s["change"] < -1.5:
        flow = f"Distribusi / Tekanan Jual: Volume tinggi ({s['rvol']}x) disertai penurunan {s['change']}%. Waspadai lanjutan pelemahan."
    else:
        flow = f"Volume Normal ({s['rvol']}x): Belum ada lonjakan dana institusi yang ekstrem. Posisi harga {vwap_diff:+.2f}% terhadap VWAP (Rp {s['vwap']:,})."

    # 3. Fundamental & Syariah Audit
    pe_txt = f"PER {s['pe']}x" if s["pe"] is not None else "PER negatif/N/A"
    pbv_txt = f"PBV {s['pbv']}x" if s["pbv"] is not None else "PBV N/A"
    roe_txt = f"ROE {s['roe']}%" if s["roe"] is not None else "ROE N/A"
    da_txt = f"Utang/Aset {s['debt_asset_ratio']}%" if s["debt_asset_ratio"] is not None else "Utang/Aset N/A"
    syariah_status = "LOLOS SYARIAH ISSI" if s["is_issi"] else "NON-ISSI / PERLU CEK DES"
    fund_audit = (
        f"Status: {syariah_status} ({da_txt} vs batas OJK 45%). Valuasi saat ini {pe_txt}, {pbv_txt}, profitabilitas {roe_txt}, "
        f"dengan Dividend Yield {s['div_yield']}%. "
        + ("Valuasi tergolong menarik untuk fundamental jangka menengah." if (s["pe"] and 0 < s["pe"] <= 15 and (s["roe"] or 0) >= 10) else "Kinerja fundamental bersifat netral/siklikal, utamakan disiplin teknikal.")
    )

    # 4. Risk Flags & Horizon
    risks = []
    if s["value_traded_b"] < 1.0:
        risks.append(f"Likuiditas tipis (Rp {s['value_traded_b']} M/hari) — rawan spread lebar & sulit keluar saat panik.")
    if s["rsi"] >= 74:
        risks.append(f"RSI Overbought ({s['rsi']}) — jangan kejar harga di pucuk, tunggu pullback ke EMA10/EMA20.")
    if c < e50:
        risks.append(f"Masih di bawah EMA50 (Rp {e50:,}) — tren menengah belum aman sepenuhnya.")
    if s["plan"]["rr"] < 1.5:
        risks.append(f"Risk:Reward hanya 1:{s['plan']['rr']} — ruang profit terbatas dibanding risiko SL.")
    if not risks:
        risks.append("Risiko teknikal & likuiditas relatif terkendali selama disiplin menjaga Stop Loss.")

    if s["alpha_score"] >= 75 and c > e50:
        horizon = "Swing Trading (1–4 Minggu) / Trend Following"
    elif s["is_breakout"] or s["rvol"] >= 1.8:
        horizon = "Day Trade / Fast Swing (2–7 Hari)"
    elif s["pe"] is not None and 0 < s["pe"] <= 14 and (s["roe"] or 0) >= 12:
        horizon = "Position / Value Investing (1–6 Bulan)"
    else:
        horizon = "Wait & See / Pantau Support"

    p = s["plan"]
    scenarios = {
        "bullish": f"Jika menembus & bertahan di atas Rp {p['entry_high']:,} dengan RVOL ≥ 1.3x, target kenaikan bertahap menuju TP1 Rp {p['tp1']:,} (+{p['tp1_pct']}%) hingga TP2 Rp {p['tp2']:,} (+{p['tp2_pct']}%).",
        "base": f"Jika terjadi konsolidasi sehat, area antre terbaik ada di Rp {p['entry_low']:,}–{p['entry_high']:,} (dekat VWAP/EMA20) agar Risk:Reward tetap 1:{p['rr']}.",
        "bearish": f"Skenario batal jika harga jebol di bawah Stop Loss Rp {p['stop_loss']:,} ({p['sl_pct']}%) disertai volume jual besar. Wajib Cut Loss disiplin untuk lindungi modal.",
    }

    # 5. Built-in Q&A Engine
    q = (question or "").strip().lower()
    if not q:
        qa_answer = f"Kesimpulan AI untuk {s['ticker']}: {s['signal']} (Skor α {s['alpha_score']}/100, Peringkat #{rank} dari {len(peers)} saham di sektor {s['sector']}). {p['note']}"
    elif "hold" in q or "jangka" in q or "menengah" in q or "lama" in q:
        qa_answer = (
            f"Untuk hold jangka menengah pada {s['ticker']}: Posisi saat ini berada di '{stage}'. "
            + (f"Struktur Stage-2 dan fundamental ({pe_txt}, {roe_txt}) mendukung untuk di-hold selama harga tidak turun menembus EMA50 (Rp {e50:,})."
               if (c > e50 and (s["roe"] or 0) >= 8)
               else f"Saat ini kurang ideal untuk hold pasif jangka panjang karena tren masih di bawah/baru menguji EMA50 (Rp {e50:,}). Lebih aman trading bertahap dengan Trailing Stop.")
        )
    elif "cut loss" in q or "average" in q or "cicil" in q or "entry" in q or "beli" in q:
        qa_answer = (
            f"Strategi Entry & Cut Loss {s['ticker']}: Jangan All-in sekaligus. Cicil 50% di area Rp {p['entry_low']:,}–{p['entry_high']:,}, dan sisa 50% hanya jika harga memantul kuat atau breakout. "
            f"Hindari Average Down jika harga sudah menembus Stop Loss Rp {p['stop_loss']:,} ({p['sl_pct']}%). Pasang Trailing Stop di EMA10 (Rp {s['ema10']:,}) setelah profit di atas +5%."
        )
    elif "sektor" in q or "kompetitor" in q or "banding" in q:
        peers_txt = ", ".join([f"{x['ticker']} (Skor {x['alpha_score']}, {x['change']:+.2f}%)" for x in top_peers]) or "tidak ada pembanding likuid"
        qa_answer = (
            f"Di sektor {s['sector']}, {s['ticker']} menempati peringkat #{rank} dari {len(peers)} emiten dengan Skor α {s['alpha_score']} "
            f"(rata-rata sektor: {avg_sector_score}, rata-rata perubahan hari ini: {avg_sector_chg:+.2f}%). "
            f"Kompetitor teratas di sektor yang sama: {peers_txt}."
        )
    elif "bandar" in q or "trap" in q or "risiko" in q or "jebakan" in q:
        qa_answer = f"Analisa Jebakan / Risiko {s['ticker']}: {flow} Peringatan utama: {' '.join(risks)}"
    else:
        qa_answer = (
            f"Analisa {s['ticker']} (Skor {s['alpha_score']}/100 • {s['signal']}): {stage_desc} "
            f"{flow} Rencana eksekusi: Beli Rp {p['entry_low']:,}–{p['entry_high']:,}, SL Rp {p['stop_loss']:,}, TP1 Rp {p['tp1']:,}."
        )

    return {
        "ticker": s["ticker"],
        "conviction": min(98, max(20, round(s["alpha_score"] * 0.85 + (10 if s["value_traded_b"] >= 5 else 0) + (5 if s["plan"]["rr"] >= 2 else 0)))),
        "horizon": horizon,
        "stage": stage,
        "stage_desc": stage_desc,
        "order_flow": flow,
        "fund_audit": fund_audit,
        "risk_flags": risks,
        "scenarios": scenarios,
        "sector_context": {
            "sector": s["sector"],
            "rank": rank,
            "total_peers": len(peers),
            "avg_score": avg_sector_score,
            "avg_change": avg_sector_chg,
            "top_peers": top_peers,
        },
        "qa_answer": qa_answer,
        "llm_used": False,
        "llm_error": "",
    }


def call_gemini_ai(s, quant_report, question, api_key):
    ctx = quant_report["sector_context"]
    prompt = (
        f"Kamu adalah analis riset ekuitas institusional pasar saham Indonesia (BEI/IDX) yang sangat tajam, objektif, dan berfokus pada manajemen risiko.\n"
        f"Data LIVE TradingView untuk IDX:{s['ticker']} ({s['name']}):\n"
        f"- Sektor: {s['sector']} (Peringkat #{ctx['rank']} dari {ctx['total_peers']} saham, rata-rata skor sektor {ctx['avg_score']})\n"
        f"- Harga: Rp {s['close']:,} ({s['change']:+.2f}%), Transaksi: Rp {s['value_traded_b']} Miliar, RVOL: {s['rvol']}x\n"
        f"- Teknikal: Skor Alpha {s['alpha_score']}/100, Sinyal {s['signal']}, Stage: {quant_report['stage']}, RSI {s['rsi']}, ADX {s['adx']}, VWAP Rp {s['vwap']:,}, EMA20 Rp {s['ema20']:,}, EMA50 Rp {s['ema50']:,}, EMA200 Rp {s['ema200']:,}\n"
        f"- Fundamental & Syariah: ISSI={s['is_issi']}, Utang/Aset={s['debt_asset_ratio']}%, PER={s['pe']}x, PBV={s['pbv']}x, ROE={s['roe']}%, DivYield={s['div_yield']}%\n"
        f"- Rencana Kuantitatif: Entry Rp {s['plan']['entry_low']:,}-{s['plan']['entry_high']:,}, Cut Loss Rp {s['plan']['stop_loss']:,} ({s['plan']['sl_pct']}%), TP1 Rp {s['plan']['tp1']:,}, TP2 Rp {s['plan']['tp2']:,}, R:R 1:{s['plan']['rr']}\n"
        f"- Top Kompetitor Sektor: {json.dumps(ctx['top_peers'])}\n\n"
        f"Pertanyaan/Permintaan User: {question or 'Berikan analisa mendalam prospek, kekuatan bandar/order flow, valuasi, risiko tersembunyi, dan strategi eksekusi terbaik untuk saham ini.'}\n\n"
        f"Jawab dalam Bahasa Indonesia yang ringkas, terstruktur (pakai poin jelas), langsung ke angka konkret, dan ingatkan risiko secara objektif."
    )
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 900},
    }).encode("utf-8")

    last_err = ""
    for model in ("gemini-3.5-flash-lite", "gemini-3.5-flash"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key.strip()},
        )
        try:
            with urllib.request.urlopen(req, timeout=18) as resp:
                res = json.loads(resp.read().decode("utf-8"))
            text = res["candidates"][0]["content"]["parts"][0]["text"]
            return text, model, ""
        except Exception as e:
            last_err = str(e)
    return None, "", last_err


@app.get("/", response_class=HTMLResponse)
def home():
    html_path = os.path.join(BASE_DIR, "react_ui.html")
    if not os.path.exists(html_path):
        return HTMLResponse("<h3>File react_ui.html tidak ditemukan di repository.</h3>", status_code=500)
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/scan")
def scan(force: int = 0):
    try:
        return get_market_data(force=(force == 1))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/ai-analyze")
async def ai_analyze(request: Request):
    try:
        body = await request.json()
        ticker = (body.get("ticker") or "").upper().strip()
        question = body.get("question") or ""
        user_key = (body.get("api_key") or "").strip()
        api_key = user_key or os.environ.get("GEMINI_API_KEY", "").strip()

        market = get_market_data(force=False)
        stocks = market["stocks"]
        s = next((x for x in stocks if x["ticker"] == ticker), None)
        if not s:
            return JSONResponse({"error": f"Saham {ticker} tidak ditemukan."}, status_code=404)

        report = build_quant_ai_report(s, stocks, question)
        if api_key:
            llm_text, model_used, llm_err = call_gemini_ai(s, report, question, api_key)
            if llm_text:
                report["qa_answer"] = llm_text
                report["llm_used"] = True
                report["llm_model"] = model_used
            else:
                report["llm_error"] = f"Gemini fallback ke Quant AI ({llm_err})"
        return report
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/issi")
def get_issi():
    return {"tickers": sorted(load_issi_set())}


@app.post("/api/issi")
async def save_issi(request: Request):
    body = await request.json()
    raw_text = body.get("text", "")
    tokens = [t.strip().upper().replace("IDX:", "") for t in raw_text.replace(",", "\n").splitlines()]
    valid = sorted({t for t in tokens if 3 <= len(t) <= 5 and t.isalpha()})
    if not valid:
        return JSONResponse({"error": "Tidak ada kode saham valid."}, status_code=400)
    try:
        with open(ISSI_REPO_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(valid))
    except Exception:
        with open(ISSI_TMP_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(valid))
    _cache["data"] = None
    return {"saved": len(valid)}
