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

app = FastAPI()

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
            stage = "Stage 3 - Overextended / Rawan Profit Taking"
            stage_desc = f"Harga sudah jauh di atas EMA20 (Rp {e20:,}) dengan RSI {s['rsi']}. Tren masih naik, tetapi rawan koreksi sehat jangka pendek."
        else:
            stage = "Stage 2 - Markup / Uptrend Institusi"
            stage_desc = f"Formasi sempurna: Harga (Rp {c:,}) > EMA20 ({e20:,}) > EMA50 ({e50:,}) > EMA200 ({e200:,}). Zona terbaik mengikuti tren naik."
    elif c > e20 and e20 <= e50:
        stage = "Stage 1 -> 2 - Transisi Akumulasi ke Breakout"
        stage_desc = f"Harga mulai menembus EMA20 (Rp {e20:,}) dan bersiap membalikkan tren menengah (EMA50 Rp {e50:,})."
    elif c < e50 and e20 < e50:
        if s["is_rebound"]:
            stage = "Stage 4 (Akhir) - Technical Rebound dari Jenuh Jual"
            stage_desc = f"Tren utama masih di bawah EMA50 (Rp {e50:,}), namun muncul pantulan awal dari oversold (RSI {s['rsi']}). Cocok swing cepat."
        else:
            stage = "Stage 4 - Markdown / Downtrend"
            stage_desc = f"Harga berada di bawah EMA20 ({e20:,}) dan EMA50 ({e50:,}). Tekanan jual masih dominan; tunggu base baru terbentuk."
    else:
        stage = "Stage 1 - Konsolidasi / Sideways Base"
        stage_desc = f"Harga bergerak mendatar di sekitar EMA20-EMA50 (BB Width {s['bbw']}%). Menunggu katalis volume."

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
        risks.append(f"Likuiditas tipis (Rp {s['value_traded_b']} M/hari) - rawan spread lebar.")
    if s["rsi"] >= 74:
        risks.append(f"RSI Overbought ({s['rsi']}) - hindari kejar harga di pucuk.")
    if c < e50:
        risks.append(f"Masih di bawah EMA50 (Rp {e50:,}) - tren menengah belum sepenuhnya aman.")
    if hist_ctx.get("volatility_ann") and hist_ctx["volatility_ann"] >= 55:
        risks.append(f"Volatilitas tahunan tinggi ({hist_ctx['volatility_ann']}%) - wajib perkecil ukuran lot.")
    if neg_n > pos_n:
        risks.append("Sentimen berita terbaru cenderung negatif - pantau reaksi pasar terhadap isu terkini.")
    if s["plan"]["rr"] < 1.5:
        risks.append(f"Risk:Reward hanya 1:{s['plan']['rr']} - ruang profit terbatas dibanding risiko SL.")
    if not risks:
        risks.append("Risiko teknikal, likuiditas, dan sentimen berita relatif terkendali selama disiplin SL.")

    if s["alpha_score"] >= 75 and c > e50:
        horizon = "Swing Trading (1-4 Minggu) / Trend Following"
    elif s["is_breakout"] or s["rvol"] >= 1.8:
        horizon = "Day Trade / Fast Swing (2-7 Hari)"
    elif s["pe"] is not None and 0 < s["pe"] <= 14 and (s["roe"] or 0) >= 12:
        horizon = "Position / Value Investing (1-6 Bulan)"
    else:
        horizon = "Wait & See / Pantau Support"

    p = s["plan"]
    scenarios = {
        "bullish": f"Bertahan di atas Rp {p['entry_high']:,} dengan RVOL >= 1.3x membuka peluang naik ke TP1 Rp {p['tp1']:,} (+{p['tp1_pct']}%) hingga TP2 Rp {p['tp2']:,} (+{p['tp2_pct']}%).",
        "base": f"Jika koreksi sehat, area antre ideal di Rp {p['entry_low']:,}-{p['entry_high']:,} (dekat Support 20D / VWAP) untuk menjaga R:R 1:{p['rr']}.",
        "bearish": f"Batal jika jebol Stop Loss Rp {p['stop_loss']:,} ({p['sl_pct']}%). Disiplin Cut Loss untuk menghindari drawdown lebih dalam.",
    }

    q = (question or "").strip().lower()
    if not q:
        qa_answer = (
            f"Sintesis 4 Sumber untuk IDX:{s['ticker']} ({s['signal']} - Skor {s['alpha_score']}/100, Peringkat #{rank}/{len(peers)} sektor {s['sector']}):\n"
            f"- Teknikal & Aksi Harga: {stage_desc}\n"
            f"- Arus Dana & Historis: {flow}\n"
            f"- Berita & Katalis: {news_summary}\n"
            f"- Eksekusi: {p['note']}"
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
            f"Strategi Entry & Cut Loss {s['ticker']}: Cicil 50% di Rp {p['entry_low']:,}-{p['entry_high']:,} (Support 20D historis: Rp {hist_ctx.get('support_20d') or p['entry_low']:,}), sisa 50% saat konfirmasi mantul. "
            f"Wajib Cut Loss jika tutup di bawah Rp {p['stop_loss']:,} ({p['sl_pct']}%)."
        )
    elif "sektor" in q or "kompetitor" in q or "banding" in q:
        peers_txt = ", ".join([f"{x['ticker']} (Skor {x['alpha_score']}, {x['change']:+.2f}%)" for x in top_peers]) or "tidak ada pembanding likuid"
        qa_answer = f"Di sektor {s['sector']}, {s['ticker']} peringkat #{rank}/{len(peers)} (Skor {s['alpha_score']} vs rata-rata {avg_sector_score}). Kompetitor teratas: {peers_txt}."
    elif "bandar" in q or "trap" in q or "risiko" in q or "jebakan" in q:
        qa_answer = f"Cek Jebakan & Risiko {s['ticker']}: {flow} {news_summary} Peringatan: {' '.join(risks)}"
    else:
        qa_answer = f"Analisa {s['ticker']} ({s['signal']}): {stage_desc} {flow} {news_summary} Area Beli Rp {p['entry_low']:,}-{p['entry_high']:,}, SL Rp {p['stop_loss']:,}, TP1 Rp {p['tp1']:,}."

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
    fee_roundtrip = 0.004

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
            msg = f"<b>ALPHA IDX ALERT</b> ({market['updated_at']})\nBelum ada sinyal di atas Skor {min_score} saat ini."
        else:
            lines = [f"<b>ALPHA IDX SNIPER ALERT</b>\n{market['updated_at']}\nFilter: {'ISSI Syariah' if only_issi else 'Semua IHSG'} - Skor >= {min_score}\n"]
            for x in picks:
                p = x["plan"]
                lines.append(
                    f"- <b>{x['ticker']}</b> ({x['signal']} - Skor {x['alpha_score']})\n"
                    f"  Harga: Rp {int(x['close']):,} ({x['change']:+.2f}%) | RVOL {x['rvol']}x\n"
                    f"  Beli: {p['entry_low']:,}-{p['entry_high']:,} | SL: {p['stop_loss']:,} | TP1: {p['tp1']:,}"
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
        lines = [f"<b>ALPHA IDX AUTO-ALERT</b> ({market['updated_at']})\n"]
        for x in picks:
            p = x["plan"]
            lines.append(f"- <b>{x['ticker']}</b> Skor {x['alpha_score']} | Beli {p['entry_low']:,}-{p['entry_high']:,} | SL {p['stop_loss']:,} | TP1 {p['tp1']:,}")
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
