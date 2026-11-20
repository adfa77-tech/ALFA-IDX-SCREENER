import json
import math
import os
import time
import urllib.request
import urllib.error
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

PORT = 8000
CACHE_TTL = 25  # Cache 25 detik agar cepat & aman dari rate-limit TradingView
_cache = {"timestamp": 0, "data": None}

# Daftar Core ISSI / JII / JII70 (Dapat ditambah via file issi_list.txt atau langsung dari UI)
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
    "VKTR", "VOKS", "WEGE", "WEHA", "WIFI", "WIKA", "WOOD", "WTON", "ZINC", "ZONE"
}

# Saham/sektor non-syariah eksplisit (agar tidak lolos meski Debt/Asset rendah)
NON_SYARIAH_TICKERS = {
    "BBCA", "BBRI", "BMRI", "BBNI", "BBTN", "BDMN", "BNGA", "BNLI", "MEGA", "NISP",
    "PNBN", "BBKP", "BJBR", "BJTM", "BTPN", "BNII", "MAYA", "AGRO", "BBYB", "AMAR",
    "GGRM", "HMSP", "WIIM", "RMBA", "ITIC", "MLBI", "DLTA", "ADMF", "BFIN", "CFIN",
    "PNLF", "PNIN", "ASRM", "LPGI", "TUGU", "MREI", "TRIM", "PANS"
}

NON_SYARIAH_KEYWORDS = ("tobacco", "brewer", "distiller", "casino", "gambling", "insurance", "consumer finance")

ISSI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "issi_list.txt")


