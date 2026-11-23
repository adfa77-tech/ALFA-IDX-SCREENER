import concurrent.futures
import json
import math
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI()

WIB = timezone(timedelta(hours=7))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ISSI_REPO_FILE = os.path.join(BASE_DIR, "issi_list.txt")
ISSI_TMP_FILE = "/tmp/issi_list.txt"

CACHE_TTL = 10
PROFILE_TTL = 300
OHLCV_TTL = 30
NEWS_TTL = 300

_cache = {"timestamp": 0, "data": None}
_profile_cache = {}
_ohlcv_cache = {}
_news_cache = {}
_yf_auth = {"timestamp": 0, "opener": None, "crumb": ""}

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

SECTOR_ID_MAP = {
    "Energy Minerals": "Energi & Pertambangan",
    "Non-Energy Minerals": "Mineral & Logam Dasar",
    "Finance": "Keuangan & Perbankan",
    "Consumer Non-Durables": "Barang Konsumen Primer",
    "Consumer Durables": "Barang Konsumen Sekunder",
    "Consumer Services": "Jasa Konsumen",
    "Retail Trade": "Perdagangan Ritel",
    "Communications": "Komunikasi & Telko",
    "Utilities": "Utilitas & Energi Terbarukan",
    "Transportation": "Transportasi & Logistik",
    "Industrial Services": "Jasa Industri & Konstruksi",
    "Producer Manufacturing": "Manufaktur Industri",
    "Process Industries": "Industri Pengolahan & Kimia",
    "Health Technology": "Teknologi Kesehatan & Farmasi",
    "Health Services": "Layanan Kesehatan & Rumah Sakit",
    "Technology Services": "Layanan Teknologi & Digital",
    "Electronic Technology": "Teknologi Elektronik",
    "Commercial Services": "Jasa Komersial",
    "Distribution Services": "Jasa Distribusi",
}

