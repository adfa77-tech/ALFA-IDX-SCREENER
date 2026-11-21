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
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="ALPHA IDX • Pro Terminal")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ISSI_REPO_FILE = os.path.join(BASE_DIR, "issi_list.txt")
ISSI_TMP_FILE = "/tmp/issi_list.txt"

CACHE_TTL = 25
PROFILE_TTL = 300
OHLCV_TTL = 300
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

    try:
        sentences = re.split(r"(?<=[.!?])\s+", clean)
        chunks, cur = [], ""
        for sent in sentences:
            if len(cur) + len(sent) + 1 <= 440:
                cur = (cur + " " + sent).strip()
            else:
                if cur:
                    chunks.append(cur)
                cur = sent[:440]
        if cur:
            chunks.append(cur)

        out_parts = []
        for ch in chunks[:4]:
            url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode({"q": ch, "langpair": "en|id"})
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                j = json.loads(resp.read().decode("utf-8"))
            t_txt = (j.get("responseData") or {}).get("translatedText") or ""
            if t_txt and "MYMEMORY WARNING" not in t_txt.upper():
                out_parts.append(t_txt)
        if out_parts:
            return " ".join(out_parts)
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
        ("10% Owner", "Pemegang Saham ≥10%"),
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


def fetch_yf_ohlcv(ticker, range_str="1y"):
    key = f"{ticker}:{range_str}"
    now = time.time()
    cached = _ohlcv_cache.get(key)
    if cached and (now - cached["ts"] < OHLCV_TTL):
        return cached["bars"]

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}.JK?range={range_str}&interval=1d"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    res = (data.get("chart") or {}).get("result") or []
    if not res:
        return []
    r0 = res[0]
    ts_list = r0.get("timestamp") or []
    quote = ((r0.get("indicators") or {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    vols = quote.get("volume") or []

    bars = []
    for i, ts in enumerate(ts_list):
        c = closes[i] if i < len(closes) else None
        o = opens[i] if i < len(opens) else c
        h = highs[i] if i < len(highs) else c
        l = lows[i] if i < len(lows) else c
        v = vols[i] if i < len(vols) else 0
        if c is None or o is None or h is None or l is None or c <= 0:
            continue
        bars.append({
            "date": time.strftime("%Y-%m-%d", time.gmtime(ts + 7 * 3600)),
            "open": float(o),
            "high": float(h),
            "low": float(l),
            "close": float(c),
            "volume": float(v or 0),
        })
    _ohlcv_cache[key] = {"ts": now, "bars": bars}
    return bars


def fetch_google_news_id(query_str, limit=8):
    now = time.time()
    cached = _news_cache.get(query_str)
    if cached and (now - cached["ts"] < NEWS_TTL):
        return cached["items"]

    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query_str,
        "hl": "id",
        "gl": "ID",
        "ceid": "ID:id",
    })
    items = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=7) as resp:
            xml_bytes = resp.read()
        root = ET.fromstring(xml_bytes)
        for item in root.findall("./channel/item")[:limit]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            source = source_el.text.strip() if (source_el is not None and source_el.text) else "Berita Ekonomi"
            tl = title.lower()
            pos_cnt = sum(1 for w in POS_NEWS_WORDS if w in tl)
            neg_cnt = sum(1 for w in NEG_NEWS_WORDS if w in tl)
            if pos_cnt > neg_cnt:
                sent, sent_score = "Positif", pos_cnt - neg_cnt
            elif neg_cnt > pos_cnt:
                sent, sent_score = "Negatif", pos_cnt - neg_cnt
            else:
                sent, sent_score = "Netral", 0
            items.append({
                "title": title,
                "link": link,
                "published": pub[:22] if pub else "-",
                "source": source,
                "sentiment": sent,
                "score": sent_score,
            })
    except Exception:
        pass

    _news_cache[query_str] = {"ts": now, "items": items}
    return items


def _get_yf_auth(force=False):
    now = time.time()
    if not force and _yf_auth["opener"] and _yf_auth["crumb"] and (now - _yf_auth["timestamp"] < 1500):
        return _yf_auth["opener"], _yf_auth["crumb"]

    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    opener.addheaders = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
        ("Accept", "application/json,text/html,*/*"),
    ]
    try:
        opener.open("https://fc.yahoo.com", timeout=6).read()
    except Exception:
        pass
    crumb = opener.open("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=6).read().decode("utf-8").strip()
    _yf_auth["timestamp"] = now
    _yf_auth["opener"] = opener
    _yf_auth["crumb"] = crumb
    return opener, crumb


def _fmt_raw(obj, key):
    val = obj.get(key)
    if isinstance(val, dict):
        return val.get("raw"), val.get("fmt")
    return val, str(val) if val is not None else None


def fetch_yahoo_profile(ticker, stock_obj=None):
    now = time.time()
    cached = _profile_cache.get(ticker)
    if cached and (now - cached["ts"] < PROFILE_TTL):
        return cached["data"]

    modules = ",".join([
        "assetProfile",
        "majorHoldersBreakdown",
        "insiderHolders",
        "insiderTransactions",
        "institutionOwnership",
        "fundOwnership",
        "netSharePurchaseActivity",
        "defaultKeyStatistics",
        "calendarEvents",
        "summaryDetail",
    ])

    fallback_summary = ""
    if stock_obj:
        fallback_summary = (
            f"{stock_obj['name']} (kode IDX:{ticker}) adalah emiten tercatat di Bursa Efek Indonesia yang bergerak di sektor "
            f"{stock_obj['sector']} (sub-industri: {stock_obj['industry']}), dengan kapitalisasi pasar sekitar Rp {stock_obj['mcap_t']} Triliun."
        )

    result = {
        "yahoo_ok": False,
        "yahoo_note": "",
        "summary": fallback_summary,
        "website": "",
        "address": "",
        "employees": None,
        "officers": [],
        "ownership": {
            "insiders_pct": None,
            "institutions_pct": None,
            "public_float_pct": None,
            "institutions_count": None,
            "shares_outstanding": None,
            "shares_outstanding_fmt": "-",
            "float_shares": None,
            "float_shares_fmt": "-",
        },
        "insider_holders": [],
        "insider_transactions": [],
        "net_insider_activity": None,
        "institutions": [],
        "funds": [],
        "calendar": {"ex_dividend": "-", "dividend_date": "-", "earnings_date": "-", "dividend_rate": "-"},
    }

    try:
        opener, crumb = _get_yf_auth()
        url = (
            f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}.JK"
            f"?modules={urllib.parse.quote(modules)}&crumb={urllib.parse.quote(crumb)}"
        )
        try:
            raw_json = opener.open(url, timeout=9).read().decode("utf-8")
        except urllib.error.HTTPError as he:
            if he.code in (401, 403):
                opener, crumb = _get_yf_auth(force=True)
                url = (
                    f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}.JK"
                    f"?modules={urllib.parse.quote(modules)}&crumb={urllib.parse.quote(crumb)}"
                )
                raw_json = opener.open(url, timeout=9).read().decode("utf-8")
            else:
                raise

        parsed = json.loads(raw_json)
        res_list = parsed.get("quoteSummary", {}).get("result") or []
        if not res_list:
            result["yahoo_note"] = "Data tambahan Yahoo Finance tidak tersedia untuk emiten ini."
            return result

        data = res_list[0]
        result["yahoo_ok"] = True

        ap = data.get("assetProfile") or {}
        raw_summary = ap.get("longBusinessSummary") or ""
        result["summary"] = translate_to_id(raw_summary) if raw_summary else fallback_summary
        result["website"] = ap.get("website") or ""
        addr_parts = [ap.get("address1"), ap.get("city"), ap.get("country")]
        result["address"] = ", ".join([p for p in addr_parts if p])
        result["employees"] = ap.get("fullTimeEmployees")
        result["officers"] = [
            {
                "name": o.get("name") or "-",
                "title": translate_role(o.get("title") or "-"),
                "age": o.get("age"),
            }
            for o in (ap.get("companyOfficers") or [])[:12]
        ]

        mhb = data.get("majorHoldersBreakdown") or {}
        dks = data.get("defaultKeyStatistics") or {}
        ins_raw, _ = _fmt_raw(mhb, "insidersPercentHeld")
        if ins_raw is None:
            ins_raw, _ = _fmt_raw(dks, "heldPercentInsiders")
        inst_raw, _ = _fmt_raw(mhb, "institutionsPercentHeld")
        if inst_raw is None:
            inst_raw, _ = _fmt_raw(dks, "heldPercentInstitutions")
        inst_cnt, _ = _fmt_raw(mhb, "institutionsCount")
        sh_out, sh_out_fmt = _fmt_raw(dks, "sharesOutstanding")
        fl_sh, fl_sh_fmt = _fmt_raw(dks, "floatShares")

        ins_pct = round(ins_raw * 100, 2) if ins_raw is not None else None
        inst_pct = round(inst_raw * 100, 2) if inst_raw is not None else None
        pub_pct = round(max(0.0, 100.0 - (ins_pct or 0.0) - (inst_pct or 0.0)), 2) if (ins_pct is not None or inst_pct is not None) else None

        result["ownership"] = {
            "insiders_pct": ins_pct,
            "institutions_pct": inst_pct,
            "public_float_pct": pub_pct,
            "institutions_count": int(inst_cnt) if inst_cnt is not None else None,
            "shares_outstanding": sh_out,
            "shares_outstanding_fmt": sh_out_fmt or "-",
            "float_shares": fl_sh,
            "float_shares_fmt": fl_sh_fmt or "-",
        }

        ih = (data.get("insiderHolders") or {}).get("holders") or []
        result["insider_holders"] = [
            {
                "name": h.get("name") or "-",
                "relation": translate_role(h.get("relation") or "-"),
                "action": h.get("transactionDescription") or "-",
                "date": (h.get("latestTransDate") or {}).get("fmt") or "-",
                "shares": (h.get("positionDirect") or {}).get("fmt") or "-",
            }
            for h in ih[:12]
        ]

        itx = (data.get("insiderTransactions") or {}).get("transactions") or []
        result["insider_transactions"] = [
            {
                "name": tx.get("filerName") or "-",
                "relation": translate_role(tx.get("filerRelation") or "-"),
                "text": (tx.get("transactionText") or "-").replace("Purchase", "Pembelian").replace("Sale", "Penjualan"),
                "shares": (tx.get("shares") or {}).get("fmt") or "-",
                "value": (tx.get("value") or {}).get("fmt") or "-",
                "date": (tx.get("startDate") or {}).get("fmt") or "-",
                "ownership": tx.get("ownership") or "-",
            }
            for tx in itx[:15]
        ]

        nspa = data.get("netSharePurchaseActivity") or {}
        if nspa:
            b_cnt, _ = _fmt_raw(nspa, "buyInfoCount")
            s_cnt, _ = _fmt_raw(nspa, "sellInfoCount")
            _, b_sh = _fmt_raw(nspa, "buyInfoShares")
            _, s_sh = _fmt_raw(nspa, "sellInfoShares")
            _, n_sh = _fmt_raw(nspa, "netInfoShares")
            if b_cnt is not None or s_cnt is not None:
                result["net_insider_activity"] = {
                    "period": nspa.get("period") or "6m",
                    "buy_count": b_cnt or 0,
                    "sell_count": s_cnt or 0,
                    "buy_shares": b_sh or "0",
                    "sell_shares": s_sh or "0",
                    "net_shares": n_sh or "0",
                }

        io_list = (data.get("institutionOwnership") or {}).get("ownershipList") or []
        result["institutions"] = [
            {
                "name": x.get("organization") or "-",
                "pct": round(((_fmt_raw(x, "pctHeld")[0] or 0) * 100), 2),
                "shares": (x.get("position") or {}).get("fmt") or "-",
                "date": (x.get("reportDate") or {}).get("fmt") or "-",
            }
            for x in io_list[:10]
        ]

        fo_list = (data.get("fundOwnership") or {}).get("ownershipList") or []
        result["funds"] = [
            {
                "name": x.get("organization") or "-",
                "pct": round(((_fmt_raw(x, "pctHeld")[0] or 0) * 100), 2),
                "shares": (x.get("position") or {}).get("fmt") or "-",
                "date": (x.get("reportDate") or {}).get("fmt") or "-",
            }
            for x in fo_list[:10]
        ]

        cal = data.get("calendarEvents") or {}
        sd = data.get("summaryDetail") or {}
        ex_div = (cal.get("exDividendDate") or {}).get("fmt") or (sd.get("exDividendDate") or {}).get("fmt") or "-"
        div_dt = (cal.get("dividendDate") or {}).get("fmt") or "-"
        earn_list = (cal.get("earnings") or {}).get("earningsDate") or []
        earn_dt = earn_list[0].get("fmt") if (earn_list and isinstance(earn_list[0], dict)) else "-"
        _, div_rate_fmt = _fmt_raw(sd, "dividendRate")
        result["calendar"] = {
            "ex_dividend": ex_div,
            "dividend_date": div_dt,
            "earnings_date": earn_dt,
            "dividend_rate": div_rate_fmt or "-",
        }

        _profile_cache[ticker] = {"ts": now, "data": result}
    except Exception as e:
        result["yahoo_note"] = f"Feed kepemilikan Yahoo Finance sementara dibatasi ({e}). Sumber data lain tetap aktif."

    return result


def compute_historical_context(bars):
    if not bars or len(bars) < 25:
        return {
            "available": False,
            "ret_1m": None,
            "ret_3m": None,
            "ret_6m": None,
            "acc_days_20": 0,
            "dist_days_20": 0,
            "support_20d": None,
            "resistance_20d": None,
            "volatility_ann": None,
        }
    closes = [b["close"] for b in bars]
    last = closes[-1]
    ret_1m = round(((last / closes[-22]) - 1) * 100, 2) if len(closes) >= 22 else None
    ret_3m = round(((last / closes[-64]) - 1) * 100, 2) if len(closes) >= 64 else None
    ret_6m = round(((last / closes[0]) - 1) * 100, 2)

    recent_20 = bars[-20:]
    avg_vol_20 = sum(b["volume"] for b in recent_20) / len(recent_20)
    acc_days = sum(1 for i in range(1, len(recent_20)) if recent_20[i]["close"] > recent_20[i - 1]["close"] and recent_20[i]["volume"] >= avg_vol_20)
    dist_days = sum(1 for i in range(1, len(recent_20)) if recent_20[i]["close"] < recent_20[i - 1]["close"] and recent_20[i]["volume"] >= avg_vol_20)
    sup_20 = round_fraksi_bei(min(b["low"] for b in recent_20))
    res_20 = round_fraksi_bei(max(b["high"] for b in recent_20))

    rets = [(closes[i] / closes[i - 1]) - 1 for i in range(max(1, len(closes) - 30), len(closes)) if closes[i - 1] > 0]
    if rets:
        mean_r = sum(rets) / len(rets)
        var_r = sum((r - mean_r) ** 2 for r in rets) / len(rets)
        vol_ann = round(math.sqrt(var_r) * math.sqrt(252) * 100, 1)
    else:
        vol_ann = None

    return {
        "available": True,
        "ret_1m": ret_1m,
        "ret_3m": ret_3m,
        "ret_6m": ret_6m,
        "acc_days_20": acc_days,
        "dist_days_20": dist_days,
        "support_20d": sup_20,
        "resistance_20d": res_20,
        "volatility_ann": vol_ann,
    }