def load_issi_set():
    s = set(DEFAULT_ISSI)
    if os.path.exists(ISSI_FILE):
        try:
            with open(ISSI_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            tokens = [t.strip().upper().replace("IDX:", "") for t in content.replace(",", "\n").splitlines()]
            custom = {t for t in tokens if 3 <= len(t) <= 5 and t.isalpha()}
            if custom:
                s = custom  # Gunakan daftar resmi user jika diisi
        except Exception:
            pass
    return s


def round_fraksi_bei(price):
    if price is None or price <= 0:
        return 0
    if price < 200:
        tick = 1
    elif price < 500:
        tick = 2
    elif price < 2000:
        tick = 5
    elif price < 5000:
        tick = 10
    else:
        tick = 25
    return int(round(price / tick) * tick)


def floor_fraksi_bei(price):
    if price is None or price <= 0:
        return 0
    if price < 200:
        tick = 1
    elif price < 500:
        tick = 2
    elif price < 2000:
        tick = 5
    elif price < 5000:
        tick = 10
    else:
        tick = 25
    return max(50, int(math.floor(price / tick) * tick))


def safe_num(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


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
    "net_margin_ttm", "debt_to_equity", "total_debt", "total_assets"
]

SAFE_COLS = [
    "name", "description", "sector", "industry", "close", "open", "high", "low",
    "change", "volume", "average_volume_10d_calc", "relative_volume_10d_calc",
    "market_cap_basic", "RSI", "RSI[1]", "Stoch.K", "Stoch.D", "MACD.macd",
    "MACD.signal", "EMA10", "EMA20", "EMA50", "EMA200", "SMA20", "SMA50", "SMA200",
    "ADX", "ADX+DI", "ADX-DI", "BB.upper", "BB.lower", "ATR", "VWMA",
    "Recommend.All", "Perf.W", "Perf.1M", "price_52_week_high", "price_52_week_low",
    "Pivot.M.Classic.S1", "Pivot.M.Classic.R1", "Pivot.M.Classic.R2",
    "price_earnings_ttm", "price_book_fq"
]


def post_tv_scanner(columns):
    payload = {
        "filter": [
            {"left": "exchange", "operation": "equal", "right": "IDX"},
            {"left": "close", "operation": "greater", "right": 50},
            {"left": "volume", "operation": "greater", "right": 0}
        ],
        "options": {"lang": "en"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": columns,
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [0, 950]
    }
    req = urllib.request.Request(
        "https://scanner.tradingview.com/indonesia/scan",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Origin": "https://www.tradingview.com",
            "Referer": "https://www.tradingview.com/"
        }
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

    val_traded = close * volume  # Rupiah
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

    # --- 1. KLASIFIKASI SYARIAH (ISSI + OJK RATIO GUARD) ---
    debt_asset_ratio = None
    if tot_debt is not None and tot_assets and tot_assets > 0:
        debt_asset_ratio = round((tot_debt / tot_assets) * 100, 1)

    ind_lower = (industry + " " + sector).lower()
    is_haram_sector = any(k in ind_lower for k in NON_SYARIAH_KEYWORDS) or (
        "bank" in ind_lower and ticker not in {"BRIS", "BTPS", "PNBS", "BANK"}
    )
    in_issi_list = ticker in issi_set
    is_non_syariah = ticker in NON_SYARIAH_TICKERS or is_haram_sector
    ratio_ok = True if debt_asset_ratio is None else (debt_asset_ratio <= 45.0)
    is_issi = (in_issi_list and not is_non_syariah and ratio_ok)

    # --- 2. PILAR SMART MONEY & BANDAR (Max 28 pts) ---
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
        tags.append("Absorption / Tampung Bawah")

    if close > vwap:
        smart_score += 6
    if vwma > sma20:
        smart_score += 6
        tags.append("VWMA Bullish Flow")
    if val_traded >= 5_000_000_000:
        smart_score += 4

    # --- 3. PILAR TREND POWER / MINERVINI SEPA (Max 27 pts) ---
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

    # --- 4. PILAR MOMENTUM & SQUEEZE SNIPER (Max 25 pts) ---
    mom_score = 0
    is_squeeze = bbw <= 0.12
    is_breakout = (close > ema20 and rvol >= 1.3 and change > 1.2 and (is_squeeze or close >= bb_up * 0.985))
    is_rebound = (26 <= rsi <= 43 and rsi > rsi_prev and stoch_k > stoch_d and close >= open_p)

    if is_breakout:
        mom_score += 10
        tags.append("Squeeze Breakout" if is_squeeze else "Momentum Breakout")
    elif is_rebound:
        mom_score += 9
        tags.append("Oversold Sniper Rebound")

    if 50 <= rsi <= 68:
        mom_score += 7
    elif 43 <= rsi < 50 and rsi > rsi_prev:
        mom_score += 5
    elif rsi > 76:
        mom_score -= 6  # Penalti rawan profit taking

    if macd > macd_sig and macd_hist > 0:
        mom_score += 6
    elif macd > macd_sig:
        mom_score += 4

    if stoch_k > stoch_d and stoch_k < 80:
        mom_score += 2

    # --- 5. PILAR FUNDAMENTAL GARP (Max 20 pts) ---
    fund_score = 0
    if pe is not None and 0 < pe <= 15:
        fund_score += 7
        tags.append("Valuasi Murah (PER)")
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

    # Konsensus TradingView Bonus/Penalty
    if tv_rec >= 0.4:
        smart_score += 2
    elif tv_rec <= -0.4:
        trend_score = max(0, trend_score - 5)

    alpha_score = max(0, min(100, round(smart_score + trend_score + mom_score + fund_score)))

    # --- 6. EXACT BUY / SELL PLAN (FRAKSI BEI) ---
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

    # Tentukan Sinyal Rekomendasi
    if rsi >= 76 and change > 4:
        signal = "TAKE PROFIT / SELL"
        signal_code = "SELL"
        action_note = f"RSI Overbought ekstrem ({rsi:.1f}). Amankan profit bertahap atau pasang Trailing Stop di EMA10 (Rp {round_fraksi_bei(ema10):,})."
    elif alpha_score >= 76 and close > ema20 and rsi < 74:
        signal = "STRONG BUY"
        signal_code = "STRONG_BUY"
        action_note = f"Konfluensi kuat: Skor {alpha_score}/100, aliran dana & tren Stage-2 sejalan. Akumulasi di area Rp {entry_low:,}–{entry_high:,}."
    elif is_breakout and alpha_score >= 62:
        signal = "BUY BREAKOUT"
        signal_code = "BUY_BREAKOUT"
        action_note = f"Breakout terkonfirmasi RVOL {rvol:.2f}x. Entry jika bertahan di atas Rp {entry_low:,} dengan disiplin SL Rp {stop_loss:,}."
    elif is_rebound and alpha_score >= 54:
        signal = "BUY ON WEAKNESS"
        signal_code = "BOW"
        action_note = f"Pantulan awal dari area jenuh jual (RSI {rsi:.1f}). Speculative buy dekat support dengan target pantulan ke Rp {tp1:,}."
    elif close < ema50 and ema20 < ema50 and tv_rec < -0.15:
        signal = "SELL / AVOID"
        signal_code = "AVOID"
        action_note = f"Struktur masih downtrend di bawah EMA50 (Rp {round_fraksi_bei(ema50):,}). Hindari dulu atau jual saat technical rebound."
    elif alpha_score >= 58:
        signal = "ACCUMULATE / WATCH"
        signal_code = "WATCH"
        action_note = f"Struktur cukup baik (Skor {alpha_score}). Tunggu konfirmasi volume atau antre di support terdekat Rp {entry_low:,}."
    else:
        signal = "HOLD / NEUTRAL"
        signal_code = "NEUTRAL"
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
        "div_yield": round(div_yield, 2),
        "perf_w": round(perf_w, 2),
        "perf_1m": round(perf_1m, 2),
        "tv_rec": round(tv_rec, 2),
        "alpha_score": alpha_score,
        "pillars": {
            "smart_money": round(smart_score),
            "trend": round(trend_score),
            "momentum": round(mom_score),
            "fundamental": round(fund_score)
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
            "note": action_note
        }
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
        vals = item.get("d", [])
        row_dict = dict(zip(cols_used, vals))
        analyzed = analyze_stock(row_dict, issi_set)
        if analyzed:
            results.append(analyzed)

    results.sort(key=lambda x: (x["alpha_score"], x["value_traded_b"]), reverse=True)

    payload = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S WIB"),
        "total_scanned": len(results),
        "total_issi": sum(1 for r in results if r["is_issi"]),
        "strong_buy_count": sum(1 for r in results if r["signal_code"] in ("STRONG_BUY", "BUY_BREAKOUT")),
        "source": "TradingView Live Scanner (IDX)",
        "stocks": results
    }
    _cache["timestamp"] = now
    _cache["data"] = payload
    return payload


class ScreenerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
            if not os.path.exists(html_path):
                self.send_error(404, "index.html tidak ditemukan di folder yang sama.")
                return
            with open(html_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if parsed.path == "/api/scan":
            qs = parse_qs(parsed.query)
            force = qs.get("force", ["0"])[0] == "1"
            try:
                data = get_market_data(force=force)
                self._send_json(data)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if parsed.path == "/api/issi":
            self._send_json({"tickers": sorted(load_issi_set())})
            return

        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/issi":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            try:
                req = json.loads(body)
                raw_text = req.get("text", "")
                tokens = [t.strip().upper().replace("IDX:", "") for t in raw_text.replace(",", "\n").splitlines()]
                valid = sorted({t for t in tokens if 3 <= len(t) <= 5 and t.isalpha()})
                if not valid:
                    self._send_json({"error": "Tidak ada kode saham valid ditemukan."}, status=400)
                    return
                with open(ISSI_FILE, "w", encoding="utf-8") as f:
                    f.write("\n".join(valid))
                _cache["data"] = None  # Reset cache
                self._send_json({"saved": len(valid)})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return
        self.send_error(404)


if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    print(f"====================================================")
    print(f"  IHSG & ISSI Alpha Screener + TradingView Engine   ")
    print(f"  Server aktif di: {url}")
    print(f"  Tekan Ctrl+C untuk berhenti.")
    print(f"====================================================")
    webbrowser.open(url)
    HTTPServer(("0.0.0.0", PORT), ScreenerHandler).serve_forever()