POS_NEWS_WORDS = (
    "naik", "melesat", "melonjak", "menguat", "rekor", "untung", "laba", "dividen",
    "ekspansi", "akuisisi", "kontrak", "proyek", "buyback", "rekomendasi beli",
    "target harga", "akumulasi", "tumbuh", "positif", "surplus", "terbang", "rally",
)
NEG_NEWS_WORDS = (
    "turun", "anjlok", "ambruk", "melemah", "rugi", "koreksi", "utang", "gagal bayar",
    "pkpu", "pailit", "suspensi", "uma", "jual", "distribusi", "tertekan", "merosot",
    "pangkas", "negatif", "defisit", "arb", "penurunan",
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


def _now_wib():
    return datetime.now(WIB)


def _today_wib_str():
    return _now_wib().strftime("%Y-%m-%d")


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


def _tick_bei(price):
    if price < 200:
        return 1
    if price < 500:
        return 2
    if price < 2000:
        return 5
    if price < 5000:
        return 10
    return 25


def round_fraksi_bei(price):
    if price is None or price <= 0:
        return 0
    tick = _tick_bei(price)
    return max(1, int(round(price / tick) * tick))


def floor_fraksi_bei(price):
    if price is None or price <= 0:
        return 0
    tick = _tick_bei(price)
    return max(1, int(math.floor(price / tick) * tick))


def safe_num(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


def _local_phrase_translate(text):
    phrases = [
        ("engages in the provision of", "bergerak di bidang penyediaan"),
        ("engages in the", "bergerak dalam bidang"),
        ("is engaged in", "bergerak di bidang"),
        ("operates through the following segments:", "beroperasi melalui segmen berikut:"),
        ("operates through", "beroperasi melalui"),
        ("The company was founded", "Perusahaan ini didirikan"),
        ("was founded in", "didirikan pada tahun"),
        ("and is headquartered in", "dan berkantor pusat di"),
        ("headquartered in", "berkantor pusat di"),
        ("is a subsidiary of", "merupakan anak perusahaan dari"),
        ("as a subsidiary of", "sebagai anak perusahaan dari"),
        ("in Indonesia and internationally", "di Indonesia maupun internasional"),
        ("in Indonesia", "di Indonesia"),
        ("products and services", "produk dan layanan"),
        ("banking products and services", "produk dan layanan perbankan"),
        ("coal mining", "pertambangan batu bara"),
        ("nickel mining", "pertambangan nikel"),
        ("oil and gas", "minyak dan gas bumi"),
        ("real estate", "properti dan real estat"),
        ("telecommunications", "telekomunikasi"),
        ("healthcare", "layanan kesehatan"),
        ("retail", "ritel"),
    ]
    out = text
    for en, idn in phrases:
        out = re.sub(re.escape(en), idn, out, flags=re.IGNORECASE)
    return out


def translate_to_id(text):
    if not text or not text.strip():
        return ""
    clean = text.strip()[:1800]

    try:
        data = urllib.parse.urlencode({"q": clean}).encode("utf-8")
        req = urllib.request.Request(
            "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=id&dt=t",
            data=data,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
        res = "".join(chunk[0] for chunk in parsed[0] if chunk and chunk[0])
        if res and res.strip().lower() != clean.lower():
            return res
    except Exception:
        pass

    return _local_phrase_translate(clean)


def translate_role(title):
    if not title:
        return "-"
    replacements = [
        ("Vice President Director", "Wakil Direktur Utama"),
        ("President Director", "Direktur Utama"),
        ("Independent President Commissioner", "Komisaris Utama Independen"),
        ("President Commissioner", "Komisaris Utama"),
        ("Independent Commissioner", "Komisaris Independen"),
        ("Vice President Commissioner", "Wakil Komisaris Utama"),
        ("Chief Executive Officer", "Direktur Utama (CEO)"),
        ("Chief Financial Officer", "Direktur Keuangan (CFO)"),
        ("Chief Operating Officer", "Direktur Operasional (COO)"),
        ("Corporate Secretary", "Sekretaris Perusahaan"),
        ("Commissioner", "Komisaris"),
        ("Director", "Direktur"),
        ("Officer", "Pejabat Eksekutif"),
        ("10% Owner", "Pemegang Saham >=10%"),
        ("Beneficial Owner", "Pemilik Manfaat / Pengendali"),
    ]
    out = title
    for en, idn in replacements:
        out = out.replace(en, idn)
    return out


def post_tv_scanner(columns):
    payload = {
        "filter": [
            {"left": "exchange", "operation": "equal", "right": "IDX"},
            {"left": "close", "operation": "greater", "right": 0},
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

    close_int = round_fraksi_bei(close)
    open_int = round_fraksi_bei(open_p)
    high_int = max(close_int, open_int, round_fraksi_bei(high_p))
    low_int = min(close_int, open_int, floor_fraksi_bei(low_p))
    prev_close_int = round_fraksi_bei(close / (1 + change / 100.0)) if abs(change) < 99 else close_int

    val_traded = close_int * volume
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

    sector_raw = row_dict.get("sector") or "-"
    sector = SECTOR_ID_MAP.get(sector_raw, sector_raw)
    industry = row_dict.get("industry") or "-"
    desc = row_dict.get("description") or ticker

    debt_asset_ratio = round((tot_debt / tot_assets) * 100, 1) if (tot_debt is not None and tot_assets and tot_assets > 0) else None
    ind_lower = (industry + " " + sector_raw).lower()
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

    risk_unit = max(atr * 1.45, close_int * 0.03)
    if is_rebound:
        entry_low = floor_fraksi_bei(close_int * 0.985)
        entry_high = max(entry_low, round_fraksi_bei(close_int * 1.005))
        sl_raw = min(low_int * 0.98, close_int - risk_unit)
    elif is_breakout:
        entry_low = floor_fraksi_bei(max(ema20 * 0.99, close_int * 0.985))
        entry_high = max(entry_low, round_fraksi_bei(close_int * 1.01))
        sl_raw = max(ema20 * 0.97, close_int - risk_unit)
    else:
        base_sup = min(ema20, vwap) if ema20 > 0 else close_int * 0.97
        entry_low = floor_fraksi_bei(max(base_sup, close_int * 0.97))
        entry_high = max(entry_low, round_fraksi_bei(close_int))
        sl_raw = min(piv_s1, close_int - risk_unit)

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
        action_note = f"Konfluensi kuat: Skor {alpha_score}/100, aliran dana & tren Stage-2 sejalan. Akumulasi di Rp {entry_low:,}-{entry_high:,}."
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
        "open": open_int,
        "high": high_int,
        "low": low_int,
        "close": close_int,
        "prev_close": prev_close_int,
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
            "sl_pct": round(((stop_loss - entry_high) / entry_high) * 100, 1) if entry_high else 0,
            "tp1_pct": round(((tp1 - entry_high) / entry_high) * 100, 1) if entry_high else 0,
            "tp2_pct": round(((tp2 - entry_high) / entry_high) * 100, 1) if entry_high else 0,
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
        "updated_at": _now_wib().strftime("%Y-%m-%d %H:%M:%S WIB"),
        "market_date": _today_wib_str(),
        "total_scanned": len(results),
        "total_issi": sum(1 for r in results if r["is_issi"]),
        "strong_buy_count": sum(1 for r in results if r["signal_code"] in ("STRONG_BUY", "BUY_BREAKOUT")),
        "source": "TradingView Live Scanner + Yahoo Finance Sync (IDX)",
        "stocks": results,
    }
    _cache["timestamp"] = now
    _cache["data"] = payload
    return payload


def _sync_live_candle_with_market(bars, ticker, live_stock=None):
    """Memastikan bar terakhir OHLCV selaras dengan harga live TradingView pada hari bursa aktif."""
    if not bars:
        bars = []

    if live_stock is None:
        market = get_market_data(force=False)
        live_stock = next((x for x in market.get("stocks", []) if x["ticker"] == ticker), None)

    if not live_stock:
        return bars

    today_str = _today_wib_str()
    live_bar = {
        "date": today_str,
        "open": float(live_stock["open"]),
        "high": float(live_stock["high"]),
        "low": float(live_stock["low"]),
        "close": float(live_stock["close"]),
        "volume": float(live_stock["volume"]),
    }

    if not bars:
        return [live_bar]

    last_bar = bars[-1]
    if last_bar["date"] == today_str:
        bars[-1] = {
            "date": today_str,
            "open": float(live_stock["open"]) or last_bar["open"],
            "high": max(last_bar["high"], float(live_stock["high"]), float(live_stock["close"])),
            "low": min(last_bar["low"], float(live_stock["low"]) or last_bar["low"], float(live_stock["close"])),
            "close": float(live_stock["close"]),
            "volume": max(last_bar["volume"], float(live_stock["volume"])),
        }
    elif last_bar["date"] < today_str and float(live_stock["close"]) != float(last_bar["close"]):
        bars.append(live_bar)

    return bars


def fetch_yf_ohlcv(ticker, range_str="1y", live_stock=None, force=False):
    clean_ticker = (ticker or "").upper().replace(".JK", "").strip()
    key = f"{clean_ticker}:{range_str}"
    now = time.time()
    cached = _ohlcv_cache.get(key)
    if not force and cached and (now - cached["ts"] < OHLCV_TTL):
        return _sync_live_candle_with_market(list(cached["bars"]), clean_ticker, live_stock=live_stock)

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(clean_ticker)}.JK?range={urllib.parse.quote(range_str)}&interval=1d"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    bars = []
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        res = (data.get("chart") or {}).get("result") or []
        if res:
            r0 = res[0]
            ts_list = r0.get("timestamp") or []
            quote = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
            opens = quote.get("open") or []
            highs = quote.get("high") or []
            lows = quote.get("low") or []
            closes = quote.get("close") or []
            vols = quote.get("volume") or []

            for i, ts in enumerate(ts_list):
                c = closes[i] if i < len(closes) else None
                o = opens[i] if i < len(opens) else c
                h = highs[i] if i < len(highs) else c
                l = lows[i] if i < len(lows) else c
                v = vols[i] if i < len(vols) else 0
                if c is None or o is None or h is None or l is None or c <= 0:
                    continue
                dt_wib = datetime.fromtimestamp(ts, tz=WIB)
                bars.append({
                    "date": dt_wib.strftime("%Y-%m-%d"),
                    "open": float(round_fraksi_bei(o)),
                    "high": float(round_fraksi_bei(h)),
                    "low": float(floor_fraksi_bei(l)),
                    "close": float(round_fraksi_bei(c)),
                    "volume": float(v or 0),
                })
    except Exception:
        pass

    merged = _sync_live_candle_with_market(bars, clean_ticker, live_stock=live_stock)
    _ohlcv_cache[key] = {"ts": now, "bars": merged}
    return merged


@app.get("/", response_class=HTMLResponse)
def home():
    html_path = os.path.join(BASE_DIR, "react_ui.html")
    if not os.path.exists(html_path):
        return HTMLResponse("<h3>File react_ui.html tidak ditemukan di repository.</h3>", status_code=500)
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/api/health")
def health():
    return {"status": "ok", "wib_time": _now_wib().strftime("%Y-%m-%d %H:%M:%S WIB")}


@app.get("/api/scan")
def scan(force: int = 0):
    try:
        return get_market_data(force=(force == 1))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/ohlcv")
def ohlcv(ticker: str = "BRIS", range_str: str = "6mo", force: int = 0):
    t = (ticker or "BRIS").upper().replace(".JK", "").strip()
    rng = range_str if range_str in ("1mo", "3mo", "6mo", "1y", "2y") else "6mo"
    try:
        market = get_market_data(force=(force == 1))
        live_stock = next((x for x in market.get("stocks", []) if x["ticker"] == t), None)
        bars = fetch_yf_ohlcv(t, range_str=rng, live_stock=live_stock, force=(force == 1))
        return {
            "ticker": t,
            "range": rng,
            "updated_at": market.get("updated_at"),
            "live_price": live_stock["close"] if live_stock else None,
            "bars": bars,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