def build_quant_ai_report(s, all_stocks, hist_ctx, profile_ctx, news_items, question=""):
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
    if c > e20 > e50 > e200:
        if s["rsi"] >= 74:
            stage = "Stage 3 • Overextended / Rawan Profit Taking"
            stage_desc = f"Harga sudah jauh di atas EMA20 (Rp {e20:,}) dengan RSI {s['rsi']}. Tren masih naik, tetapi rawan koreksi sehat jangka pendek."
        else:
            stage = "Stage 2 • Markup / Uptrend Institusi"
            stage_desc = f"Formasi sempurna: Harga (Rp {c:,}) > EMA20 ({e20:,}) > EMA50 ({e50:,}) > EMA200 ({e200:,}). Zona terbaik mengikuti tren naik."
    elif c > e20 and e20 <= e50:
        stage = "Stage 1 → 2 • Transisi Akumulasi ke Breakout"
        stage_desc = f"Harga mulai menembus EMA20 (Rp {e20:,}) dan bersiap membalikkan tren menengah (EMA50 Rp {e50:,})."
    elif c < e50 and e20 < e50:
        if s["is_rebound"]:
            stage = "Stage 4 (Akhir) • Technical Rebound dari Jenuh Jual"
            stage_desc = f"Tren utama masih di bawah EMA50 (Rp {e50:,}), namun muncul pantulan awal dari oversold (RSI {s['rsi']}). Cocok swing cepat."
        else:
            stage = "Stage 4 • Markdown / Downtrend"
            stage_desc = f"Harga berada di bawah EMA20 ({e20:,}) dan EMA50 ({e50:,}). Tekanan jual masih dominan; tunggu base baru terbentuk."
    else:
        stage = "Stage 1 • Konsolidasi / Sideways Base"
        stage_desc = f"Harga bergerak mendatar di sekitar EMA20–EMA50 (BB Width {s['bbw']}%). Menunggu katalis volume."

    vwap_diff = round(((c - s["vwap"]) / s["vwap"]) * 100, 2) if s["vwap"] else 0
    hist_flow = ""
    if hist_ctx.get("available"):
        hist_flow = (
            f" Dalam 20 hari bursa terakhir tercatat {hist_ctx['acc_days_20']} hari akumulasi vs "
            f"{hist_ctx['dist_days_20']} hari distribusi (Return 3Bln: {hist_ctx['ret_3m']}%, 6Bln: {hist_ctx['ret_6m']}%, "
            f"Support 20D Rp {hist_ctx['support_20d']:,}, Resistance 20D Rp {hist_ctx['resistance_20d']:,})."
        )

    if s["rvol"] >= 1.8 and c >= s["vwap"]:
        flow = f"Akumulasi Agresif: Volume hari ini {s['rvol']}x rata-rata 10 hari, harga +{vwap_diff}% di atas VWAP (Rp {s['vwap']:,}).{hist_flow}"
    elif s["vwma_bull"] and c >= s["vwap"]:
        flow = f"Aliran Dana Positif: VWMA > SMA20 dan harga di atas VWAP (Rp {s['vwap']:,}).{hist_flow}"
    elif s["rvol"] >= 1.5 and s["change"] < -1.5:
        flow = f"Distribusi / Tekanan Jual: Volume tinggi ({s['rvol']}x) disertai penurunan {s['change']}%.{hist_flow}"
    else:
        flow = f"Volume Normal ({s['rvol']}x), posisi {vwap_diff:+.2f}% dari VWAP (Rp {s['vwap']:,}).{hist_flow}"

    own = (profile_ctx or {}).get("ownership") or {}
    own_txt = ""
    if own.get("insiders_pct") is not None:
        own_txt = f" Struktur saham: Pengendali/Insider {own['insiders_pct']}%, Institusi {own.get('institutions_pct')}%, Publik {own.get('public_float_pct')}%."

    pe_txt = f"PER {s['pe']}x" if s["pe"] is not None else "PER negatif/N/A"
    pbv_txt = f"PBV {s['pbv']}x" if s["pbv"] is not None else "PBV N/A"
    roe_txt = f"ROE {s['roe']}%" if s["roe"] is not None else "ROE N/A"
    da_txt = f"Utang/Aset {s['debt_asset_ratio']}%" if s["debt_asset_ratio"] is not None else "Utang/Aset N/A"
    syariah_status = "LOLOS SYARIAH ISSI" if s["is_issi"] else "NON-ISSI / PERLU CEK DES"
    fund_audit = (
        f"Status: {syariah_status} ({da_txt} vs batas OJK 45%). Valuasi {pe_txt}, {pbv_txt}, {roe_txt}, Div Yield {s['div_yield']}%.{own_txt}"
    )

    pos_n = sum(1 for n in news_items if n["sentiment"] == "Positif")
    neg_n = sum(1 for n in news_items if n["sentiment"] == "Negatif")
    if news_items:
        overall_sent = "Positif" if pos_n > neg_n else ("Negatif" if neg_n > pos_n else "Netral")
        news_summary = f"Sentimen Berita Terkini: {overall_sent} ({pos_n} positif, {neg_n} negatif dari {len(news_items)} berita media ekonomi Indonesia)."
    else:
        overall_sent = "Netral"
        news_summary = "Belum ada lonjakan pemberitaan media besar dalam beberapa hari terakhir (pergerakan murni teknikal/arus dana)."

    risks = []
    if s["value_traded_b"] < 1.0:
        risks.append(f"Likuiditas tipis (Rp {s['value_traded_b']} M/hari) — rawan spread lebar.")
    if s["rsi"] >= 74:
        risks.append(f"RSI Overbought ({s['rsi']}) — hindari kejar harga di pucuk.")
    if c < e50:
        risks.append(f"Masih di bawah EMA50 (Rp {e50:,}) — tren menengah belum sepenuhnya aman.")
    if hist_ctx.get("volatility_ann") and hist_ctx["volatility_ann"] >= 55:
        risks.append(f"Volatilitas tahunan tinggi ({hist_ctx['volatility_ann']}%) — wajib perkecil ukuran lot.")
    if neg_n > pos_n:
        risks.append("Sentimen berita terbaru cenderung negatif — pantau reaksi pasar terhadap isu terkini.")
    if s["plan"]["rr"] < 1.5:
        risks.append(f"Risk:Reward hanya 1:{s['plan']['rr']} — ruang profit terbatas dibanding risiko SL.")
    if not risks:
        risks.append("Risiko teknikal, likuiditas, dan sentimen berita relatif terkendali selama disiplin SL.")

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
        "bullish": f"Bertahan di atas Rp {p['entry_high']:,} dengan RVOL ≥ 1.3x membuka peluang naik ke TP1 Rp {p['tp1']:,} (+{p['tp1_pct']}%) hingga TP2 Rp {p['tp2']:,} (+{p['tp2_pct']}%).",
        "base": f"Jika koreksi sehat, area antre ideal di Rp {p['entry_low']:,}–{p['entry_high']:,} (dekat Support 20D / VWAP) untuk menjaga R:R 1:{p['rr']}.",
        "bearish": f"Batal jika jebol Stop Loss Rp {p['stop_loss']:,} ({p['sl_pct']}%). Disiplin Cut Loss untuk menghindari drawdown lebih dalam.",
    }

    q = (question or "").strip().lower()
    if not q:
        qa_answer = (
            f"Sintesis 4 Sumber untuk IDX:{s['ticker']} ({s['signal']} • Skor {s['alpha_score']}/100, Peringkat #{rank}/{len(peers)} sektor {s['sector']}):\n"
            f"• Teknikal & Aksi Harga: {stage_desc}\n"
            f"• Arus Dana & Historis: {flow}\n"
            f"• Berita & Katalis: {news_summary}\n"
            f"• Eksekusi: {p['note']}"
        )
    elif "hold" in q or "jangka" in q or "menengah" in q or "lama" in q:
        qa_answer = (
            f"Analisa Hold Menengah {s['ticker']}: Fase saat ini '{stage}' (Return 6Bln: {hist_ctx.get('ret_6m', '-')}%). "
            + (f"Struktur Stage-2 dan fundamental ({pe_txt}, {roe_txt}) mendukung untuk di-hold selama harga bertahan di atas EMA50 (Rp {e50:,})."
               if (c > e50 and (s["roe"] or 0) >= 8)
               else f"Kurang aman untuk hold pasif jangka panjang karena tren masih di bawah/baru menguji EMA50 (Rp {e50:,}). Gunakan Trailing Stop.")
        )
    elif "cut loss" in q or "average" in q or "cicil" in q or "entry" in q or "beli" in q:
        qa_answer = (
            f"Strategi Entry & Cut Loss {s['ticker']}: Cicil 50% di Rp {p['entry_low']:,}–{p['entry_high']:,} (Support 20D historis: Rp {hist_ctx.get('support_20d') or p['entry_low']:,}), sisa 50% saat konfirmasi mantul. "
            f"Wajib Cut Loss jika tutup di bawah Rp {p['stop_loss']:,} ({p['sl_pct']}%)."
        )
    elif "sektor" in q or "kompetitor" in q or "banding" in q:
        peers_txt = ", ".join([f"{x['ticker']} (Skor {x['alpha_score']}, {x['change']:+.2f}%)" for x in top_peers]) or "tidak ada pembanding likuid"
        qa_answer = f"Di sektor {s['sector']}, {s['ticker']} peringkat #{rank}/{len(peers)} (Skor {s['alpha_score']} vs rata-rata {avg_sector_score}). Kompetitor teratas: {peers_txt}."
    elif "bandar" in q or "trap" in q or "risiko" in q or "jebakan" in q:
        qa_answer = f"Cek Jebakan & Risiko {s['ticker']}: {flow} {news_summary} Peringatan: {' '.join(risks)}"
    else:
        qa_answer = f"Analisa {s['ticker']} ({s['signal']}): {stage_desc} {flow} {news_summary} Area Beli Rp {p['entry_low']:,}–{p['entry_high']:,}, SL Rp {p['stop_loss']:,}, TP1 Rp {p['tp1']:,}."

    conv_base = s["alpha_score"] * 0.8 + (8 if s["value_traded_b"] >= 5 else 0) + (5 if s["plan"]["rr"] >= 2 else 0)
    if hist_ctx.get("available") and hist_ctx["acc_days_20"] > hist_ctx["dist_days_20"]:
        conv_base += 4
    if pos_n > neg_n:
        conv_base += 3

    return {
        "ticker": s["ticker"],
        "conviction": min(98, max(20, round(conv_base))),
        "horizon": horizon,
        "stage": stage,
        "stage_desc": stage_desc,
        "order_flow": flow,
        "fund_audit": fund_audit,
        "news_summary": news_summary,
        "news_sentiment": overall_sent,
        "news_items": news_items[:5],
        "hist_ctx": hist_ctx,
        "ownership": own,
        "calendar": (profile_ctx or {}).get("calendar") or {},
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
        "sources_used": [
            "TradingView Live Scanner",
            "Yahoo Finance 6M OHLCV" if hist_ctx.get("available") else "TradingView Historical",
            "Yahoo Finance Ownership & Calendar" if (profile_ctx or {}).get("yahoo_ok") else "IDX Syariah Audit",
            f"Berita Ekonomi ID ({len(news_items)} artikel)",
        ],
        "llm_used": False,
        "llm_error": "",
    }


def call_gemini_ai(s, quant_report, question, api_key):
    ctx = quant_report["sector_context"]
    hc = quant_report["hist_ctx"]
    headlines = [f"- [{n['sentiment']}] {n['title']} ({n['source']})" for n in quant_report["news_items"]]
    news_block = "\n".join(headlines) if headlines else "- Tidak ada berita terkini yang signifikan."
    prompt = (
        f"Kamu adalah Kepala Riset Ekuitas Pasar Modal Indonesia (BEI/IDX). Lakukan analisa mendalam berbasis 4 sumber data berikut untuk IDX:{s['ticker']} ({s['name']}):\n"
        f"1) TRADINGVIEW LIVE: Harga Rp {s['close']:,} ({s['change']:+.2f}%), Val Rp {s['value_traded_b']}M, RVOL {s['rvol']}x, Alpha {s['alpha_score']}/100 ({s['signal']}), RSI {s['rsi']}, ADX {s['adx']}, VWAP Rp {s['vwap']:,}, EMA20/50/200={s['ema20']:,}/{s['ema50']:,}/{s['ema200']:,}.\n"
        f"   Sektor {s['sector']} (Peringkat #{ctx['rank']}/{ctx['total_peers']}, rata-rata skor {ctx['avg_score']}). Top Peers: {json.dumps(ctx['top_peers'])}\n"
        f"2) HISTORIS 6 BULAN: Return 1M={hc.get('ret_1m')}%, 3M={hc.get('ret_3m')}%, 6M={hc.get('ret_6m')}%, Hari Akumulasi vs Distribusi (20D)={hc.get('acc_days_20')} vs {hc.get('dist_days_20')}, Support 20D Rp {hc.get('support_20d')}, Resistance 20D Rp {hc.get('resistance_20d')}, Volatilitas={hc.get('volatility_ann')}%.\n"
        f"3) FUNDAMENTAL, SYARIAH & KEPEMILIKAN: ISSI={s['is_issi']}, Utang/Aset={s['debt_asset_ratio']}%, PER={s['pe']}x, PBV={s['pbv']}x, ROE={s['roe']}%, DivYield={s['div_yield']}%, Kepemilikan={json.dumps(quant_report['ownership'])}, Kalender={json.dumps(quant_report['calendar'])}.\n"
        f"4) BERITA MEDIA INDONESIA TERKINI:\n{news_block}\n\n"
        f"Rencana Kuantitatif: Beli Rp {s['plan']['entry_low']:,}-{s['plan']['entry_high']:,}, SL Rp {s['plan']['stop_loss']:,} ({s['plan']['sl_pct']}%), TP1 Rp {s['plan']['tp1']:,}, TP2 Rp {s['plan']['tp2']:,}, R:R 1:{s['plan']['rr']}.\n"
        f"Pertanyaan User: {question or 'Berikan riset ekuitas mendalam yang menghubungkan teknikal, jejak akumulasi historis, fundamental/kepemilikan, sentimen berita, skenario jebakan/risiko, dan rencana eksekusi terbaik.'}\n\n"
        f"Jawab dalam Bahasa Indonesia yang tajam, terstruktur (pakai poin bernomor), menyebut angka konkret, dan objektif terhadap risiko."
    )
    payload = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1100},
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


def run_backtest_sim(bars, strategy="BREAKOUT"):
    if not bars or len(bars) < 60:
        return {"error": "Data historis tidak cukup untuk backtest (minimal 60 hari bursa)."}

    closes = [b["close"] for b in bars]
    vols = [b["volume"] for b in bars]

    # Indikator per bar
    ema20, ema50, rsi14, atr14 = [closes[0]], [closes[0]], [50.0] * len(bars), [closes[0] * 0.025] * len(bars)
    k20, k50 = 2 / 21.0, 2 / 51.0
    for i in range(1, len(bars)):
        ema20.append(closes[i] * k20 + ema20[-1] * (1 - k20))
        ema50.append(closes[i] * k50 + ema50[-1] * (1 - k50))

    gains, losses = [0.0], [0.0]
    trs = [bars[0]["high"] - bars[0]["low"]]
    for i in range(1, len(bars)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(0.0, diff))
        losses.append(max(0.0, -diff))
        tr = max(bars[i]["high"] - bars[i]["low"], abs(bars[i]["high"] - closes[i - 1]), abs(bars[i]["low"] - closes[i - 1]))
        trs.append(tr)

    for i in range(14, len(bars)):
        ag = sum(gains[i - 13:i + 1]) / 14.0
        al = sum(losses[i - 13:i + 1]) / 14.0
        rsi14[i] = 100.0 if al == 0 else (100.0 - (100.0 / (1.0 + ag / al)))
        atr14[i] = max(closes[i] * 0.015, sum(trs[i - 13:i + 1]) / 14.0)

    equity = 100.0
    peak = 100.0
    max_dd = 0.0
    in_pos = False
    entry_p, sl_p, tp_p, entry_dt = 0.0, 0.0, 0.0, ""
    trades = []
    curve = []
    fee_roundtrip = 0.004  # 0.15% beli + 0.25% jual BEI

    for i in range(52, len(bars)):
        b = bars[i]
        avg_v10 = sum(vols[i - 10:i]) / 10.0 if i >= 10 else vols[i]
        rvol = (b["volume"] / avg_v10) if avg_v10 > 0 else 1.0
        sma20 = sum(closes[i - 19:i + 1]) / 20.0
        std20 = math.sqrt(sum((x - sma20) ** 2 for x in closes[i - 19:i + 1]) / 20.0)
        bb_up = sma20 + 2 * std20

        if not in_pos:
            sig = False
            if strategy == "BREAKOUT":
                sig = b["close"] > ema20[i] and rvol >= 1.3 and b["close"] > b["open"] and (b["close"] >= bb_up * 0.985 or b["close"] > max(closes[i - 10:i]))
            elif strategy == "TREND":
                sig = ema20[i] > ema50[i] and b["close"] > ema20[i] and closes[i - 1] <= ema20[i - 1]
            elif strategy == "REBOUND":
                sig = 25 <= rsi14[i] <= 42 and rsi14[i] > rsi14[i - 1] and b["close"] > b["open"]

            if sig:
                in_pos = True
                entry_p = b["close"]
                entry_dt = b["date"]
                sl_p = entry_p - 1.5 * atr14[i]
                tp_p = entry_p + 2.8 * atr14[i]
        else:
            exit_reason = None
            exit_p = b["close"]
            if b["low"] <= sl_p:
                exit_reason = "Stop Loss"
                exit_p = sl_p
            elif b["high"] >= tp_p:
                exit_reason = "Take Profit"
                exit_p = tp_p
            elif strategy == "TREND" and b["close"] < ema20[i]:
                exit_reason = "Cross < EMA20"
            elif strategy == "REBOUND" and rsi14[i] >= 65:
                exit_reason = "RSI Target"

            if exit_reason:
                ret = ((exit_p / entry_p) - 1.0) - fee_roundtrip
                equity *= (1.0 + ret)
                trades.append({
                    "entry_date": entry_dt,
                    "exit_date": b["date"],
                    "entry": round_fraksi_bei(entry_p),
                    "exit": round_fraksi_bei(exit_p),
                    "return_pct": round(ret * 100, 2),
                    "reason": exit_reason,
                })
                in_pos = False

        mtm_eq = equity * (b["close"] / entry_p) if in_pos else equity
        peak = max(peak, mtm_eq)
        dd = ((mtm_eq / peak) - 1.0) * 100.0
        max_dd = min(max_dd, dd)
        curve.append({"date": b["date"], "equity": round(mtm_eq, 2)})

    # Tutup posisi terbuka di bar terakhir untuk statistik akhir
    if in_pos:
        ret = ((closes[-1] / entry_p) - 1.0) - fee_roundtrip
        equity *= (1.0 + ret)
        trades.append({
            "entry_date": entry_dt,
            "exit_date": bars[-1]["date"],
            "entry": round_fraksi_bei(entry_p),
            "exit": round_fraksi_bei(closes[-1]),
            "return_pct": round(ret * 100, 2),
            "reason": "Open (Mark-to-Market)",
        })

    wins = [t["return_pct"] for t in trades if t["return_pct"] > 0]
    losses_t = [abs(t["return_pct"]) for t in trades if t["return_pct"] <= 0]
    win_rate = round((len(wins) / len(trades)) * 100, 1) if trades else 0.0
    pf = round(sum(wins) / sum(losses_t), 2) if sum(losses_t) > 0 else (round(sum(wins), 2) if wins else 0.0)
    bh_ret = round(((closes[-1] / closes[52]) - 1.0) * 100, 2)

    return {
        "total_trades": len(trades),
        "win_rate": win_rate,
        "total_return_pct": round(equity - 100.0, 2),
        "buy_hold_pct": bh_ret,
        "max_drawdown_pct": round(max_dd, 2),
        "profit_factor": pf,
        "equity_curve": curve[::max(1, len(curve) // 90)],
        "trades": list(reversed(trades))[:25],
    }


def _send_telegram_msg(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token.strip()}/sendMessage"
    payload = json.dumps({
        "chat_id": str(chat_id).strip(),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ========================
# ENDPOINTS API
# ========================
@app.get("/", response_class=HTMLResponse)
def home():
    html_path = os.path.join(BASE_DIR, "react_ui.html")
    if not os.path.exists(html_path):
        return HTMLResponse("<h3>File react_ui.html tidak ditemukan di repository.</h3>", status_code=500)
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), headers={"Cache-Control": "no-store, no-cache, must-revalidate"})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/scan")
def scan(force: int = 0):
    try:
        return get_market_data(force=(force == 1))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/sectors")
def sectors():
    try:
        market = get_market_data(force=False)
        groups = {}
        for s in market["stocks"]:
            if s["value_traded_b"] < 0.2:
                continue
            sec = s["sector"]
            if sec == "-":
                continue
            groups.setdefault(sec, []).append(s)

        out = []
        for sec, items in groups.items():
            n = len(items)
            avg_chg = round(sum(x["change"] for x in items) / n, 2)
            avg_w = round(sum(x["perf_w"] for x in items) / n, 2)
            avg_1m = round(sum(x["perf_1m"] for x in items) / n, 2)
            avg_alpha = round(sum(x["alpha_score"] for x in items) / n, 1)
            avg_rvol = round(sum(x["rvol"] for x in items) / n, 2)
            tot_val = round(sum(x["value_traded_b"] for x in items), 1)
            issi_cnt = sum(1 for x in items if x["is_issi"])

            # RRG Quadrant: RS proxy (avg_1m) vs Momentum (avg_w)
            if avg_1m >= 0 and avg_w >= 0:
                quad = "LEADING"
            elif avg_1m >= 0 and avg_w < 0:
                quad = "WEAKENING"
            elif avg_1m < 0 and avg_w >= 0:
                quad = "IMPROVING"
            else:
                quad = "LAGGING"

            top3 = sorted(items, key=lambda x: (x["alpha_score"], x["value_traded_b"]), reverse=True)[:3]
            out.append({
                "sector": sec,
                "count": n,
                "issi_count": issi_cnt,
                "avg_change": avg_chg,
                "avg_perf_w": avg_w,
                "avg_perf_1m": avg_1m,
                "avg_alpha": avg_alpha,
                "avg_rvol": avg_rvol,
                "total_val_b": tot_val,
                "quadrant": quad,
                "top_stocks": [{"ticker": x["ticker"], "close": x["close"], "change": x["change"], "alpha_score": x["alpha_score"], "is_issi": x["is_issi"]} for x in top3],
            })

        out.sort(key=lambda x: (x["avg_alpha"], x["total_val_b"]), reverse=True)
        return {"updated_at": market["updated_at"], "sectors": out}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/profile")
def stock_profile(ticker: str):
    t = (ticker or "").upper().strip()
    if not t:
        return JSONResponse({"error": "Kode saham wajib diisi."}, status_code=400)
    try:
        market = get_market_data(force=False)
        stock = next((x for x in market["stocks"] if x["ticker"] == t), None)
        yf = fetch_yahoo_profile(t, stock_obj=stock)
        return {"ticker": t, "market": stock, "profile": yf}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/news")
def stock_news(ticker: str = "IHSG"):
    t = (ticker or "IHSG").upper().strip()
    try:
        market = get_market_data(force=False)
        stock = next((x for x in market["stocks"] if x["ticker"] == t), None)
        q = "IHSG pasar saham Indonesia BEI" if t in ("IHSG", "ALL", "") else f"saham {t} BEI Indonesia"

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            f_news = ex.submit(fetch_google_news_id, q, 10)
            f_prof = ex.submit(fetch_yahoo_profile, t, stock) if (stock and t not in ("IHSG", "ALL")) else None
            news_items = f_news.result()
            prof = f_prof.result() if f_prof else {}

        pos = sum(1 for n in news_items if n["sentiment"] == "Positif")
        neg = sum(1 for n in news_items if n["sentiment"] == "Negatif")
        net = sum(1 for n in news_items if n["sentiment"] == "Netral")

        # Daftar emiten dividen tertinggi (ISSI/IDX)
        div_hunters = sorted(
            [x for x in market["stocks"] if x["div_yield"] >= 3.0 and x["value_traded_b"] >= 0.5],
            key=lambda x: x["div_yield"],
            reverse=True,
        )[:15]

        return {
            "ticker": t,
            "news": news_items,
            "sentiment_stats": {"positif": pos, "negatif": neg, "netral": net},
            "calendar": prof.get("calendar") if prof else {},
            "div_hunters": [
                {"ticker": x["ticker"], "name": x["name"], "close": x["close"], "div_yield": x["div_yield"], "is_issi": x["is_issi"], "alpha_score": x["alpha_score"], "pe": x["pe"]}
                for x in div_hunters
            ],
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/compare")
def compare_stocks(tickers: str = "BRIS,TLKM,ADRO"):
    t_list = [t.strip().upper() for t in tickers.split(",") if t.strip()][:3]
    if not t_list:
        return JSONResponse({"error": "Minimal pilih 1 saham."}, status_code=400)
    try:
        market = get_market_data(force=False)
        by_ticker = {x["ticker"]: x for x in market["stocks"]}
        items = [by_ticker[t] for t in t_list if t in by_ticker]

        series = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            futs = {t: ex.submit(fetch_yf_ohlcv, t, "6mo") for t in t_list}
            for t, fut in futs.items():
                try:
                    bars = fut.result()
                    if bars:
                        base = bars[0]["close"]
                        series[t] = [{"date": b["date"], "idx": round((b["close"] / base) * 100, 2), "close": round(b["close"], 0)} for b in bars[::max(1, len(bars) // 70)]]
                    else:
                        series[t] = []
                except Exception:
                    series[t] = []

        return {"tickers": t_list, "stocks": items, "series": series}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/backtest")
def backtest(ticker: str = "BRIS", strategy: str = "BREAKOUT", range_str: str = "1y"):
    t = (ticker or "BRIS").upper().strip()
    strat = (strategy or "BREAKOUT").upper().strip()
    rng = range_str if range_str in ("6mo", "1y", "2y") else "1y"
    try:
        bars = fetch_yf_ohlcv(t, rng)
        sim = run_backtest_sim(bars, strat)
        if "error" in sim:
            return JSONResponse(sim, status_code=400)
        return {"ticker": t, "strategy": strat, "range": rng, **sim}
    except Exception as e:
        return JSONResponse({"error": f"Gagal ambil data historis {t}: {e}"}, status_code=500)


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

        # Ambil 3 sumber tambahan secara paralel (Historis 6Bln + Kepemilikan/Kalender + Berita ID)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            f_ohlcv = ex.submit(fetch_yf_ohlcv, ticker, "6mo")
            f_prof = ex.submit(fetch_yahoo_profile, ticker, s)
            f_news = ex.submit(fetch_google_news_id, f"saham {ticker} BEI", 6)

            try:
                hist_ctx = compute_historical_context(f_ohlcv.result())
            except Exception:
                hist_ctx = {"available": False}
            try:
                prof_ctx = f_prof.result()
            except Exception:
                prof_ctx = {}
            try:
                news_items = f_news.result()
            except Exception:
                news_items = []

        report = build_quant_ai_report(s, stocks, hist_ctx, prof_ctx, news_items, question)
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


@app.post("/api/telegram-send")
async def telegram_send(request: Request):
    try:
        body = await request.json()
        token = (body.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN", "")).strip()
        chat_id = (body.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID", "")).strip()
        only_issi = bool(body.get("only_issi", True))
        min_score = int(body.get("min_score", 70))
        if not token or not chat_id:
            return JSONResponse({"error": "Bot Token dan Chat ID Telegram wajib diisi."}, status_code=400)

        market = get_market_data(force=True)
        picks = [
            x for x in market["stocks"]
            if (not only_issi or x["is_issi"])
            and x["value_traded_b"] >= 1.0
            and x["alpha_score"] >= min_score
            and x["signal_code"] in ("STRONG_BUY", "BUY_BREAKOUT", "BOW")
        ][:8]

        if not picks:
            msg = f"📊 <b>ALPHA IDX ALERT</b> ({market['updated_at']})\nBelum ada sinyal di atas Skor {min_score} saat ini."
        else:
            lines = [f"🚨 <b>ALPHA IDX SNIPER ALERT</b>\n🕒 {market['updated_at']}\nFilter: {'☪ ISSI Syariah' if only_issi else 'Semua IHSG'} • Skor ≥ {min_score}\n"]
            for x in picks:
                p = x["plan"]
                lines.append(
                    f"• <b>{x['ticker']}</b> ({x['signal']} • Skor {x['alpha_score']})\n"
                    f"  Harga: Rp {int(x['close']):,} ({x['change']:+.2f}%) | RVOL {x['rvol']}x\n"
                    f"  Beli: {p['entry_low']:,}–{p['entry_high']:,} | SL: {p['stop_loss']:,} | TP1: {p['tp1']:,}"
                )
            msg = "\n".join(lines)

        res = _send_telegram_msg(token, chat_id, msg)
        if not res.get("ok"):
            return JSONResponse({"error": res.get("description", "Gagal kirim ke Telegram")}, status_code=400)
        return {"sent": True, "count": len(picks), "preview": msg}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/telegram-cron")
def telegram_cron(only_issi: int = 1, min_score: int = 74):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return JSONResponse({"error": "Set TELEGRAM_BOT_TOKEN & TELEGRAM_CHAT_ID di Vercel Environment Variables."}, status_code=400)
    try:
        market = get_market_data(force=True)
        picks = [
            x for x in market["stocks"]
            if (only_issi == 0 or x["is_issi"])
            and x["value_traded_b"] >= 1.0
            and x["alpha_score"] >= min_score
            and x["signal_code"] in ("STRONG_BUY", "BUY_BREAKOUT")
        ][:6]
        if not picks:
            return {"sent": False, "reason": "Tidak ada sinyal baru yang memenuhi syarat."}
        lines = [f"🚨 <b>ALPHA IDX AUTO-ALERT</b> ({market['updated_at']})\n"]
        for x in picks:
            p = x["plan"]
            lines.append(f"• <b>{x['ticker']}</b> Skor {x['alpha_score']} | Beli {p['entry_low']:,}–{p['entry_high']:,} | SL {p['stop_loss']:,} | TP1 {p['tp1']:,}")
        _send_telegram_msg(token, chat_id, "\n".join(lines))
        return {"sent": True, "count": len(picks)}
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
```

---

Setelah Anda commit **`index.py`** di GitHub, balas saja **`lanjut file 2`** — nanti saya langsung kirimkan **`react_ui.html`** yang lengkap dengan kesembilan menu tersebut!
Ini dia **File 2 (`react_ui.html`)** yang lengkap dengan **kesembilan menu** dalam tampilan terstruktur dan bersih, **Analisa AI 4 Sumber**, dan **tanpa Widget Profil TradingView**.

### Cara Memasangnya di GitHub:
1. Buka **`react_ui.html`** di GitHub → klik ikon pensil (**Edit**).
2. Tekan **`Ctrl + A`** → hapus semua isi lama → **Copy & Paste** seluruh kode di bawah ini → klik **Commit changes**.
3. Tunggu ±30 detik di dashboard Vercel sampai statusnya **`Ready`**, lalu buka link web Anda dengan **`Ctrl + Shift + R`**.

---

### File 2: `react_ui.html`

```html
<!DOCTYPE html>
<html lang="id" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="google" content="notranslate" />
  <title>ALPHA IDX • Pro Terminal IHSG & ISSI</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
  <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <style>
    body { background: #070b14; color: #e2e8f0; font-family: 'Plus Jakarta Sans', sans-serif; }
    .font-mono { font-family: 'JetBrains Mono', monospace; }
    .glass { background: rgba(15, 23, 42, 0.82); backdrop-filter: blur(14px); border: 1px solid rgba(148, 163, 184, 0.14); }
    ::-webkit-scrollbar { width: 7px; height: 7px; }
    ::-webkit-scrollbar-track { background: #0b1120; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 99px; }
  </style>
</head>
<body>
  <div id="root"></div>

  <script type="text/babel">
    const { useState, useEffect, useMemo, useRef } = React;
    const fmtRp = (n) => (n != null && !isNaN(n) ? "Rp " + Math.round(Number(n)).toLocaleString("id-ID") : "-");

    // ================= TRADINGVIEW WIDGETS =================
    function TickerTape() {
      const ref = useRef(null);
      useEffect(() => {
        const host = ref.current;
        if (!host || host.childElementCount > 0) return;
        const wrap = document.createElement("div");
        wrap.className = "tradingview-widget-container";
        const w = document.createElement("div");
        w.className = "tradingview-widget-container__widget";
        wrap.appendChild(w);
        const s = document.createElement("script");
        s.type = "text/javascript";
        s.src = "https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js";
        s.async = true;
        s.text = JSON.stringify({
          symbols: [
            { description: "IHSG", proName: "IDX:COMPOSITE" },
            { description: "BRIS", proName: "IDX:BRIS" },
            { description: "TLKM", proName: "IDX:TLKM" },
            { description: "ADRO", proName: "IDX:ADRO" },
            { description: "AMMN", proName: "IDX:AMMN" },
            { description: "ANTM", proName: "IDX:ANTM" },
            { description: "ASII", proName: "IDX:ASII" },
            { description: "ICBP", proName: "IDX:ICBP" },
            { description: "PGEO", proName: "IDX:PGEO" },
          ],
          showSymbolLogo: true,
          isTransparent: true,
          displayMode: "adaptive",
          colorTheme: "dark",
          locale: "id",
        });
        wrap.appendChild(s);
        host.appendChild(wrap);
      }, []);
      return <div ref={ref} className="w-full bg-slate-950 border-b border-slate-800/80" />;
    }

    function TradingViewChart({ ticker, interval, expanded }) {
      const ref = useRef(null);
      useEffect(() => {
        if (!ticker || !ref.current) return;
        let timer = null;
        const mount = () => {
          if (!ref.current) return;
          if (typeof TradingView !== "undefined") {
            ref.current.innerHTML = "";
            new TradingView.widget({
              autosize: true,
              symbol: "IDX:" + ticker,
              interval: interval,
              timezone: "Asia/Jakarta",
              theme: "dark",
              style: "1",
              locale: "id",
              toolbar_bg: "#0f172a",
              enable_publishing: false,
              allow_symbol_change: true,
              studies: [
                { id: "MASimple@tv-basicstudies", inputs: { length: 20 } },
                { id: "MASimple@tv-basicstudies", inputs: { length: 50 } },
                "RSI@tv-basicstudies",
                "MACD@tv-basicstudies",
              ],
              container_id: "tv_react_chart",
            });
          } else {
            timer = setTimeout(mount, 250);
          }
        };
        mount();
        return () => timer && clearTimeout(timer);
      }, [ticker, interval, expanded]);
      return <div id="tv_react_chart" ref={ref} style={{ height: expanded ? "620px" : "460px" }} className="w-full bg-slate-950" />;
    }

    function TradingViewGauge({ ticker }) {
      const ref = useRef(null);
      useEffect(() => {
        if (!ticker || !ref.current) return;
        ref.current.innerHTML = "";
        const wrap = document.createElement("div");
        wrap.className = "tradingview-widget-container";
        wrap.style.height = "100%";
        wrap.style.width = "100%";
        const w = document.createElement("div");
        w.className = "tradingview-widget-container__widget";
        wrap.appendChild(w);
        const s = document.createElement("script");
        s.type = "text/javascript";
        s.src = "https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js";
        s.async = true;
        s.text = JSON.stringify({
          interval: "1D", width: "100%", isTransparent: true, height: "100%",
          symbol: "IDX:" + ticker, showIntervalTabs: true, displayMode: "multiple", locale: "id", colorTheme: "dark",
        });
        wrap.appendChild(s);
        ref.current.appendChild(wrap);
      }, [ticker]);
      return <div ref={ref} className="w-full h-[380px] bg-slate-950" />;
    }

    function TradingViewFinancialsWidget({ ticker }) {
      const ref = useRef(null);
      useEffect(() => {
        if (!ticker || !ref.current) return;
        ref.current.innerHTML = "";
        const wrap = document.createElement("div");
        wrap.className = "tradingview-widget-container";
        wrap.style.width = "100%";
        wrap.style.height = "640px";
        const w = document.createElement("div");
        w.className = "tradingview-widget-container__widget";
        w.style.width = "100%";
        w.style.height = "100%";
        wrap.appendChild(w);
        const s = document.createElement("script");
        s.type = "text/javascript";
        s.src = "https://s3.tradingview.com/external-embedding/embed-widget-financials.js";
        s.async = true;
        s.text = JSON.stringify({
          isTransparent: true, largeChartUrl: "", displayMode: "regular",
          width: "100%", height: "100%", colorTheme: "dark", symbol: "IDX:" + ticker, locale: "id",
        });
        wrap.appendChild(s);
        ref.current.appendChild(wrap);
      }, [ticker]);
      return <div ref={ref} style={{ width: "100%", height: "640px" }} className="bg-slate-950" />;
    }

    // ================= CUSTOM SVG CHARTS =================
    function RrgSectorChart({ sectors }) {
      if (!sectors || sectors.length === 0) return null;
      const W = 560, H = 320, PAD = 42;
      const maxX = Math.max(6, ...sectors.map((s) => Math.abs(s.avg_perf_1m || 0)));
      const maxY = Math.max(4, ...sectors.map((s) => Math.abs(s.avg_perf_w || 0)));
      const mapX = (v) => PAD + ((v + maxX) / (2 * maxX)) * (W - 2 * PAD);
      const mapY = (v) => H - PAD - ((v + maxY) / (2 * maxY)) * (H - 2 * PAD);
      const cx = mapX(0), cy = mapY(0);

      const qColor = { LEADING: "#34d399", WEAKENING: "#fbbf24", IMPROVING: "#38bdf8", LAGGING: "#fb7185" };

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-72 bg-slate-950/90 rounded-xl border border-slate-800">
          <rect x={cx} y={PAD} width={W - PAD - cx} height={cy - PAD} fill="rgba(16,185,129,0.08)" />
          <rect x={cx} y={cy} width={W - PAD - cx} height={H - PAD - cy} fill="rgba(245,158,11,0.07)" />
          <rect x={PAD} y={PAD} width={cx - PAD} height={cy - PAD} fill="rgba(56,189,248,0.07)" />
          <rect x={PAD} y={cy} width={cx - PAD} height={H - PAD - cy} fill="rgba(244,63,94,0.07)" />
          <line x1={PAD} y1={cy} x2={W - PAD} y2={cy} stroke="#475569" strokeDasharray="4 4" />
          <line x1={cx} y1={PAD} x2={cx} y2={H - PAD} stroke="#475569" strokeDasharray="4 4" />
          <text x={W - PAD - 6} y={PAD + 14} textAnchor="end" fill="#34d399" fontSize="10" fontWeight="bold">LEADING (Kuat & Naik)</text>
          <text x={W - PAD - 6} y={H - PAD - 6} textAnchor="end" fill="#fbbf24" fontSize="10" fontWeight="bold">WEAKENING (Melambat)</text>
          <text x={PAD + 6} y={PAD + 14} textAnchor="start" fill="#38bdf8" fontSize="10" fontWeight="bold">IMPROVING (Mulai Bangkit)</text>
          <text x={PAD + 6} y={H - PAD - 6} textAnchor="start" fill="#fb7185" fontSize="10" fontWeight="bold">LAGGING (Lemah)</text>
          {sectors.map((s) => {
            const px = mapX(s.avg_perf_1m), py = mapY(s.avg_perf_w);
            const c = qColor[s.quadrant] || "#94a3b8";
            return (
              <g key={s.sector}>
                <circle cx={px} cy={py} r={Math.min(12, Math.max(5, s.avg_alpha / 10))} fill={c} fillOpacity="0.85" stroke="#0f172a" strokeWidth="1.5" />
                <text x={px} y={py - 9} textAnchor="middle" fill="#e2e8f0" fontSize="9" fontWeight="600">{s.sector.split(" ")[0]}</text>
              </g>
            );
          })}
        </svg>
      );
    }

    function CompareLineChart({ series, tickers }) {
      const colors = ["#10b981", "#38bdf8", "#f59e0b"];
      const allVals = tickers.flatMap((t) => (series[t] || []).map((p) => p.idx));
      if (allVals.length < 2) {
        return <div className="h-64 flex items-center justify-center text-xs text-slate-400">Data grafik historis belum tersedia.</div>;
      }
      const W = 680, H = 260, PAD = 34;
      const minV = Math.min(...allVals), maxV = Math.max(...allVals);
      const span = Math.max(1, maxV - minV);

      return (
        <div className="space-y-2">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-64 bg-slate-950/90 rounded-xl border border-slate-800">
            <line x1={PAD} y1={H - PAD - ((100 - minV) / span) * (H - 2 * PAD)} x2={W - PAD} y2={H - PAD - ((100 - minV) / span) * (H - 2 * PAD)} stroke="#334155" strokeDasharray="4 4" />
            {tickers.map((t, idx) => {
              const pts = series[t] || [];
              if (pts.length < 2) return null;
              const d = pts.map((p, i) => {
                const x = PAD + (i / (pts.length - 1)) * (W - 2 * PAD);
                const y = H - PAD - ((p.idx - minV) / span) * (H - 2 * PAD);
                return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
              }).join(" ");
              return <path key={t} d={d} fill="none" stroke={colors[idx]} strokeWidth="2.5" />;
            })}
            <text x={PAD} y={18} fill="#94a3b8" fontSize="10">Basis = 100 (Performa 6 Bulan Terakhir)</text>
          </svg>
          <div className="flex flex-wrap gap-4 text-xs font-mono">
            {tickers.map((t, idx) => {
              const pts = series[t] || [];
              const last = pts.length ? (pts[pts.length - 1].idx - 100).toFixed(2) : "-";
              return (
                <span key={t} className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm inline-block" style={{ background: colors[idx] }} />
                  <b className="text-white">{t}</b> ({last !== "-" ? `${Number(last) > 0 ? "+" : ""}${last}%` : "-"})
                </span>
              );
            })}
          </div>
        </div>
      );
    }

    function EquityCurveSvg({ curve }) {
      if (!curve || curve.length < 2) {
        return <div className="h-56 flex items-center justify-center text-xs text-slate-400">Belum ada kurva ekuitas.</div>;
      }
      const W = 680, H = 230, PAD = 34;
      const vals = curve.map((c) => c.equity);
      const minV = Math.min(...vals), maxV = Math.max(...vals);
      const span = Math.max(0.5, maxV - minV);
      const pts = curve.map((c, i) => {
        const x = PAD + (i / (curve.length - 1)) * (W - 2 * PAD);
        const y = H - PAD - ((c.equity - minV) / span) * (H - 2 * PAD);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(" ");
      const lastEq = vals[vals.length - 1];
      const stroke = lastEq >= 100 ? "#10b981" : "#f43f5e";

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-56 bg-slate-950/90 rounded-xl border border-slate-800">
          <polyline fill="none" stroke={stroke} strokeWidth="2.5" points={pts} />
          <text x={PAD} y={18} fill="#94a3b8" fontSize="10">Modal Awal = 100 • Akhir = {lastEq.toFixed(2)} ({curve[0].date} s/d {curve[curve.length - 1].date})</text>
        </svg>
      );
    }

    // ================= VIEW: ROTASI SEKTOR =================
    function SectorRotationView({ onJumpTicker }) {
      const [data, setData] = useState(null);
      const [loading, setLoading] = useState(true);
      const [err, setErr] = useState("");

      const load = async () => {
        setLoading(true);
        setErr("");
        try {
          const r = await fetch("/api/sectors");
          const d = await r.json();
          if (d.error) throw new Error(d.error);
          setData(d);
        } catch (e) { setErr(e.message); }
        finally { setLoading(false); }
      };
      useEffect(() => { load(); }, []);

      const qBadge = (q) => {
        if (q === "LEADING") return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
        if (q === "WEAKENING") return "bg-amber-500/20 text-amber-300 border-amber-500/40";
        if (q === "IMPROVING") return "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
        return "bg-rose-500/20 text-rose-300 border-rose-500/40";
      };

      return (
        <div className="space-y-5">
          <div className="glass rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-extrabold text-white">🧭 Rotasi Sektor & Heatmap IHSG (RRG Quadrant)</h2>
              <p className="text-xs text-slate-400">Mengetahui sektor mana yang sedang dimasuki dana institusi minggu ini</p>
            </div>
            <button onClick={load} className="h-9 px-4 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-xs font-extrabold text-slate-950">↻ Refresh Sektor</button>
          </div>
          {err && <div className="glass rounded-xl p-3 text-xs text-rose-300">{err}</div>}
          {loading && <div className="glass rounded-xl p-8 text-center text-xs text-cyan-300 animate-pulse">Menghitung rotasi seluruh sektor BEI...</div>}
          {data && !loading && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
                <div className="lg:col-span-6 glass rounded-2xl p-4 space-y-3">
                  <div className="text-xs font-bold uppercase text-cyan-300">Kuadran Rotasi Sektor (1 Bulan vs 1 Minggu)</div>
                  <RrgSectorChart sectors={data.sectors} />
                </div>
                <div className="lg:col-span-6 glass rounded-2xl p-4 space-y-3">
                  <div className="text-xs font-bold uppercase text-emerald-300">Heatmap Kinerja Hari Ini per Sektor</div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                    {data.sectors.map((s) => {
                      const bg = s.avg_change >= 1 ? "bg-emerald-500/25 border-emerald-500/50" : s.avg_change > 0 ? "bg-emerald-500/10 border-emerald-500/30" : s.avg_change <= -1 ? "bg-rose-500/25 border-rose-500/50" : "bg-rose-500/10 border-rose-500/30";
                      return (
                        <div key={s.sector} className={`rounded-xl border p-2.5 ${bg}`}>
                          <div className="text-xs font-bold text-white truncate">{s.sector}</div>
                          <div className={`text-base font-extrabold font-mono mt-0.5 ${s.avg_change >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                            {s.avg_change > 0 ? "+" : ""}{s.avg_change}%
                          </div>
                          <div className="text-[10px] text-slate-300">Skor α: {s.avg_alpha} • Val {s.total_val_b}M</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="glass rounded-2xl p-4 space-y-3">
                <div className="text-xs font-bold uppercase text-slate-300">Daftar Sektor & Saham Pemimpin (Klik Saham untuk Buka Chart)</div>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {data.sectors.map((s) => (
                    <div key={s.sector} className="rounded-xl bg-slate-900/80 border border-slate-800 p-3.5 space-y-2.5">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="font-bold text-white text-sm">{s.sector}</div>
                          <div className="text-[11px] text-slate-400">{s.count} emiten ({s.issi_count} ISSI) • Avg RVOL {s.avg_rvol}x</div>
                        </div>
                        <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${qBadge(s.quadrant)}`}>{s.quadrant}</span>
                      </div>
                      <div className="flex gap-3 text-[11px] font-mono text-slate-300">
                        <span>1W: <b className={s.avg_perf_w >= 0 ? "text-emerald-400" : "text-rose-400"}>{s.avg_perf_w > 0 ? "+" : ""}{s.avg_perf_w}%</b></span>
                        <span>1M: <b className={s.avg_perf_1m >= 0 ? "text-emerald-400" : "text-rose-400"}>{s.avg_perf_1m > 0 ? "+" : ""}{s.avg_perf_1m}%</b></span>
                        <span>Skor: <b className="text-cyan-300">{s.avg_alpha}</b></span>
                      </div>
                      <div className="flex flex-wrap gap-1.5 pt-1 border-t border-slate-800">
                        {s.top_stocks.map((st) => (
                          <button key={st.ticker} onClick={() => onJumpTicker(st.ticker)} className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-emerald-500/20 border border-slate-700 text-[11px] font-mono text-white transition">
                            <b>{st.ticker}</b> <span className={st.change >= 0 ? "text-emerald-400" : "text-rose-400"}>{st.change > 0 ? "+" : ""}{st.change}%</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      );
    }

    // ================= VIEW: ANALISA AI 4 SUMBER =================
    function DeepAiView({ stock, allStocks, onSelectTicker, onBackToChart }) {
      const [report, setReport] = useState(null);
      const [loading, setLoading] = useState(false);
      const [err, setErr] = useState("");
      const [question, setQuestion] = useState("");
      const [apiKey, setApiKey] = useState(() => localStorage.getItem("alpha_idx_gemini_key") || "");
      const [showKeyBox, setShowKeyBox] = useState(false);

      const runAnalysis = async (customQ = "") => {
        if (!stock) return;
        setLoading(true);
        setErr("");
        try {
          const res = await fetch("/api/ai-analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ticker: stock.ticker, question: customQ, api_key: apiKey }),
          });
          const data = await res.json();
          if (data.error) throw new Error(data.error);
          setReport(data);
        } catch (e) { setErr(e.message); }
        finally { setLoading(false); }
      };

      useEffect(() => { if (stock) runAnalysis(""); }, [stock && stock.ticker]);

      const saveKey = (val) => {
        setApiKey(val);
        localStorage.setItem("alpha_idx_gemini_key", val);
      };

      const quickPrompts = [
        "Apakah aman di-hold jangka menengah (1–3 bulan)?",
        "Strategi entry cicil & cut loss terbaik?",
        "Bandingkan dengan kompetitor satu sektornya!",
        "Cek risiko jebakan bandar / bull trap",
      ];

      if (!stock) return <div className="glass rounded-2xl p-8 text-center text-slate-400">Memuat data saham...</div>;

      return (
        <div className="space-y-5">
          <div className="glass rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center text-white text-lg font-extrabold">🤖</div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base lg:text-lg font-extrabold text-white">AI Deep Equity Analyst (4 Sumber Data) • <span className="text-emerald-400 font-mono">IDX:{stock.ticker}</span></h2>
                  {stock.is_issi && <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">☪ ISSI</span>}
                </div>
                <p className="text-xs text-slate-400">{stock.name} • {stock.sector} • Rp {stock.close.toLocaleString("id-ID")} ({stock.change > 0 ? "+" : ""}{stock.change}%)</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select value={stock.ticker} onChange={(e) => onSelectTicker(e.target.value)} className="h-9 bg-slate-900 border border-slate-700 rounded-lg px-3 text-xs font-mono text-white">
                {allStocks.slice(0, 150).map((x) => <option key={x.ticker} value={x.ticker}>{x.ticker} — Skor {x.alpha_score} ({x.signal})</option>)}
              </select>
              <button onClick={() => setShowKeyBox(!showKeyBox)} className="h-9 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-violet-300">
                🔑 {apiKey ? "Gemini Key Aktif" : "Gemini Key (Opsional)"}
              </button>
              <button onClick={() => runAnalysis(question)} className="h-9 px-3.5 rounded-lg bg-gradient-to-r from-violet-500 to-cyan-500 text-xs font-extrabold text-white">⚡ Analisa Ulang</button>
              <button onClick={onBackToChart} className="h-9 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200">← Chart</button>
            </div>
          </div>

          {showKeyBox && (
            <div className="glass rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 border-violet-500/30">
              <div className="text-xs text-slate-300 max-w-2xl">
                <b className="text-violet-300">Opsional (Gemini LLM):</b> Tanpa key, Quant AI 4-Sumber tetap berjalan penuh. Tempel Gemini API Key gratis dari <i>aistudio.google.com</i> jika ingin narasi AI generatif ekstra:
              </div>
              <div className="flex items-center gap-2 flex-1 max-w-md">
                <input type="password" value={apiKey} onChange={(e) => saveKey(e.target.value)} placeholder="AIzaSy..." className="h-8 flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 text-xs font-mono text-white" />
                <button onClick={() => runAnalysis(question)} className="h-8 px-3 rounded-lg bg-violet-500 text-white text-xs font-bold">Terapkan</button>
              </div>
            </div>
          )}

          {err && <div className="glass rounded-xl p-4 border-rose-500/40 text-xs text-rose-300">Error AI: {err}</div>}
          {loading && <div className="glass rounded-2xl p-10 text-center text-sm text-cyan-300 animate-pulse">🤖 Menggabungkan data TradingView + Historis 6 Bulan + Kepemilikan/Insider + Berita Indonesia untuk IDX:{stock.ticker}...</div>}

          {report && !loading && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2 text-[11px]">
                <span className="text-slate-400 font-bold">Sumber Aktif:</span>
                {(report.sources_used || []).map((src) => (
                  <span key={src} className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-semibold">✓ {src}</span>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
                <div className="lg:col-span-8 space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="glass rounded-xl p-3.5 border-violet-500/30">
                      <div className="text-[10px] uppercase text-slate-400 font-bold">AI Conviction</div>
                      <div className="text-2xl font-extrabold font-mono text-violet-300 mt-1">{report.conviction}/100</div>
                      <div className="text-[11px] text-emerald-300 font-semibold">{stock.signal}</div>
                    </div>
                    <div className="glass rounded-xl p-3.5 border-cyan-500/30">
                      <div className="text-[10px] uppercase text-slate-400 font-bold">Horizon Cocok</div>
                      <div className="text-xs font-extrabold text-cyan-300 mt-1.5">{report.horizon}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">R:R 1 : {stock.plan.rr}</div>
                    </div>
                    <div className="glass rounded-xl p-3.5 border-emerald-500/30">
                      <div className="text-[10px] uppercase text-slate-400 font-bold">Rank Sektor</div>
                      <div className="text-xl font-extrabold font-mono text-emerald-400 mt-1">#{report.sector_context.rank}/{report.sector_context.total_peers}</div>
                      <div className="text-[10px] text-slate-400 truncate">{report.sector_context.sector}</div>
                    </div>
                    <div className="glass rounded-xl p-3.5 border-amber-500/30">
                      <div className="text-[10px] uppercase text-slate-400 font-bold">Sentimen Berita</div>
                      <div className={`text-xl font-extrabold mt-1 ${report.news_sentiment === "Positif" ? "text-emerald-400" : report.news_sentiment === "Negatif" ? "text-rose-400" : "text-amber-300"}`}>
                        {report.news_sentiment}
                      </div>
                      <div className="text-[10px] text-slate-400">{report.news_items.length} berita terkini</div>
                    </div>
                  </div>

                  <div className="glass rounded-2xl p-5 space-y-4">
                    <div>
                      <div className="text-xs font-bold uppercase text-cyan-400">1. Fase Tren Pasar (Weinstein / Wyckoff)</div>
                      <div className="text-sm font-extrabold text-white mt-1">{report.stage}</div>
                      <p className="text-xs text-slate-300 mt-1 leading-relaxed">{report.stage_desc}</p>
                    </div>
                    <div className="border-t border-slate-800 pt-3">
                      <div className="text-xs font-bold uppercase text-emerald-400">2. Order Flow, Akumulasi & Jejak Historis 6 Bulan</div>
                      <p className="text-xs text-slate-300 mt-1 leading-relaxed">{report.order_flow}</p>
                    </div>
                    <div className="border-t border-slate-800 pt-3">
                      <div className="text-xs font-bold uppercase text-amber-400">3. Audit Fundamental, Syariah & Struktur Kepemilikan</div>
                      <p className="text-xs text-slate-300 mt-1 leading-relaxed">{report.fund_audit}</p>
                    </div>
                    <div className="border-t border-slate-800 pt-3">
                      <div className="text-xs font-bold uppercase text-violet-400">4. Ringkasan Berita Media Ekonomi Indonesia</div>
                      <p className="text-xs text-slate-300 mt-1 leading-relaxed">{report.news_summary}</p>
                    </div>
                  </div>

                  <div className="glass rounded-2xl p-5 space-y-3">
                    <div className="text-xs font-bold uppercase text-slate-300">5. Playbook 3 Skenario Eksekusi</div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-3">
                        <div className="text-xs font-extrabold text-emerald-300">🟢 Bullish</div>
                        <p className="text-xs text-slate-200 mt-1 leading-relaxed">{report.scenarios.bullish}</p>
                      </div>
                      <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-3">
                        <div className="text-xs font-extrabold text-amber-300">🟡 Pullback</div>
                        <p className="text-xs text-slate-200 mt-1 leading-relaxed">{report.scenarios.base}</p>
                      </div>
                      <div className="rounded-xl bg-rose-500/10 border border-rose-500/30 p-3">
                        <div className="text-xs font-extrabold text-rose-300">🔴 Cut Loss</div>
                        <p className="text-xs text-slate-200 mt-1 leading-relaxed">{report.scenarios.bearish}</p>
                      </div>
                    </div>
                  </div>

                  <div className="glass rounded-2xl p-5 space-y-3 border-violet-500/30">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="text-xs font-bold uppercase text-violet-300">
                        6. Konsultasi AI {report.llm_used ? `(Gemini: ${report.llm_model})` : "(Quant 4-Source Engine)"}
                      </div>
                      {report.llm_error && <span className="text-[10px] text-amber-400">{report.llm_error}</span>}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {quickPrompts.map((qp) => (
                        <button key={qp} onClick={() => { setQuestion(qp); runAnalysis(qp); }} className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-violet-500/20 border border-slate-700 text-[11px] text-slate-200">{qp}</button>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => e.key === "Enter" && runAnalysis(question)} placeholder={`Tanya apa saja tentang ${stock.ticker}...`} className="h-9 flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 text-xs text-white" />
                      <button onClick={() => runAnalysis(question)} className="h-9 px-4 rounded-lg bg-violet-500 hover:bg-violet-400 text-xs font-bold text-white">Tanya AI</button>
                    </div>
                    <div className="rounded-xl bg-slate-950/90 border border-slate-800 p-4 text-xs text-slate-200 leading-relaxed whitespace-pre-line">{report.qa_answer}</div>
                  </div>
                </div>

                <div className="lg:col-span-4 space-y-4">
                  <div className="glass rounded-2xl p-4 space-y-2 border-rose-500/25">
                    <div className="text-xs font-bold uppercase text-rose-300">⚠️ Deteksi Risiko & Red Flags</div>
                    {report.risk_flags.map((rf, i) => <div key={i} className="text-xs text-slate-200 bg-slate-900/80 border border-slate-800 rounded-lg p-2.5">• {rf}</div>)}
                  </div>

                  {report.news_items.length > 0 && (
                    <div className="glass rounded-2xl p-4 space-y-2">
                      <div className="text-xs font-bold uppercase text-cyan-300">📰 Headline Berita {stock.ticker}</div>
                      {report.news_items.map((n, i) => (
                        <a key={i} href={n.link} target="_blank" rel="noopener noreferrer" className="block rounded-lg bg-slate-900/80 hover:bg-slate-800 border border-slate-800 p-2.5 transition">
                          <div className="text-xs font-semibold text-white leading-snug">{n.title}</div>
                          <div className="flex justify-between text-[10px] mt-1">
                            <span className="text-slate-400">{n.source}</span>
                            <span className={n.sentiment === "Positif" ? "text-emerald-400 font-bold" : n.sentiment === "Negatif" ? "text-rose-400 font-bold" : "text-slate-400"}>{n.sentiment}</span>
                          </div>
                        </a>
                      ))}
                    </div>
                  )}

                  <div className="glass rounded-2xl p-4 space-y-2.5">
                    <div className="text-xs font-bold uppercase text-emerald-300">🏆 Kompetitor ({report.sector_context.sector})</div>
                    {report.sector_context.top_peers.map((peer) => (
                      <button key={peer.ticker} onClick={() => onSelectTicker(peer.ticker)} className="w-full text-left rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800 p-2.5 flex justify-between items-center">
                        <div>
                          <div className="font-mono font-bold text-white text-sm">{peer.ticker} <span className="text-[10px] text-cyan-300">Skor {peer.alpha_score}</span></div>
                          <div className="text-[10px] text-slate-400">{peer.signal} • PER {peer.pe ?? "-"}x</div>
                        </div>
                        <div className="text-right font-mono">
                          <div className="text-xs font-bold text-white">Rp {peer.close.toLocaleString("id-ID")}</div>
                          <div className={`text-[11px] font-bold ${peer.change >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{peer.change > 0 ? "+" : ""}{peer.change}%</div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      );
    }

    // ================= VIEW: PROFIL & INSIDER (TANPA WIDGET PROFIL TV) =================
    function ProfileInsiderView({ stock, allStocks, onSelectTicker, onBackToChart }) {
      const [profData, setProfData] = useState(null);
      const [loading, setLoading] = useState(false);
      const [err, setErr] = useState("");

      const loadProfile = async (t) => {
        if (!t) return;
        setLoading(true);
        setErr("");
        try {
          const res = await fetch(`/api/profile?ticker=${encodeURIComponent(t)}`);
          const d = await res.json();
          if (d.error) throw new Error(d.error);
          setProfData(d);
        } catch (e) { setErr(e.message); }
        finally { setLoading(false); }
      };
      useEffect(() => { if (stock) loadProfile(stock.ticker); }, [stock && stock.ticker]);

      if (!stock) return <div className="glass rounded-2xl p-8 text-center text-slate-400">Memuat data saham...</div>;
      const p = profData && profData.profile ? profData.profile : null;
      const own = p && p.ownership ? p.ownership : {};
      const insPct = own.insiders_pct ?? 0, instPct = own.institutions_pct ?? 0, pubPct = own.public_float_pct ?? 0;

      return (
        <div className="space-y-5">
          <div className="glass rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-emerald-500 flex items-center justify-center text-slate-950 text-lg font-extrabold">🏢</div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base lg:text-lg font-extrabold text-white">Profil Emiten, Pemegang Saham & Insider • <span className="text-amber-300 font-mono">IDX:{stock.ticker}</span></h2>
                  {stock.is_issi && <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">☪ ISSI</span>}
                </div>
                <p className="text-xs text-slate-400">{stock.name} • {stock.sector} • Market Cap Rp {stock.mcap_t} Triliun</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select value={stock.ticker} onChange={(e) => onSelectTicker(e.target.value)} className="h-9 bg-slate-900 border border-slate-700 rounded-lg px-3 text-xs font-mono text-white">
                {allStocks.slice(0, 180).map((x) => <option key={x.ticker} value={x.ticker}>{x.ticker} — {x.name.slice(0, 26)}</option>)}
              </select>
              <a href={`https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/${stock.ticker}`} target="_blank" rel="noopener noreferrer" className="h-9 inline-flex items-center px-3 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-amber-300">🏛️ BEI ↗</a>
              <button onClick={() => loadProfile(stock.ticker)} className="h-9 px-3 rounded-lg bg-amber-500 hover:bg-amber-400 text-xs font-extrabold text-slate-950">↻ Refresh</button>
              <button onClick={onBackToChart} className="h-9 px-3 rounded-lg bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-200">← Chart</button>
            </div>
          </div>

          {err && <div className="glass rounded-xl p-3 text-xs text-rose-300">{err}</div>}

          <div className="glass rounded-2xl p-4 space-y-3">
            <div className="flex flex-wrap justify-between text-xs">
              <span className="font-bold uppercase text-amber-300">📊 Struktur Kepemilikan Saham & Free Float</span>
              <span className="font-mono text-slate-400">Saham Beredar: <b className="text-white">{own.shares_outstanding_fmt || "-"}</b> • Float: <b className="text-cyan-300">{own.float_shares_fmt || "-"}</b></span>
            </div>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="rounded-xl bg-slate-900/90 border border-amber-500/30 p-3"><div className="text-[11px] text-slate-400">Pengendali / Insider</div><div className="text-2xl font-extrabold font-mono text-amber-400 mt-1">{own.insiders_pct != null ? `${own.insiders_pct}%` : "-"}</div></div>
              <div className="rounded-xl bg-slate-900/90 border border-cyan-500/30 p-3"><div className="text-[11px] text-slate-400">Institusi / Fund</div><div className="text-2xl font-extrabold font-mono text-cyan-400 mt-1">{own.institutions_pct != null ? `${own.institutions_pct}%` : "-"}</div></div>
              <div className="rounded-xl bg-slate-900/90 border border-emerald-500/30 p-3"><div className="text-[11px] text-slate-400">Estimasi Publik / Float</div><div className="text-2xl font-extrabold font-mono text-emerald-400 mt-1">{own.public_float_pct != null ? `${own.public_float_pct}%` : "-"}</div></div>
              <div className="rounded-xl bg-slate-900/90 border border-slate-700 p-3"><div className="text-[11px] text-slate-400">Valuasi & Syariah</div><div className="text-sm font-mono font-bold text-white mt-1.5">PER {stock.pe ?? "-"}x • PBV {stock.pbv ?? "-"}x</div><div className="text-[11px] text-emerald-300">Debt/Asset: {stock.debt_asset_ratio != null ? `${stock.debt_asset_ratio}%` : "-"}</div></div>
            </div>
            {(own.insiders_pct != null || own.institutions_pct != null) && (
              <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden flex">
                <div style={{ width: `${insPct}%` }} className="bg-amber-400 h-full" />
                <div style={{ width: `${instPct}%` }} className="bg-cyan-400 h-full" />
                <div style={{ width: `${pubPct}%` }} className="bg-emerald-400 h-full" />
              </div>
            )}
          </div>

          {loading && <div className="glass rounded-xl p-6 text-center text-xs text-amber-300 animate-pulse">Mengambil data Direksi & Insider IDX:{stock.ticker}...</div>}

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
            <div className="xl:col-span-6 space-y-5">
              <div className="glass rounded-2xl p-4 space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="text-xs font-bold uppercase text-cyan-300">🏢 Tentang Perusahaan & Manajemen</div>
                  {p && p.website && <a href={p.website} target="_blank" rel="noopener noreferrer" className="text-xs text-emerald-400 hover:underline font-mono">{p.website} ↗</a>}
                </div>
                {p && p.address && <div className="text-[11px] text-slate-400">📍 {p.address} {p.employees ? `• 👥 ${Number(p.employees).toLocaleString("id-ID")} Karyawan` : ""}</div>}
                {p && p.summary && <p className="text-xs text-slate-200 leading-relaxed max-h-48 overflow-y-auto pr-1">{p.summary}</p>}
                {p && p.officers && p.officers.length > 0 && (
                  <div className="pt-2 border-t border-slate-800 space-y-2">
                    <div className="text-[11px] font-bold uppercase text-slate-300">👔 Jajaran Direksi & Komisaris</div>
                    <div className="overflow-x-auto max-h-56 overflow-y-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-800"><tr><th className="py-1.5">Nama</th><th className="py-1.5">Jabatan</th><th className="py-1.5 text-right">Usia</th></tr></thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {p.officers.map((o, i) => <tr key={i}><td className="py-1.5 font-semibold text-white">{o.name}</td><td className="py-1.5 text-slate-300">{o.title}</td><td className="py-1.5 text-right font-mono text-slate-400">{o.age ?? "-"}</td></tr>)}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>

              <div className="glass rounded-2xl p-4 space-y-3">
                <div className="text-xs font-bold uppercase text-emerald-300">📌 Ringkasan Statistik Live TradingView</div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
                  <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5"><div className="text-[10px] text-slate-400">Sektor / Industri</div><div className="font-semibold text-white mt-0.5">{stock.sector}</div><div className="text-[10px] text-slate-400 truncate">{stock.industry}</div></div>
                  <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5"><div className="text-[10px] text-slate-400">Market Cap</div><div className="font-mono font-bold text-white mt-0.5">Rp {stock.mcap_t} T</div><div className="text-[10px] text-cyan-300">Val: Rp {stock.value_traded_b} M</div></div>
                  <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5"><div className="text-[10px] text-slate-400">Rentang 52 Minggu</div><div className="font-mono font-bold text-white mt-0.5">{stock.low_52w?.toLocaleString("id-ID")} – {stock.high_52w?.toLocaleString("id-ID")}</div><div className="text-[10px] text-slate-400">1Bln: {stock.perf_1m > 0 ? "+" : ""}{stock.perf_1m}%</div></div>
                  <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5"><div className="text-[10px] text-slate-400">ROE / Net Margin</div><div className="font-mono font-bold text-emerald-400 mt-0.5">ROE {stock.roe ?? "-"}%</div><div className="text-[10px] text-slate-400">NPM: {stock.npm ?? "-"}%</div></div>
                  <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5"><div className="text-[10px] text-slate-400">Dividen Yield</div><div className="font-mono font-bold text-amber-300 mt-0.5">{stock.div_yield}%</div><div className="text-[10px] text-slate-400">{stock.is_issi ? "Syariah ISSI" : "Non-ISSI"}</div></div>
                  <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-2.5"><div className="text-[10px] text-slate-400">EMA20 / EMA200</div><div className="font-mono font-bold text-white mt-0.5">{stock.ema20.toLocaleString("id-ID")} / {stock.ema200.toLocaleString("id-ID")}</div><div className="text-[10px] text-cyan-300">ADX: {stock.adx}</div></div>
                </div>
              </div>
            </div>

            <div className="xl:col-span-6 space-y-5">
              <div className="glass rounded-2xl p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-xs font-bold uppercase text-emerald-300">🕵️ Aktivitas & Pemegang Insider</div>
                  {p && p.net_insider_activity && (
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-cyan-300">
                      Beli: {p.net_insider_activity.buy_count}x ({p.net_insider_activity.buy_shares}) • Jual: {p.net_insider_activity.sell_count}x ({p.net_insider_activity.sell_shares})
                    </span>
                  )}
                </div>
                {p && p.insider_holders && p.insider_holders.length > 0 && (
                  <div className="overflow-x-auto max-h-48 overflow-y-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-800"><tr><th className="py-1.5">Nama</th><th className="py-1.5">Relasi</th><th className="py-1.5 text-right">Saham</th><th className="py-1.5 text-right">Tanggal</th></tr></thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {p.insider_holders.map((h, i) => <tr key={i}><td className="py-1.5 font-semibold text-white">{h.name}</td><td className="py-1.5 text-slate-300">{h.relation}</td><td className="py-1.5 text-right font-mono text-amber-300">{h.shares}</td><td className="py-1.5 text-right font-mono text-slate-400">{h.date}</td></tr>)}
                      </tbody>
                    </table>
                  </div>
                )}
                <div className="pt-2 border-t border-slate-800">
                  <div className="text-[11px] font-bold text-slate-400 mb-1">Riwayat Transaksi Insider</div>
                  {p && p.insider_transactions && p.insider_transactions.length > 0 ? (
                    <div className="overflow-x-auto max-h-52 overflow-y-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-800"><tr><th className="py-1.5">Pelaku</th><th className="py-1.5">Transaksi</th><th className="py-1.5 text-right">Lembar</th><th className="py-1.5 text-right">Tanggal</th></tr></thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {p.insider_transactions.map((tx, i) => (
                            <tr key={i}><td className="py-1.5"><div className="font-semibold text-white">{tx.name}</div><div className="text-[10px] text-slate-400">{tx.relation}</div></td><td className="py-1.5 text-slate-200">{tx.text}</td><td className="py-1.5 text-right font-mono text-white">{tx.shares}</td><td className="py-1.5 text-right font-mono text-slate-400">{tx.date}</td></tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-xs text-slate-400 bg-slate-900/70 border border-slate-800 rounded-lg p-3">Belum ada transaksi insider tercatat di feed publik Yahoo Finance. Gunakan tombol <b>🏛️ BEI ↗</b> untuk keterbukaan resmi ≥5%.</div>
                  )}
                </div>
              </div>

              <div className="glass rounded-2xl p-4 space-y-3">
                <div className="text-xs font-bold uppercase text-cyan-300">🏛️ Top Pemegang Saham Institusi & ETF</div>
                {p && ((p.institutions && p.institutions.length > 0) || (p.funds && p.funds.length > 0)) ? (
                  <div className="overflow-x-auto max-h-60 overflow-y-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-800"><tr><th className="py-1.5">Institusi / Fund</th><th className="py-1.5 text-right">Porsi</th><th className="py-1.5 text-right">Lembar</th><th className="py-1.5 text-right">Tanggal</th></tr></thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {[...(p.institutions || []), ...(p.funds || [])].slice(0, 12).map((ins, i) => (
                          <tr key={i}><td className="py-1.5 font-semibold text-white">{ins.name}</td><td className="py-1.5 text-right font-mono text-cyan-300">{ins.pct}%</td><td className="py-1.5 text-right font-mono text-slate-200">{ins.shares}</td><td className="py-1.5 text-right font-mono text-slate-400">{ins.date}</td></tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-xs text-slate-400">Belum ada rincian institusi publik untuk emiten ini.</div>
                )}
              </div>
            </div>
          </div>

          <div className="glass rounded-2xl overflow-hidden">
            <div className="px-4 py-2.5 border-b border-slate-800 text-xs font-bold text-slate-300">📑 Laporan Keuangan Resmi TradingView (Laba Rugi, Neraca, Arus Kas • IDX:{stock.ticker})</div>
            <TradingViewFinancialsWidget ticker={stock.ticker} />
          </div>
        </div>
      );
    }

    // ================= VIEW: DUEL SAHAM =================
    function CompareStocksView({ allStocks, defaultTicker }) {
      const [t1, setT1] = useState(defaultTicker || "BRIS");
      const [t2, setT2] = useState("TLKM");
      const [t3, setT3] = useState("ADRO");
      const [data, setData] = useState(null);
      const [loading, setLoading] = useState(false);

      const runCompare = async () => {
        setLoading(true);
        try {
          const r = await fetch(`/api/compare?tickers=${encodeURIComponent([t1, t2, t3].filter(Boolean).join(","))}`);
          const d = await r.json();
          setData(d);
        } catch {}
        finally { setLoading(false); }
      };
      useEffect(() => { runCompare(); }, []);

      const topOpts = allStocks.slice(0, 200);
      const rows = [
        ["Harga Saat Ini", (s) => fmtRp(s.close)],
        ["Perubahan Hari Ini", (s) => `${s.change > 0 ? "+" : ""}${s.change}%`],
        ["Skor α Total", (s) => `${s.alpha_score}/100`],
        ["Rekomendasi", (s) => s.signal],
        ["Status Syariah ISSI", (s) => (s.is_issi ? "☪ YA (Lolos)" : "Tidak / Non-ISSI")],
        ["Utang / Aset (OJK ≤45%)", (s) => (s.debt_asset_ratio != null ? `${s.debt_asset_ratio}%` : "-")],
        ["PER / PBV", (s) => `${s.pe ?? "-"}x / ${s.pbv ?? "-"}x`],
        ["ROE / Net Margin", (s) => `${s.roe ?? "-"}% / ${s.npm ?? "-"}%`],
        ["Dividen Yield", (s) => `${s.div_yield}%`],
        ["RVOL / RSI / ADX", (s) => `${s.rvol}x / ${s.rsi} / ${s.adx}`],
        ["Area Beli", (s) => `${s.plan.entry_low.toLocaleString("id-ID")}–${s.plan.entry_high.toLocaleString("id-ID")}`],
        ["Stop Loss / TP1", (s) => `${s.plan.stop_loss.toLocaleString("id-ID")} / ${s.plan.tp1.toLocaleString("id-ID")}`],
        ["Risk : Reward", (s) => `1 : ${s.plan.rr}`],
      ];

      return (
        <div className="space-y-5">
          <div className="glass rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-extrabold text-white">⚖️ Duel Saham (Head-to-Head Compare)</h2>
              <p className="text-xs text-slate-400">Bandingkan valuasi, skor alpha, status syariah, dan kinerja 6 bulan hingga 3 saham sekaligus</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {[ [t1, setT1], [t2, setT2], [t3, setT3] ].map(([val, setter], idx) => (
                <select key={idx} value={val} onChange={(e) => setter(e.target.value)} className="h-9 bg-slate-900 border border-slate-700 rounded-lg px-2.5 text-xs font-mono text-white">
                  {topOpts.map((x) => <option key={x.ticker} value={x.ticker}>{x.ticker}</option>)}
                </select>
              ))}
              <button onClick={runCompare} className="h-9 px-4 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-xs font-extrabold text-slate-950">⚖️ Bandingkan</button>
            </div>
          </div>

          {loading && <div className="glass rounded-xl p-8 text-center text-xs text-cyan-300 animate-pulse">Memuat perbandingan 6 bulan...</div>}

          {data && !loading && (
            <>
              <div className="glass rounded-2xl p-4">
                <div className="text-xs font-bold uppercase text-cyan-300 mb-3">Grafik Perbandingan Performa 6 Bulan (Basis = 100)</div>
                <CompareLineChart series={data.series || {}} tickers={data.tickers || []} />
              </div>

              <div className="glass rounded-2xl overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-slate-300 uppercase text-[11px] border-b border-slate-800">
                    <tr>
                      <th className="py-3 px-4">Metrik Perbandingan</th>
                      {(data.stocks || []).map((s) => (
                        <th key={s.ticker} className="py-3 px-4 font-mono text-sm text-white">IDX:{s.ticker} <span className="block text-[10px] font-sans text-slate-400 font-normal">{s.sector}</span></th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {rows.map(([label, fn]) => (
                      <tr key={label} className="hover:bg-slate-800/40">
                        <td className="py-2.5 px-4 font-semibold text-slate-300">{label}</td>
                        {(data.stocks || []).map((s) => <td key={s.ticker} className="py-2.5 px-4 font-mono text-white">{fn(s)}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      );
    }

    // ================= VIEW: BACKTEST LAB =================
    function BacktestView({ allStocks, defaultTicker }) {
      const [ticker, setTicker] = useState(defaultTicker || "BRIS");
      const [strategy, setStrategy] = useState("BREAKOUT");
      const [rangeStr, setRangeStr] = useState("1y");
      const [res, setRes] = useState(null);
      const [loading, setLoading] = useState(false);
      const [err, setErr] = useState("");

      const runBt = async () => {
        setLoading(true);
        setErr("");
        try {
          const r = await fetch(`/api/backtest?ticker=${encodeURIComponent(ticker)}&strategy=${strategy}&range_str=${rangeStr}`);
          const d = await r.json();
          if (d.error) throw new Error(d.error);
          setRes(d);
        } catch (e) { setErr(e.message); }
        finally { setLoading(false); }
      };
      useEffect(() => { runBt(); }, []);

      return (
        <div className="space-y-5">
          <div className="glass rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-extrabold text-white">🧪 Backtest Lab (Uji Akurasi Strategi Historis)</h2>
              <p className="text-xs text-slate-400">Simulasi historis lengkap dengan biaya broker BEI 0,40% (0,15% beli + 0,25% jual)</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select value={ticker} onChange={(e) => setTicker(e.target.value)} className="h-9 bg-slate-900 border border-slate-700 rounded-lg px-3 text-xs font-mono text-white">
                {allStocks.slice(0, 180).map((x) => <option key={x.ticker} value={x.ticker}>{x.ticker}</option>)}
              </select>
              <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className="h-9 bg-slate-900 border border-slate-700 rounded-lg px-3 text-xs text-white">
                <option value="BREAKOUT">⚡ Squeeze / Volume Breakout</option>
                <option value="TREND">📈 Trend Following (EMA20/50)</option>
                <option value="REBOUND">🎯 RSI Oversold Rebound</option>
              </select>
              <select value={rangeStr} onChange={(e) => setRangeStr(e.target.value)} className="h-9 bg-slate-900 border border-slate-700 rounded-lg px-3 text-xs text-white">
                <option value="6mo">6 Bulan</option>
                <option value="1y">1 Tahun</option>
                <option value="2y">2 Tahun</option>
              </select>
              <button onClick={runBt} className="h-9 px-4 rounded-lg bg-gradient-to-r from-cyan-400 to-emerald-400 text-xs font-extrabold text-slate-950">▶ Jalankan Backtest</button>
            </div>
          </div>

          {err && <div className="glass rounded-xl p-3 text-xs text-rose-300">{err}</div>}
          {loading && <div className="glass rounded-xl p-8 text-center text-xs text-cyan-300 animate-pulse">Menjalankan simulasi historis...</div>}

          {res && !loading && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                <div className="glass rounded-xl p-3.5"><div className="text-[11px] text-slate-400">Win Rate</div><div className="text-2xl font-extrabold font-mono text-emerald-400 mt-1">{res.win_rate}%</div><div className="text-[10px] text-slate-500">{res.total_trades} transaksi</div></div>
                <div className="glass rounded-xl p-3.5"><div className="text-[11px] text-slate-400">Return Strategi</div><div className={`text-2xl font-extrabold font-mono mt-1 ${res.total_return_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{res.total_return_pct > 0 ? "+" : ""}{res.total_return_pct}%</div><div className="text-[10px] text-slate-500">Setelah fee BEI</div></div>
                <div className="glass rounded-xl p-3.5"><div className="text-[11px] text-slate-400">Buy & Hold</div><div className={`text-2xl font-extrabold font-mono mt-1 ${res.buy_hold_pct >= 0 ? "text-cyan-400" : "text-rose-400"}`}>{res.buy_hold_pct > 0 ? "+" : ""}{res.buy_hold_pct}%</div><div className="text-[10px] text-slate-500">Pembanding pasif</div></div>
                <div className="glass rounded-xl p-3.5"><div className="text-[11px] text-slate-400">Profit Factor</div><div className="text-2xl font-extrabold font-mono text-amber-300 mt-1">{res.profit_factor}x</div><div className="text-[10px] text-slate-500">Bagus jika &gt; 1.5x</div></div>
                <div className="glass rounded-xl p-3.5"><div className="text-[11px] text-slate-400">Max Drawdown</div><div className="text-2xl font-extrabold font-mono text-rose-400 mt-1">{res.max_drawdown_pct}%</div><div className="text-[10px] text-slate-500">Penurunan terdalam</div></div>
              </div>

              <div className="glass rounded-2xl p-4 space-y-2">
                <div className="text-xs font-bold uppercase text-cyan-300">Kurva Pertumbuhan Modal (Equity Curve)</div>
                <EquityCurveSvg curve={res.equity_curve} />
              </div>

              <div className="glass rounded-2xl overflow-x-auto">
                <div className="px-4 py-2.5 border-b border-slate-800 text-xs font-bold text-slate-300">Riwayat Simulasi Transaksi Terbaru</div>
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-[11px] uppercase text-slate-400 border-b border-slate-800">
                    <tr><th className="py-2 px-4">Tgl Beli</th><th className="py-2 px-4">Tgl Jual</th><th className="py-2 px-4 text-right">Harga Beli</th><th className="py-2 px-4 text-right">Harga Jual</th><th className="py-2 px-4 text-right">Hasil %</th><th className="py-2 px-4">Alasan Keluar</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {(res.trades || []).map((t, i) => (
                      <tr key={i}>
                        <td className="py-2 px-4 font-mono text-slate-300">{t.entry_date}</td>
                        <td className="py-2 px-4 font-mono text-slate-300">{t.exit_date}</td>
                        <td className="py-2 px-4 text-right font-mono text-white">{t.entry.toLocaleString("id-ID")}</td>
                        <td className="py-2 px-4 text-right font-mono text-white">{t.exit.toLocaleString("id-ID")}</td>
                        <td className={`py-2 px-4 text-right font-mono font-bold ${t.return_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{t.return_pct > 0 ? "+" : ""}{t.return_pct}%</td>
                        <td className="py-2 px-4 text-slate-300">{t.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      );
    }

    // ================= VIEW: BERITA, SENTIMEN & DIVIDEN =================
    function NewsDividendView({ allStocks, defaultTicker, onJumpTicker }) {
      const [ticker, setTicker] = useState(defaultTicker || "IHSG");
      const [data, setData] = useState(null);
      const [loading, setLoading] = useState(false);

      const loadNews = async (t) => {
        setLoading(true);
        try {
          const r = await fetch(`/api/news?ticker=${encodeURIComponent(t)}`);
          const d = await r.json();
          setData(d);
        } catch {}
        finally { setLoading(false); }
      };
      useEffect(() => { loadNews(ticker); }, []);

      return (
        <div className="space-y-5">
          <div className="glass rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-extrabold text-white">📅 Berita Ekonomi AI, Sentimen & Pemburu Dividen</h2>
              <p className="text-xs text-slate-400">Pantau berita pasar modal Indonesia terbaru, jadwal dividen/earnings, dan saham dividen tertinggi</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select value={ticker} onChange={(e) => { setTicker(e.target.value); loadNews(e.target.value); }} className="h-9 bg-slate-900 border border-slate-700 rounded-lg px-3 text-xs font-mono text-white">
                <option value="IHSG">🌐 Pasar IHSG Umum</option>
                {allStocks.slice(0, 150).map((x) => <option key={x.ticker} value={x.ticker}>{x.ticker} — {x.name.slice(0, 24)}</option>)}
              </select>
              <a href="https://www.idx.co.id/id/perusahaan-tercatat/kalender-korporasi" target="_blank" rel="noopener noreferrer" className="h-9 inline-flex items-center px-3 rounded-lg bg-slate-800 border border-slate-700 text-xs font-semibold text-amber-300">🏛️ Kalender BEI Resmi ↗</a>
              <button onClick={() => loadNews(ticker)} className="h-9 px-3.5 rounded-lg bg-emerald-500 text-xs font-extrabold text-slate-950">↻ Muat Ulang</button>
            </div>
          </div>

          {loading && <div className="glass rounded-xl p-8 text-center text-xs text-cyan-300 animate-pulse">Mengambil berita ekonomi Indonesia & jadwal dividen...</div>}

          {data && !loading && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
              <div className="lg:col-span-7 space-y-4">
                <div className="glass rounded-2xl p-4 space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="text-xs font-bold uppercase text-cyan-300">📰 Berita Ekonomi Terkini ({data.ticker})</div>
                    <div className="flex gap-2 text-[11px] font-mono">
                      <span className="text-emerald-400">Positif: {data.sentiment_stats?.positif ?? 0}</span>
                      <span className="text-slate-400">Netral: {data.sentiment_stats?.netral ?? 0}</span>
                      <span className="text-rose-400">Negatif: {data.sentiment_stats?.negatif ?? 0}</span>
                    </div>
                  </div>
                  <div className="space-y-2.5">
                    {(data.news || []).map((n, i) => (
                      <a key={i} href={n.link} target="_blank" rel="noopener noreferrer" className="block rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800 p-3 transition">
                        <div className="text-xs font-bold text-white leading-snug">{n.title}</div>
                        <div className="flex justify-between items-center text-[10px] mt-1.5">
                          <span className="text-slate-400">{n.source} • {n.published}</span>
                          <span className={`px-2 py-0.5 rounded font-bold ${n.sentiment === "Positif" ? "bg-emerald-500/20 text-emerald-300" : n.sentiment === "Negatif" ? "bg-rose-500/20 text-rose-300" : "bg-slate-700 text-slate-300"}`}>{n.sentiment}</span>
                        </div>
                      </a>
                    ))}
                    {(!data.news || data.news.length === 0) && <div className="text-xs text-slate-400">Tidak ada berita ditemukan untuk kata kunci ini.</div>}
                  </div>
                </div>
              </div>

              <div className="lg:col-span-5 space-y-4">
                {data.calendar && Object.keys(data.calendar).length > 0 && (
                  <div className="glass rounded-2xl p-4 space-y-2">
                    <div className="text-xs font-bold uppercase text-amber-300">📆 Jadwal Korporasi ({data.ticker})</div>
                    <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                      <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800"><span className="text-[10px] text-slate-400 block font-sans">Ex-Dividend Date</span>{data.calendar.ex_dividend || "-"}</div>
                      <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800"><span className="text-[10px] text-slate-400 block font-sans">Tanggal Bayar Dividen</span>{data.calendar.dividend_date || "-"}</div>
                      <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800"><span className="text-[10px] text-slate-400 block font-sans">Rilis Lap. Keuangan</span>{data.calendar.earnings_date || "-"}</div>
                      <div className="bg-slate-900 p-2.5 rounded-lg border border-slate-800"><span className="text-[10px] text-slate-400 block font-sans">Dividend Rate</span>{data.calendar.dividend_rate || "-"}</div>
                    </div>
                  </div>
                )}

                <div className="glass rounded-2xl p-4 space-y-3">
                  <div className="text-xs font-bold uppercase text-emerald-300">💰 Top 15 Saham Dividen Yield Tertinggi (Likuid)</div>
                  <div className="overflow-x-auto max-h-96 overflow-y-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-800"><tr><th className="py-1.5">Kode</th><th className="py-1.5 text-right">Harga</th><th className="py-1.5 text-right">Div Yield</th><th className="py-1.5 text-right">Skor α</th></tr></thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {(data.div_hunters || []).map((d) => (
                          <tr key={d.ticker} onClick={() => onJumpTicker(d.ticker)} className="cursor-pointer hover:bg-slate-800/60">
                            <td className="py-2 font-mono font-bold text-white">{d.ticker} {d.is_issi && <span className="text-[9px] text-emerald-400">☪</span>}</td>
                            <td className="py-2 text-right font-mono text-slate-200">{d.close.toLocaleString("id-ID")}</td>
                            <td className="py-2 text-right font-mono font-bold text-amber-300">{d.div_yield}%</td>
                            <td className="py-2 text-right font-mono text-cyan-300">{d.alpha_score}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      );
    }

    // ================= VIEW: JURNAL TRADING & ZAKAT SYARIAH =================
    function JournalZakatView({ stocks, onJumpTicker }) {
      const [trades, setTrades] = useState(() => {
        try { return JSON.parse(localStorage.getItem("alpha_idx_journal") || "[]"); }
        catch { return []; }
      });
      const [ticker, setTicker] = useState("BRIS");
      const [lots, setLots] = useState(10);
      const [buyPrice, setBuyPrice] = useState(2500);
      const [sl, setSl] = useState(2350);
      const [tp, setTp] = useState(2850);
      const [note, setNote] = useState("");
      const [cashRdn, setCashRdn] = useState(10000000);
      const [haulPass, setHaulPass] = useState(true);

      const priceMap = useMemo(() => {
        const m = {};
        stocks.forEach((s) => { m[s.ticker] = s; });
        return m;
      }, [stocks]);

      const saveTrades = (next) => {
        setTrades(next);
        localStorage.setItem("alpha_idx_journal", JSON.stringify(next));
      };

      const addTrade = () => {
        const t = ticker.trim().toUpperCase();
        if (!t || lots <= 0 || buyPrice <= 0) return;
        const item = { id: Date.now(), ticker: t, lots: Number(lots), buyPrice: Number(buyPrice), sl: Number(sl), tp: Number(tp), note, status: "OPEN", sellPrice: null, date: new Date().toISOString().slice(0, 10) };
        saveTrades([item, ...trades]);
        setNote("");
      };

      const closeTrade = (id, liveP) => {
        const input = prompt("Masukkan harga jual realisasi (Rp):", String(liveP || ""));
        if (!input) return;
        const sp = Number(input);
        if (isNaN(sp) || sp <= 0) return;
        saveTrades(trades.map((tr) => tr.id === id ? { ...tr, status: "CLOSED", sellPrice: sp } : tr));
      };

      const delTrade = (id) => saveTrades(trades.filter((tr) => tr.id !== id));

      const openTrades = trades.filter((t) => t.status === "OPEN");
      const closedTrades = trades.filter((t) => t.status === "CLOSED");

      let totalAssetOpen = 0, totalCostOpen = 0, nonHalalAlert = 0;
      openTrades.forEach((tr) => {
        const live = priceMap[tr.ticker];
        const curP = live ? live.close : tr.buyPrice;
        totalAssetOpen += tr.lots * 100 * curP;
        totalCostOpen += tr.lots * 100 * tr.buyPrice;
        if (live && !live.is_issi) nonHalalAlert += 1;
      });
      const unrealPnl = totalAssetOpen - totalCostOpen;

      let realPnl = 0, winCnt = 0;
      closedTrades.forEach((tr) => {
        const pnl = tr.lots * 100 * (tr.sellPrice - tr.buyPrice);
        realPnl += pnl;
        if (pnl > 0) winCnt += 1;
      });
      const winRate = closedTrades.length ? ((winCnt / closedTrades.length) * 100).toFixed(1) : "0";
      const totalWealth = totalAssetOpen + Number(cashRdn || 0);
      const zakatDue = haulPass ? Math.round(totalWealth * 0.025) : 0;

      return (
        <div className="space-y-5">
          <div className="glass rounded-2xl p-4">
            <h2 className="text-lg font-extrabold text-white">📓 Portofolio Live, Jurnal Trading & Kalkulator Zakat Saham</h2>
            <p className="text-xs text-slate-400">Data tersimpan aman di browser Anda & otomatis menghitung P&L menggunakan harga live TradingView</p>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="glass rounded-xl p-3.5"><div className="text-xs text-slate-400">Nilai Portofolio Live</div><div className="text-xl font-extrabold font-mono text-white mt-1">{fmtRp(totalAssetOpen)}</div></div>
            <div className="glass rounded-xl p-3.5"><div className="text-xs text-slate-400">Unrealized P&L</div><div className={`text-xl font-extrabold font-mono mt-1 ${unrealPnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{unrealPnl >= 0 ? "+" : ""}{fmtRp(unrealPnl)}</div></div>
            <div className="glass rounded-xl p-3.5"><div className="text-xs text-slate-400">Realized P&L ({closedTrades.length} trade)</div><div className={`text-xl font-extrabold font-mono mt-1 ${realPnl >= 0 ? "text-cyan-400" : "text-rose-400"}`}>{realPnl >= 0 ? "+" : ""}{fmtRp(realPnl)}</div></div>
            <div className="glass rounded-xl p-3.5"><div className="text-xs text-slate-400">Win Rate Jurnal</div><div className="text-xl font-extrabold font-mono text-amber-300 mt-1">{winRate}%</div></div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            <div className="lg:col-span-8 space-y-4">
              {/* Form Catat Posisi */}
              <div className="glass rounded-2xl p-4 space-y-3">
                <div className="text-xs font-bold uppercase text-emerald-300">+ Catat Posisi Beli Baru</div>
                <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
                  <input value={ticker} onChange={(e) => { const v = e.target.value.toUpperCase(); setTicker(v); if (priceMap[v]) { setBuyPrice(priceMap[v].close); setSl(priceMap[v].plan.stop_loss); setTp(priceMap[v].plan.tp1); } }} placeholder="Kode (BRIS)" className="h-9 bg-slate-950 border border-slate-700 rounded-lg px-2.5 text-xs font-mono text-white" />
                  <input type="number" value={lots} onChange={(e) => setLots(e.target.value)} placeholder="Lot" className="h-9 bg-slate-950 border border-slate-700 rounded-lg px-2.5 text-xs font-mono text-white" />
                  <input type="number" value={buyPrice} onChange={(e) => setBuyPrice(e.target.value)} placeholder="Harga Beli" className="h-9 bg-slate-950 border border-slate-700 rounded-lg px-2.5 text-xs font-mono text-white" />
                  <input type="number" value={sl} onChange={(e) => setSl(e.target.value)} placeholder="Cut Loss" className="h-9 bg-slate-950 border border-slate-700 rounded-lg px-2.5 text-xs font-mono text-rose-300" />
                  <input type="number" value={tp} onChange={(e) => setTp(e.target.value)} placeholder="Target TP" className="h-9 bg-slate-950 border border-slate-700 rounded-lg px-2.5 text-xs font-mono text-emerald-300" />
                  <button onClick={addTrade} className="h-9 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-xs font-extrabold text-slate-950">Simpan</button>
                </div>
                <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Catatan alasan entry (mis: Breakout RVOL 2x)..." className="w-full h-8 bg-slate-950 border border-slate-800 rounded-lg px-3 text-xs text-slate-200" />
              </div>

              {/* Tabel Open Positions */}
              <div className="glass rounded-2xl overflow-x-auto">
                <div className="px-4 py-2.5 border-b border-slate-800 text-xs font-bold text-slate-300">Posisi Aktif (Terhubung Harga Live)</div>
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900 text-[10px] uppercase text-slate-400 border-b border-slate-800">
                    <tr><th className="py-2 px-3">Saham</th><th className="py-2 px-3 text-right">Lot</th><th className="py-2 px-3 text-right">Beli / Live</th><th className="py-2 px-3 text-right">P&L Live</th><th className="py-2 px-3 text-right">SL / TP</th><th className="py-2 px-3 text-right">Aksi</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {openTrades.length === 0 && <tr><td colSpan="6" className="py-6 text-center text-slate-500">Belum ada posisi aktif. Tambahkan di atas!</td></tr>}
                    {openTrades.map((tr) => {
                      const live = priceMap[tr.ticker];
                      const cur = live ? live.close : tr.buyPrice;
                      const pnl = tr.lots * 100 * (cur - tr.buyPrice);
                      const pct = (((cur / tr.buyPrice) - 1) * 100).toFixed(2);
                      const hitSl = tr.sl > 0 && cur <= tr.sl;
                      const hitTp = tr.tp > 0 && cur >= tr.tp;
                      return (
                        <tr key={tr.id}>
                          <td className="py-2.5 px-3">
                            <button onClick={() => onJumpTicker(tr.ticker)} className="font-mono font-bold text-white hover:text-emerald-400">{tr.ticker}</button>
                            {live && !live.is_issi && <span className="ml-1.5 px-1 text-[9px] rounded bg-rose-500/20 text-rose-300">Non-ISSI!</span>}
                            {hitSl && <span className="ml-1.5 px-1 text-[9px] rounded bg-rose-500/30 text-rose-200 font-bold">KENA SL!</span>}
                            {hitTp && <span className="ml-1.5 px-1 text-[9px] rounded bg-emerald-500/30 text-emerald-200 font-bold">CAPAI TP!</span>}
                            <div className="text-[10px] text-slate-400">{tr.note || tr.date}</div>
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono text-white">{tr.lots}</td>
                          <td className="py-2.5 px-3 text-right font-mono"><span className="text-slate-400">{tr.buyPrice.toLocaleString("id-ID")}</span> → <b className="text-white">{cur.toLocaleString("id-ID")}</b></td>
                          <td className={`py-2.5 px-3 text-right font-mono font-bold ${pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>{pnl >= 0 ? "+" : ""}{fmtRp(pnl)} ({pct}%)</td>
                          <td className="py-2.5 px-3 text-right font-mono text-[11px]"><span className="text-rose-400">{tr.sl.toLocaleString("id-ID")}</span> / <span className="text-emerald-400">{tr.tp.toLocaleString("id-ID")}</span></td>
                          <td className="py-2.5 px-3 text-right space-x-1">
                            <button onClick={() => closeTrade(tr.id, cur)} className="px-2 py-1 rounded bg-cyan-500/20 text-cyan-300 text-[10px] font-bold">Tutup</button>
                            <button onClick={() => delTrade(tr.id)} className="px-2 py-1 rounded bg-rose-500/20 text-rose-300 text-[10px]">✕</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Kalkulator Zakat Saham Syariah */}
            <div className="lg:col-span-4 space-y-4">
              <div className="glass rounded-2xl p-4 space-y-3 border-emerald-500/30">
                <div className="text-xs font-bold uppercase text-emerald-300">☪ Kalkulator Zakat Saham (2,5%)</div>
                <p className="text-[11px] text-slate-400 leading-relaxed">Berdasarkan Fatwa MUI / BAZNAS, zakat saham perdagangan dikenakan 2,5% dari total nilai pasar saham + kas RDN jika mencapai Nishab (setara 85 gr emas) dan Haul 1 tahun.</p>
                <div>
                  <label className="text-[10px] text-slate-400 block">Saldo Kas Mengendap di RDN (Rp)</label>
                  <input type="number" value={cashRdn} step={1000000} onChange={(e) => setCashRdn(e.target.value)} className="w-full h-9 mt-1 bg-slate-950 border border-slate-700 rounded-lg px-3 text-xs font-mono text-white" />
                </div>
                <label className="flex items-center gap-2 text-xs text-slate-200 cursor-pointer">
                  <input type="checkbox" checked={haulPass} onChange={(e) => setHaulPass(e.target.checked)} className="accent-emerald-400" />
                  Sudah mencapai Nishab & Haul (1 Tahun)
                </label>
                <div className="rounded-xl bg-slate-900 border border-slate-800 p-3 space-y-1 text-xs font-mono">
                  <div className="flex justify-between"><span className="text-slate-400">Total Harta Saham+RDN:</span><span className="text-white font-bold">{fmtRp(totalWealth)}</span></div>
                  <div className="flex justify-between"><span className="text-emerald-300 font-bold">Zakat Wajib (2,5%):</span><span className="text-emerald-400 font-extrabold text-sm">{fmtRp(zakatDue)}</span></div>
                </div>
                {nonHalalAlert > 0 && (
                  <div className="rounded-lg bg-rose-500/15 border border-rose-500/30 p-2.5 text-[11px] text-rose-200">
                    ⚠️ Peringatan Syariah: Ada <b>{nonHalalAlert}</b> saham di posisi aktif Anda yang berstatus Non-ISSI. Pertimbangkan cleansing jika mendapat dividen dari saham tersebut.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      );
    }

    // ================= VIEW: ALERT TELEGRAM =================
    function TelegramAlertView({ stocks }) {
      const [token, setToken] = useState(() => localStorage.getItem("alpha_idx_tg_token") || "");
      const [chatId, setChatId] = useState(() => localStorage.getItem("alpha_idx_tg_chat") || "");
      const [onlyIssi, setOnlyIssi] = useState(true);
      const [minScore, setMinScore] = useState(70);
      const [status, setStatus] = useState("");
      const [preview, setPreview] = useState("");
      const [sending, setSending] = useState(false);

      const saveCfg = (t, c) => {
        setToken(t); setChatId(c);
        localStorage.setItem("alpha_idx_tg_token", t);
        localStorage.setItem("alpha_idx_tg_chat", c);
      };

      const sendAlert = async () => {
        setSending(true);
        setStatus("");
        try {
          const r = await fetch("/api/telegram-send", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ bot_token: token, chat_id: chatId, only_issi: onlyIssi, min_score: Number(minScore) }),
          });
          const d = await r.json();
          if (d.error) throw new Error(d.error);
          setStatus(`✅ Berhasil dikirim ke Telegram! (${d.count} saham sinyal kuat)`);
          setPreview(d.preview || "");
        } catch (e) { setStatus("❌ Gagal: " + e.message); }
        finally { setSending(false); }
      };

      const candidates = stocks.filter((s) => (!onlyIssi || s.is_issi) && s.value_traded_b >= 1 && s.alpha_score >= minScore && ["STRONG_BUY", "BUY_BREAKOUT", "BOW"].includes(s.signal_code)).slice(0, 8);
      const cronUrl = typeof window !== "undefined" ? `${window.location.origin}/api/telegram-cron?only_issi=${onlyIssi ? 1 : 0}&min_score=${minScore}` : "";

      return (
        <div className="space-y-5">
          <div className="glass rounded-2xl p-4">
            <h2 className="text-lg font-extrabold text-white">🔔 Bot Alert Telegram Otomatis (Sniper Jam Bursa)</h2>
            <p className="text-xs text-slate-400">Kirim sinyal saham terbaik langsung ke HP Anda lewat Bot Telegram pribadi</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            <div className="lg:col-span-6 glass rounded-2xl p-5 space-y-4">
              <div className="text-xs font-bold uppercase text-cyan-300">1. Konfigurasi Bot Telegram</div>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-slate-300 block mb-1">Bot Token (dari @BotFather)</label>
                  <input type="password" value={token} onChange={(e) => saveCfg(e.target.value, chatId)} placeholder="123456789:ABCdefGHI..." className="w-full h-9 bg-slate-950 border border-slate-700 rounded-lg px-3 text-xs font-mono text-white" />
                </div>
                <div>
                  <label className="text-xs text-slate-300 block mb-1">Chat ID Anda (dari @userinfobot)</label>
                  <input value={chatId} onChange={(e) => saveCfg(token, e.target.value)} placeholder="987654321" className="w-full h-9 bg-slate-950 border border-slate-700 rounded-lg px-3 text-xs font-mono text-white" />
                </div>
                <div className="flex flex-wrap gap-3 items-center">
                  <label className="flex items-center gap-2 text-xs text-emerald-300 font-bold cursor-pointer">
                    <input type="checkbox" checked={onlyIssi} onChange={(e) => setOnlyIssi(e.target.checked)} className="accent-emerald-400" />
                    ☪ Khusus ISSI Syariah
                  </label>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-slate-400">Minimal Skor α:</span>
                    <input type="number" value={minScore} min={50} max={95} onChange={(e) => setMinScore(e.target.value)} className="w-16 h-8 bg-slate-950 border border-slate-700 rounded-lg px-2 text-xs font-mono text-white" />
                  </div>
                </div>
                <button onClick={sendAlert} disabled={sending} className="w-full h-10 rounded-xl bg-gradient-to-r from-cyan-400 to-emerald-400 hover:brightness-110 text-xs font-extrabold text-slate-950 transition">
                  {sending ? "Mengirim ke Telegram..." : "🚀 Kirim Sinyal Sekarang ke Telegram"}
                </button>
                {status && <div className="text-xs font-semibold p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-white">{status}</div>}
                {preview && <pre className="text-[11px] font-mono bg-slate-950 border border-slate-800 p-3 rounded-xl text-emerald-300 whitespace-pre-wrap">{preview}</pre>}
              </div>
            </div>

            <div className="lg:col-span-6 space-y-4">
              <div className="glass rounded-2xl p-5 space-y-3">
                <div className="text-xs font-bold uppercase text-amber-300">2. Cara Buat Otomatis 24 Jam (Tiap 15 Menit)</div>
                <ol className="text-xs text-slate-300 space-y-2 list-decimal pl-4 leading-relaxed">
                  <li>Di Vercel Project Anda → masuk ke <b>Settings → Environment Variables</b>, tambahkan <code className="text-emerald-300">TELEGRAM_BOT_TOKEN</code> dan <code className="text-emerald-300">TELEGRAM_CHAT_ID</code>, lalu Redeploy 1x.</li>
                  <li>Daftar gratis di <b>cron-job.org</b> → buat Cronjob baru setiap 15 menit (pukul 09:00–16:00 WIB, Senin–Jumat).</li>
                  <li>Masukkan URL pemicu otomatis ini:
                    <div className="mt-1 p-2 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-cyan-300 break-all">{cronUrl}</div>
                  </li>
                </ol>
              </div>

              <div className="glass rounded-2xl p-4 space-y-2">
                <div className="text-xs font-bold uppercase text-emerald-300">Kandidat yang Akan Terkirim ({candidates.length} Saham)</div>
                {candidates.length === 0 ? (
                  <div className="text-xs text-slate-400">Belum ada saham dengan Skor ≥ {minScore}. Coba turunkan batas minimal skor.</div>
                ) : (
                  <div className="space-y-1.5">
                    {candidates.map((c) => (
                      <div key={c.ticker} className="flex justify-between text-xs font-mono bg-slate-900/80 border border-slate-800 rounded-lg px-3 py-2">
                        <span><b className="text-white">{c.ticker}</b> <span className="text-emerald-400">({c.signal} • {c.alpha_score})</span></span>
                        <span className="text-cyan-300">Beli {c.plan.entry_low.toLocaleString("id-ID")}–{c.plan.entry_high.toLocaleString("id-ID")}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      );
    }

    // ================= MAIN APP =================
    function App() {
      const [activePage, setActivePage] = useState("SCREENER");
      const [meta, setMeta] = useState({ updated_at: "-", total_scanned: 0, total_issi: 0, strong_buy_count: 0 });
      const [stocks, setStocks] = useState([]);
      const [loading, setLoading] = useState(true);
      const [error, setError] = useState("");
      const [preset, setPreset] = useState("ALL");
      const [onlyIssi, setOnlyIssi] = useState(true);
      const [minVal, setMinVal] = useState(1);
      const [search, setSearch] = useState("");
      const [sortKey, setSortKey] = useState("alpha_score");
      const [sortAsc, setSortAsc] = useState(false);
      const [selectedTicker, setSelectedTicker] = useState(null);
      const [interval, setIntervalTv] = useState("D");
      const [expanded, setExpanded] = useState(false);
      const [capital, setCapital] = useState(20000000);
      const [riskPct, setRiskPct] = useState(2);
      const [showIssiModal, setShowIssiModal] = useState(false);
      const [issiText, setIssiText] = useState("");
      const [watchlist, setWatchlist] = useState(() => {
        try { return JSON.parse(localStorage.getItem("alpha_idx_watchlist") || "[]"); }
        catch { return []; }
      });

      const fetchScan = async (force = false) => {
        setLoading(true);
        setError("");
        try {
          const res = await fetch("/api/scan" + (force ? "?force=1" : ""));
          const data = await res.json();
          if (data.error) throw new Error(data.error);
          setMeta({ updated_at: data.updated_at, total_scanned: data.total_scanned, total_issi: data.total_issi, strong_buy_count: data.strong_buy_count });
          setStocks(data.stocks || []);
        } catch (e) { setError(e.message); }
        finally { setLoading(false); }
      };

      useEffect(() => {
        fetchScan(false);
        const id = setInterval(() => fetchScan(false), 60000);
        return () => clearInterval(id);
      }, []);

      const openIssiModal = async () => {
        setShowIssiModal(true);
        try {
          const res = await fetch("/api/issi");
          const d = await res.json();
          setIssiText((d.tickers || []).join("\n"));
        } catch {}
      };

      const saveIssiList = async () => {
        const res = await fetch("/api/issi", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: issiText }) });
        const d = await res.json();
        if (d.error) { alert(d.error); return; }
        setShowIssiModal(false);
        fetchScan(true);
      };

      const toggleWatchlist = (e, ticker) => {
        e.stopPropagation();
        const next = watchlist.includes(ticker) ? watchlist.filter((t) => t !== ticker) : [...watchlist, ticker];
        setWatchlist(next);
        localStorage.setItem("alpha_idx_watchlist", JSON.stringify(next));
      };

      const jumpToTicker = (t) => {
        setSelectedTicker(t);
        setActivePage("SCREENER");
      };

      const filtered = useMemo(() => {
        const q = search.trim().toUpperCase();
        const list = stocks.filter((s) => {
          if (onlyIssi && !s.is_issi) return false;
          if (s.value_traded_b < minVal) return false;
          if (q && !s.ticker.includes(q) && !s.name.toUpperCase().includes(q)) return false;
          if (preset === "WATCHLIST") return watchlist.includes(s.ticker);
          if (preset === "SNIPER") return s.alpha_score >= 70;
          if (preset === "BANDAR") return s.rvol >= 1.35 && s.vwma_bull && s.pillars.smart_money >= 16;
          if (preset === "BREAKOUT") return s.is_breakout || (s.is_squeeze && s.alpha_score >= 60);
          if (preset === "VALUE") return s.pe != null && s.pe > 0 && s.pe <= 18 && (s.roe == null || s.roe >= 10) && s.alpha_score >= 55;
          if (preset === "REBOUND") return s.is_rebound || (s.rsi <= 42 && s.macd_bull);
          return true;
        });

        return [...list].sort((a, b) => {
          let va = a[sortKey], vb = b[sortKey];
          if (typeof va === "string") return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
          va = va ?? -999999; vb = vb ?? -999999;
          return sortAsc ? va - vb : vb - va;
        });
      }, [stocks, onlyIssi, minVal, search, preset, watchlist, sortKey, sortAsc]);

      const selected = useMemo(() => stocks.find((s) => s.ticker === selectedTicker) || filtered[0] || stocks[0] || null, [stocks, filtered, selectedTicker]);
      const topAlerts = useMemo(() => stocks.filter((s) => (!onlyIssi || s.is_issi) && (s.signal_code === "STRONG_BUY" || s.signal_code === "BUY_BREAKOUT")).slice(0, 6), [stocks, onlyIssi]);

      const handleSort = (key) => {
        if (sortKey === key) setSortAsc(!sortAsc);
        else { setSortKey(key); setSortAsc(key === "ticker"); }
      };

      const exportCsv = () => {
        const header = "Ticker,ISSI,Close,Change%,AlphaScore,Signal,EntryLow,EntryHigh,SL,TP1,TP2,RR,RVOL,RSI,ValMiliar\n";
        const body = filtered.map((s) => [s.ticker, s.is_issi, s.close, s.change, s.alpha_score, `"${s.signal}"`, s.plan.entry_low, s.plan.entry_high, s.plan.stop_loss, s.plan.tp1, s.plan.tp2, s.plan.rr, s.rvol, s.rsi, s.value_traded_b].join(",")).join("\n");
        const blob = new Blob([header + body], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = "alpha_idx_screener.csv"; a.click();
      };

      const sigBadge = (code) => {
        if (code === "STRONG_BUY") return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
        if (code === "BUY_BREAKOUT") return "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
        if (code === "BOW") return "bg-sky-500/20 text-sky-300 border-sky-500/40";
        if (code === "SELL") return "bg-amber-500/20 text-amber-300 border-amber-500/40";
        if (code === "AVOID") return "bg-rose-500/20 text-rose-300 border-rose-500/40";
        return "bg-slate-700/50 text-slate-300 border-slate-600/40";
      };

      const posCalc = useMemo(() => {
        if (!selected) return null;
        const entry = selected.plan.entry_high, sl = selected.plan.stop_loss, tp1 = selected.plan.tp1;
        const rps = Math.max(1, entry - sl);
        const lots = Math.max(0, Math.min(Math.floor((capital * (riskPct / 100)) / (rps * 100)), Math.floor(capital / (entry * 100))));
        return { lots, val: lots * 100 * entry, profit: lots * 100 * (tp1 - entry), loss: lots * 100 * rps };
      }, [selected, capital, riskPct]);

      const presets = [
        ["ALL", "🌐 Semua"], ["WATCHLIST", `⭐ Watchlist (${watchlist.length})`], ["SNIPER", "🏆 Top Alpha (≥70)"],
        ["BANDAR", "🐋 Bandar VPA"], ["BREAKOUT", "⚡ Squeeze Breakout"], ["VALUE", "💎 Value GARP"], ["REBOUND", "🎯 Rebound/BOW"],
      ];

      const navGroups = [
        {
          group: "Pasar",
          tabs: [
            { id: "SCREENER", label: "📊 Screener & Chart", activeCls: "bg-emerald-500 text-slate-950" },
            { id: "SECTORS", label: "🧭 Rotasi Sektor", activeCls: "bg-cyan-400 text-slate-950" },
            { id: "NEWS", label: "📅 Berita & Dividen", activeCls: "bg-amber-400 text-slate-950" },
          ],
        },
        {
          group: "Riset Saham",
          tabs: [
            { id: "AI", label: "🤖 Analisa AI (4 Sumber)", activeCls: "bg-gradient-to-r from-violet-500 to-cyan-500 text-white" },
            { id: "PROFILE", label: "🏢 Profil & Insider", activeCls: "bg-gradient-to-r from-amber-400 to-emerald-400 text-slate-950" },
            { id: "COMPARE", label: "⚖️ Duel Saham", activeCls: "bg-sky-400 text-slate-950" },
            { id: "BACKTEST", label: "🧪 Backtest Lab", activeCls: "bg-purple-400 text-slate-950" },
          ],
        },
        {
          group: "Eksekusi",
          tabs: [
            { id: "JOURNAL", label: "📓 Jurnal & Zakat", activeCls: "bg-emerald-400 text-slate-950" },
            { id: "TELEGRAM", label: "🔔 Alert Telegram", activeCls: "bg-cyan-500 text-slate-950" },
          ],
        },
      ];

      return (
        <div className="min-h-screen flex flex-col">
          <TickerTape />

          {/* Header Bersih + Sub-Navigasi Terkelompok */}
          <header className="border-b border-slate-800/80 bg-slate-950/85 sticky top-0 z-30 backdrop-blur-xl">
            <div className="max-w-[1800px] mx-auto px-4 lg:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center text-slate-950 font-extrabold text-lg shadow-lg shadow-emerald-500/20">α</div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-lg font-extrabold text-white tracking-tight">ALPHA <span className="text-emerald-400">IDX</span> PRO</h1>
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">IHSG & ISSI TERMINAL</span>
                  </div>
                  <p className="text-[11px] text-slate-400">Quant Screener • Multi-Source AI • Rotasi Sektor • Backtest • Jurnal Syariah</p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className={`h-8 inline-flex items-center text-xs font-mono px-3 rounded-lg border ${error ? "bg-rose-500/10 border-rose-500/30 text-rose-300" : "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"}`}>
                  {loading ? "Memuat data..." : (error ? error : `LIVE • ${meta.updated_at}`)}
                </span>
                <button onClick={openIssiModal} className="h-8 px-3 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-emerald-300">☪ ISSI</button>
                <button onClick={exportCsv} className="h-8 px-3 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200">📥 CSV</button>
                <button onClick={() => fetchScan(true)} className="h-8 px-3.5 text-xs font-extrabold rounded-lg bg-gradient-to-r from-emerald-400 to-cyan-400 text-slate-950">↻ Scan Live</button>
              </div>
            </div>

            {/* Sub-Navbar 9 Menu yang Rapi & Terkelompok */}
            <div className="border-t border-slate-800/80 bg-slate-900/50">
              <div className="max-w-[1800px] mx-auto px-4 lg:px-6 py-2 flex flex-wrap items-center gap-3 overflow-x-auto">
                {navGroups.map((grp, gIdx) => (
                  <div key={grp.group} className="flex items-center gap-1.5">
                    {gIdx > 0 && <div className="h-5 w-px bg-slate-700/70 mx-1 hidden sm:block" />}
                    <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mr-1 hidden md:inline">{grp.group}:</span>
                    {grp.tabs.map((tb) => (
                      <button
                        key={tb.id}
                        onClick={() => setActivePage(tb.id)}
                        className={`h-8 px-3 rounded-lg text-xs font-bold whitespace-nowrap transition ${activePage === tb.id ? `${tb.activeCls} shadow` : "text-slate-300 hover:text-white hover:bg-slate-800/80"}`}
                      >
                        {tb.label}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          </header>

          <main className="flex-1 max-w-[1800px] w-full mx-auto p-4 lg:p-6 space-y-4">
            {activePage === "SECTORS" && <SectorRotationView onJumpTicker={jumpToTicker} />}
            {activePage === "AI" && <DeepAiView stock={selected} allStocks={filtered.length > 0 ? filtered : stocks} onSelectTicker={(t) => setSelectedTicker(t)} onBackToChart={() => setActivePage("SCREENER")} />}
            {activePage === "PROFILE" && <ProfileInsiderView stock={selected} allStocks={filtered.length > 0 ? filtered : stocks} onSelectTicker={(t) => setSelectedTicker(t)} onBackToChart={() => setActivePage("SCREENER")} />}
            {activePage === "COMPARE" && <CompareStocksView allStocks={stocks} defaultTicker={selected ? selected.ticker : "BRIS"} />}
            {activePage === "BACKTEST" && <BacktestView allStocks={stocks} defaultTicker={selected ? selected.ticker : "BRIS"} />}
            {activePage === "NEWS" && <NewsDividendView allStocks={stocks} defaultTicker={selected ? selected.ticker : "IHSG"} onJumpTicker={jumpToTicker} />}
            {activePage === "JOURNAL" && <JournalZakatView stocks={stocks} onJumpTicker={jumpToTicker} />}
            {activePage === "TELEGRAM" && <TelegramAlertView stocks={stocks} />}

            {activePage === "SCREENER" && (
              <>
                {topAlerts.length > 0 && (
                  <div className="glass rounded-xl px-4 py-2.5 flex flex-wrap items-center gap-2">
                    <span className="text-[11px] font-bold uppercase text-emerald-400 mr-1">🔥 Sinyal Terkuat:</span>
                    {topAlerts.map((a) => (
                      <button key={a.ticker} onClick={() => setSelectedTicker(a.ticker)} className="h-7 px-2.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/25 border border-emerald-500/30 text-xs font-mono text-white inline-flex items-center gap-1.5">
                        <span className="font-bold text-emerald-300">{a.ticker}</span>
                        <span className="text-[10px] text-slate-300">Skor {a.alpha_score}</span>
                      </button>
                    ))}
                  </div>
                )}

                <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <div className="glass rounded-xl p-3.5"><div className="text-xs text-slate-400">Emiten IDX</div><div className="text-2xl font-extrabold font-mono text-white mt-1">{meta.total_scanned}</div></div>
                  <div className="glass rounded-xl p-3.5"><div className="text-xs text-slate-400">Lolos ISSI Syariah</div><div className="text-2xl font-extrabold font-mono text-emerald-400 mt-1">{meta.total_issi}</div></div>
                  <div className="glass rounded-xl p-3.5"><div className="text-xs text-slate-400">Strong Buy / Breakout</div><div className="text-2xl font-extrabold font-mono text-cyan-400 mt-1">{meta.strong_buy_count}</div></div>
                  <div className="glass rounded-xl p-3.5"><div className="text-xs text-slate-400">Saham Terpilih</div><div className="text-2xl font-extrabold font-mono text-amber-400 mt-1">{selected ? selected.ticker : "-"}</div></div>
                </section>

                <section className="glass rounded-2xl p-3.5 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap gap-2">
                    {presets.map(([k, lbl]) => (
                      <button key={k} onClick={() => setPreset(k)} className={`h-8 px-3 rounded-lg text-xs inline-flex items-center transition ${preset === k ? "bg-emerald-500 text-slate-950 font-extrabold shadow-md shadow-emerald-500/20" : "bg-slate-800/90 text-slate-300 hover:bg-slate-700 border border-slate-700/60 font-semibold"}`}>{lbl}</button>
                    ))}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <label className="h-8 inline-flex items-center gap-2 px-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 cursor-pointer text-xs font-bold text-emerald-300">
                      <input type="checkbox" checked={onlyIssi} onChange={(e) => setOnlyIssi(e.target.checked)} className="accent-emerald-400" />
                      ☪ Khusus ISSI Syariah
                    </label>
                    <select value={minVal} onChange={(e) => setMinVal(Number(e.target.value))} className="h-8 bg-slate-900 border border-slate-700 rounded-lg px-2.5 text-xs text-slate-200">
                      <option value={0}>Semua Likuiditas</option>
                      <option value={1}>Transaksi ≥ Rp 1 Miliar</option>
                      <option value={5}>Transaksi ≥ Rp 5 Miliar</option>
                      <option value={20}>Transaksi ≥ Rp 20 Miliar</option>
                    </select>
                    <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Cari kode (BRIS, TLKM)..." className="h-8 bg-slate-900 border border-slate-700 rounded-lg px-3 text-xs text-white w-48" />
                  </div>
                </section>

                <section className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
                  <div className={`${expanded ? "xl:col-span-12 order-2" : "xl:col-span-7"} glass rounded-2xl overflow-hidden`}>
                    <div className="px-4 py-3 border-b border-slate-800 flex justify-between text-xs">
                      <span className="font-bold uppercase text-slate-300">Hasil Screening (<span className="text-emerald-400 font-mono">{filtered.length}</span> Saham)</span>
                      <span className="text-slate-400">Klik ★ untuk Watchlist • Klik baris untuk Chart</span>
                    </div>
                    <div className="overflow-x-auto max-h-[760px] overflow-y-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="bg-slate-900/95 sticky top-0 z-10 text-[11px] uppercase text-slate-400 border-b border-slate-800">
                          <tr>
                            <th className="py-2.5 px-3 cursor-pointer hover:text-white" onClick={() => handleSort("ticker")}>Saham</th>
                            <th className="py-2.5 px-2 text-right cursor-pointer hover:text-white" onClick={() => handleSort("close")}>Harga</th>
                            <th className="py-2.5 px-2 text-right cursor-pointer hover:text-white" onClick={() => handleSort("alpha_score")}>Skor α</th>
                            <th className="py-2.5 px-2">Rekomendasi</th>
                            <th className="py-2.5 px-2 text-right">Area Beli / SL</th>
                            <th className="py-2.5 px-2 text-right">TP1 / TP2</th>
                            <th className="py-2.5 px-2 text-right cursor-pointer hover:text-white" onClick={() => handleSort("rvol")}>RVOL / RSI</th>
                            <th className="py-2.5 px-3 text-right cursor-pointer hover:text-white" onClick={() => handleSort("value_traded_b")}>Val (M)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {filtered.slice(0, 200).map((s) => {
                            const isActive = selected && selected.ticker === s.ticker;
                            const isFav = watchlist.includes(s.ticker);
                            return (
                              <tr key={s.ticker} onClick={() => setSelectedTicker(s.ticker)} className={`cursor-pointer hover:bg-slate-800/60 transition ${isActive ? "bg-emerald-500/15 shadow-[inset_3px_0_0_#10b981]" : ""}`}>
                                <td className="py-2.5 px-3">
                                  <div className="flex items-center gap-1.5">
                                    <button onClick={(e) => toggleWatchlist(e, s.ticker)} className={`text-sm leading-none ${isFav ? "text-amber-400" : "text-slate-600 hover:text-amber-300"}`}>★</button>
                                    <span className="font-mono font-bold text-white text-sm">{s.ticker}</span>
                                    {s.is_issi && <span className="px-1 text-[9px] font-bold rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">ISSI</span>}
                                  </div>
                                  <div className="text-[10px] text-slate-400 truncate max-w-[140px] pl-5">{s.name}</div>
                                </td>
                                <td className="py-2.5 px-2 text-right font-mono">
                                  <div className="font-bold text-white">{s.close.toLocaleString("id-ID")}</div>
                                  <div className={`text-[11px] font-bold ${s.change > 0 ? "text-emerald-400" : s.change < 0 ? "text-rose-400" : "text-slate-300"}`}>{s.change > 0 ? "+" : ""}{s.change}%</div>
                                </td>
                                <td className="py-2.5 px-2 text-right font-mono font-extrabold text-white">{s.alpha_score}</td>
                                <td className="py-2.5 px-2"><span className={`px-2 py-0.5 rounded text-[10px] font-bold border whitespace-nowrap ${sigBadge(s.signal_code)}`}>{s.signal}</span></td>
                                <td className="py-2.5 px-2 text-right font-mono">
                                  <div className="text-cyan-300">{s.plan.entry_low.toLocaleString("id-ID")}–{s.plan.entry_high.toLocaleString("id-ID")}</div>
                                  <div className="text-rose-400 text-[10px]">SL {s.plan.stop_loss.toLocaleString("id-ID")}</div>
                                </td>
                                <td className="py-2.5 px-2 text-right font-mono">
                                  <div className="text-emerald-400">{s.plan.tp1.toLocaleString("id-ID")} (+{s.plan.tp1_pct}%)</div>
                                  <div className="text-amber-300 text-[10px]">TP2 {s.plan.tp2.toLocaleString("id-ID")}</div>
                                </td>
                                <td className="py-2.5 px-2 text-right font-mono">
                                  <div className={s.rvol >= 1.5 ? "text-cyan-300 font-bold" : "text-slate-300"}>{s.rvol}x</div>
                                  <div className="text-[10px] text-slate-400">RSI {s.rsi}</div>
                                </td>
                                <td className="py-2.5 px-3 text-right font-mono text-slate-300">{s.value_traded_b.toFixed(1)}M</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {selected && (
                    <div className={`${expanded ? "xl:col-span-12 order-1" : "xl:col-span-5 xl:sticky xl:top-28"} space-y-4`}>
                      <div className="glass rounded-2xl p-4 space-y-3">
                        <div className="flex justify-between items-start gap-2">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <h2 className="text-2xl font-extrabold font-mono text-white">IDX:{selected.ticker}</h2>
                              {selected.is_issi && <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">☪ ISSI</span>}
                              <span className={`px-2 py-0.5 text-[10px] font-bold rounded border ${sigBadge(selected.signal_code)}`}>{selected.signal}</span>
                            </div>
                            <p className="text-xs text-slate-400 mt-0.5">{selected.name} • {selected.sector}</p>
                          </div>
                          <div className="text-right">
                            <div className="text-2xl font-extrabold font-mono text-white">{fmtRp(selected.close)}</div>
                            <div class
