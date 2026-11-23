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
    const { useState, useEffect, useMemo, useRef, useId } = React;
    const fmtRp = (n) => (n != null && !isNaN(n) ? "Rp " + Math.round(Number(n)).toLocaleString("id-ID") : "-");

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
            { description: "IHSG", proName: "IDX:COMPOSITE" }, { description: "BRIS", proName: "IDX:BRIS" },
            { description: "TLKM", proName: "IDX:TLKM" }, { description: "ADRO", proName: "IDX:ADRO" },
            { description: "AMMN", proName: "IDX:AMMN" }, { description: "ANTM", proName: "IDX:ANTM" },
            { description: "ASII", proName: "IDX:ASII" }, { description: "ICBP", proName: "IDX:ICBP" },
            { description: "PGEO", proName: "IDX:PGEO" },
          ],
          showSymbolLogo: true, isTransparent: true, displayMode: "adaptive", colorTheme: "dark", locale: "id",
        });
        wrap.appendChild(s);
        host.appendChild(wrap);
      }, []);
      return <div ref={ref} className="w-full bg-slate-950 border-b border-slate-800/80" />;
    }

    function TradingViewChart({ ticker, interval, expanded }) {
      const containerId = "tv_chart_" + useId().replace(/[:]/g, "");
      const ref = useRef(null);
      useEffect(() => {
        if (!ticker || !ref.current) return;
        let timer = null;
        let active = true;
        const mount = () => {
          if (!active || !ref.current) return;
          if (typeof TradingView !== "undefined") {
            ref.current.innerHTML = "";
            new TradingView.widget({
              autosize: true,
              symbol: "IDX:" + ticker,
              interval: interval || "D",
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
              container_id: containerId,
            });
          } else {
            timer = setTimeout(mount, 250);
          }
        };
        mount();
        return () => {
          active = false;
          if (timer) clearTimeout(timer);
        };
      }, [ticker, interval, expanded, containerId]);

      return (
        <div
          id={containerId}
          ref={ref}
          style={{ height: expanded ? "620px" : "460px" }}
          className="w-full bg-slate-950"
        />
      );
    }

    function TradingViewGauge({ ticker }) {
      const ref = useRef(null);
      useEffect(() => {
        if (!ticker || !ref.current) return;
        ref.current.innerHTML = "";
        const wrap = document.createElement("div");
        wrap.className = "tradingview-widget-container";
        wrap.style.height = "100%"; wrap.style.width = "100%";
        const w = document.createElement("div");
        w.className = "tradingview-widget-container__widget";
        wrap.appendChild(w);
        const s = document.createElement("script");
        s.type = "text/javascript";
        s.src = "https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js";
        s.async = true;
        s.text = JSON.stringify({
          interval: "1D", width: "100%", isTransparent: true, height: "100%",
          symbol: "IDX:" + ticker, showIntervalTabs: true, displayMode: "multiple",
          locale: "id", colorTheme: "dark",
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
        wrap.style.width = "100%"; wrap.style.height = "640px";
        const w = document.createElement("div");
        w.className = "tradingview-widget-container__widget";
        w.style.width = "100%"; w.style.height = "100%";
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
          <text x={W - PAD - 6} y={PAD + 14} textAnchor="end" fill="#34d399" fontSize="10" fontWeight="bold">LEADING (Kuat)</text>
          <text x={W - PAD - 6} y={H - PAD - 6} textAnchor="end" fill="#fbbf24" fontSize="10" fontWeight="bold">WEAKENING (Melambat)</text>
          <text x={PAD + 6} y={PAD + 14} textAnchor="start" fill="#38bdf8" fontSize="10" fontWeight="bold">IMPROVING (Bangkit)</text>
          <text x={PAD + 6} y={H - PAD - 6} textAnchor="start" fill="#fb7185" fontSize="10" fontWeight="bold">LAGGING (Lemah)</text>
          {sectors.map((s) => {
            const px = mapX(s.avg_perf_1m), py = mapY(s.avg_perf_w);
            return (
              <g key={s.sector}>
                <circle cx={px} cy={py} r={Math.min(12, Math.max(5, s.avg_alpha / 10))} fill={qColor[s.quadrant] || "#94a3b8"} fillOpacity="0.85" stroke="#0f172a" strokeWidth="1.5" />
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
      if (allVals.length < 2) return <div className="h-64 flex items-center justify-center text-xs text-slate-400">Data grafik historis belum tersedia.</div>;
      const W = 680, H = 260, PAD = 34;
      const minV = Math.min(...allVals), maxV = Math.max(...allVals), span = Math.max(1, maxV - minV);
      return (
        <div className="space-y-2">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-64 bg-slate-950/90 rounded-xl border border-slate-800">
            <line x1={PAD} y1={H - PAD - ((100 - minV) / span) * (H - 2 * PAD)} x2={W - PAD} y2={H - PAD - ((100 - minV) / span) * (H - 2 * PAD)} stroke="#334155" strokeDasharray="4 4" />
            {tickers.map((t, idx) => {
              const pts = series[t] || [];
              if (pts.length < 2) return null;
              const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${(PAD + (i / (pts.length - 1)) * (W - 2 * PAD)).toFixed(1)},${(H - PAD - ((p.idx - minV) / span) * (H - 2 * PAD)).toFixed(1)}`).join(" ");
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
      if (!curve || curve.length < 2) return <div className="h-56 flex items-center justify-center text-xs text-slate-400">Belum ada kurva ekuitas.</div>;
      const W = 680, H = 230, PAD = 34, vals = curve.map((c) => c.equity);
      const minV = Math.min(...vals), maxV = Math.max(...vals), span = Math.max(0.5, maxV - minV);
      const pts = curve.map((c, i) => `${(PAD + (i / (curve.length - 1)) * (W - 2 * PAD)).toFixed(1)},${(H - PAD - ((c.equity - minV) / span) * (H - 2 * PAD)).toFixed(1)}`).join(" ");
      const lastEq = vals[vals.length - 1];
      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-56 bg-slate-950/90 rounded-xl border border-slate-800">
          <polyline fill="none" stroke={lastEq >= 100 ? "#10b981" : "#f43f5e"} strokeWidth="2.5" points={pts} />
          <text x={PAD} y={18} fill="#94a3b8" fontSize="10">
            Modal Awal = 100 • Akhir = {lastEq.toFixed(2)} ({curve[0].date} s/d {curve[curve.length - 1].date})
          </text>
        </svg>
      );
    }

    function SectorRotationView({ onJumpTicker }) {
      const [data, setData] = useState(null), [loading, setLoading] = useState(true), [err, setErr] = useState("");
      const load = async () => {
        setLoading(true); setErr("");
        try {
          const r = await fetch("/api/sectors");
          const d = await r.json();
          if (d.error) throw new Error(d.error);
          setData(d);
        } catch (e) {
          setErr(e.message);
        } finally {
          setLoading(false);
        }
      };
      useEffect(() => { load(); }, []);

      const qBadge = (q) =>
        q === "LEADING"
          ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
          : q === "WEAKENING"
          ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
          : q === "IMPROVING"
          ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
          : "bg-rose-500/20 text-rose-300 border-rose-500/40";

      return (
        <div className="space-y-5">
          <div className="glass rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-extrabold text-white">🧭 Rotasi Sektor & Heatmap IHSG (RRG Quadrant)</h2>
              <p className="text-xs text-slate-400">Mengetahui sektor mana yang sedang dimasuki dana institusi minggu ini</p>
            </div>
            <button onClick={load} className="h-9 px-4 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-xs font-extrabold text-slate-950">
              ↻ Refresh Sektor
            </button>
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
                    {data.sectors.map((s) => (
                      <div
                        key={s.sector}
                        className={`rounded-xl border p-2.5 ${
                          s.avg_change >= 1
                            ? "bg-emerald-500/25 border-emerald-500/50"
                            : s.avg_change > 0
                            ? "bg-emerald-500/10 border-emerald-500/30"
                            : s.avg_change <= -1
                            ? "bg-rose-500/25 border-rose-500/50"
                            : "bg-rose-500/10 border-rose-500/30"
                        }`}
                      >
                        <div className="text-xs font-bold text-white truncate">{s.sector}</div>
                        <div className={`text-base font-extrabold font-mono mt-0.5 ${s.avg_change >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                          {s.avg_change > 0 ? "+" : ""}{s.avg_change}%
                        </div>
                        <div className="text-[10px] text-slate-300">Skor α: {s.avg_alpha} • Val {s.total_val_b}M</div>
                      </div>
                    ))}
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
                          <div className="text-[11px] text-slate-400">{s.count} emiten ({s.issi_count} ISSI) • RVOL {s.avg_rvol}x</div>
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
                          <button
                            key={st.ticker}
                            onClick={() => onJumpTicker(st.ticker)}
                            className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-emerald-500/20 border border-slate-700 text-[11px] font-mono text-white"
                          >
                            <b>{st.ticker}</b>{" "}
                            <span className={st.change >= 0 ? "text-emerald-400" : "text-rose-400"}>
                              {st.change > 0 ? "+" : ""}{st.change}%
                            </span>
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

    function DeepAiView({ stock, allStocks, onSelectTicker, onBackToChart }) {
      const [report, setReport] = useState(null), [loading, setLoading] = useState(false), [err, setErr] = useState("");
      const [question, setQuestion] = useState("");
      const [apiKey, setApiKey] = useState(() => localStorage.getItem("alpha_idx_gemini_key") || "");
      const [showKeyBox, setShowKeyBox] = useState(false);

      const runAnalysis = async (customQ = "") => {
        if (!stock) return;
        setLoading(true); setErr("");
        try {
          const res = await fetch("/api/ai-analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ticker: stock.ticker, question: customQ, api_key: apiKey }),
          });
          const data = await res.json();
          if (data.error) throw new Error(data.error);
          setReport(data);
        } catch (e) {
          setErr(e.message);
        } finally {
          setLoading(false);
        }
      };

      useEffect(() => {
        if (stock) runAnalysis("");
      }, [stock && stock.ticker]);

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
                  <h2 className="text-base lg:text-lg font-extrabold text-white">
                    AI Deep Equity Analyst (4 Sumber) • <span className="text-emerald-400 font-mono">IDX:{stock.ticker}</span>
                  </h2>
                  {stock.is_issi && (
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                      ☪ ISSI
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  {stock.name} • {stock.sector} • {fmtRp(stock.close)} ({stock.change > 0 ? "+" : ""}{stock.change}%)
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={stock.ticker}
                onChange={(e) => onSelectTicker(e.target.value)}
                className="h-9 bg-slate-900 border border-slate-700 rounded-lg px-3 text-xs font-mono text-white"
              >
                {allStocks.slice(0, 150).map((x) => (
                  <option key={x.ticker} value={x.ticker}>
                    {x.ticker} — Skor {x.alpha_score} ({x.signal})
                  </option>
                ))}
              </select>
              <button
                onClick={() => setShowKeyBox(!showKeyBox)}
                className="h-9 px-3 rounded-lg bg-slate-800 border border-slate-700 text-xs font-semibold text-violet-300"
              >
                🔑 {apiKey ? "Gemini Aktif" : "Gemini (Opsional)"}
              </button>
              <button
                onClick={() => runAnalysis(question)}
                className="h-9 px-3.5 rounded-lg bg-gradient-to-r from-violet-500 to-cyan-500 text-xs font-extrabold text-white"
              >
                ⚡ Analisa Ulang
              </button>
              <button
                onClick={onBackToChart}
                className="h-9 px-3 rounded-lg bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-200"
              >
                ← Chart
              </button>
            </div>
          </div>

          {showKeyBox && (
            <div className="glass rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 border-violet-500/30">
              <div className="text-xs text-slate-300 max-w-2xl">
                <b className="text-violet-300">Opsional (Gemini LLM):</b> Tanpa key, Quant AI 4-Sumber tetap berjalan penuh. Tempel API Key gratis dari <i>aistudio.google.com</i> untuk narasi ekstra:
              </div>
              <div className="flex items-center gap-2 flex-1 max-w-md">
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => saveKey(e.target.value)}
                  placeholder="AIzaSy..."
                  className="h-8 flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 text-xs font-mono text-white"
                />
                <button onClick={() => runAnalysis(question)} className="h-8 px-3 rounded-lg bg-violet-500 text-white text-xs font-bold">
                  Terapkan
                </button>
              </div>
            </div>
          )}

          {err && <div className="glass rounded-xl p-4 border-rose-500/40 text-xs text-rose-300">Error AI: {err}</div>}
          {loading && (
            <div className="glass rounded-2xl p-10 text-center text-sm text-cyan-300 animate-pulse">
              🤖 Menggabungkan 4 sumber data live untuk IDX:{stock.ticker}...
            </div>
          )}

          {report && !loading && (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2 text-[11px]">
                <span className="text-slate-400 font-bold">Sumber Aktif:</span>
                {(report.sources_used || []).map((src) => (
                  <span key={src} className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-semibold">
                    ✓ {src}
                  </span>
                ))}
                {report.hist_ctx && report.hist_ctx.last_bar_date && (
                  <span className="px-2.5 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 font-mono">
                    Bar Terakhir: {report.hist_ctx.last_bar_date}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
                <div className="lg:col-span-8 space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="glass rounded-xl p-3.5 border-violet-500/30">
                      <div className="text-[10px] uppercase text-slate-400 font-bold">AI Conviction</div>
                      <div className="text-2xl font-extrabold font-mono text-violet-300 mt-1">{report.conviction}/100</div>
                      <div className="text-[11px] text-emerald-300 font-semibold">{stock.signal}</div>
                    </div>
                    <div className="glass rounded-xl p-3.5">
                      <div className="text-[10px] uppercase text-slate-400 font-bold">Horizon Ideal</div>
                      <div className="text-xs font-bold text-white mt-1.5 leading-snug">{report.horizon}</div>
                    </div>
                    <div className="glass rounded-xl p-3.5">
                      <div className="text-[10px] uppercase text-slate-400 font-bold">Risk : Reward</div>
                      <div className="text-2xl font-extrabold font-mono text-cyan-300 mt-1">1:{stock.plan.rr}</div>
                      <div className="text-[11px] text-rose-300">SL {stock.plan.sl_pct}% • TP1 +{stock.plan.tp1_pct}%</div>
                    </div>
                    <div className="glass rounded-xl p-3.5">
                      <div className="text-[10px] uppercase text-slate-400 font-bold">Sentimen Berita</div>
                      <div className={`text-lg font-extrabold mt-1 ${report.news_sentiment === "Positif" ? "text-emerald-300" : report.news_sentiment === "Negatif" ? "text-rose-300" : "text-slate-300"}`}>
                        {report.news_sentiment}
                      </div>
                      <div className="text-[11px] text-slate-400">{(report.news_items || []).length} artikel</div>
                    </div>
                  </div>

                  <div className="glass rounded-2xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-bold uppercase text-cyan-300">Ringkasan Riset & Tanya Jawab AI</div>
                      {report.llm_used && (
                        <span className="px-2 py-0.5 rounded bg-violet-500/20 text-violet-200 text-[10px] font-mono">
                          {report.llm_model}
                        </span>
                      )}
                    </div>
                    <pre className="whitespace-pre-wrap text-xs text-slate-200 leading-relaxed font-sans bg-slate-950/70 rounded-xl p-3.5 border border-slate-800">
                      {report.qa_answer}
                    </pre>
                    <div className="flex flex-wrap gap-1.5">
                      {quickPrompts.map((qp) => (
                        <button
                          key={qp}
                          onClick={() => { setQuestion(qp); runAnalysis(qp); }}
                          className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-[11px] text-slate-200"
                        >
                          {qp}
                        </button>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && runAnalysis(question)}
                        placeholder="Tanyakan strategi entry, hold, atau risiko saham ini..."
                        className="h-9 flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 text-xs text-white"
                      />
                      <button
                        onClick={() => runAnalysis(question)}
                        className="h-9 px-4 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-xs font-extrabold text-slate-950"
                      >
                        Kirim
                      </button>
                    </div>
                  </div>
                </div>

                <div className="lg:col-span-4 space-y-4">
                  <div className="glass rounded-2xl p-4 space-y-2.5">
                    <div className="text-xs font-bold uppercase text-emerald-300">Rencana Trading Terukur</div>
                    <div className="text-xs font-mono space-y-1.5 text-slate-200">
                      <div className="flex justify-between"><span>Area Beli:</span><b>{fmtRp(stock.plan.entry_low)} - {fmtRp(stock.plan.entry_high)}</b></div>
                      <div className="flex justify-between text-rose-300"><span>Stop Loss:</span><b>{fmtRp(stock.plan.stop_loss)} ({stock.plan.sl_pct}%)</b></div>
                      <div className="flex justify-between text-emerald-300"><span>Target 1:</span><b>{fmtRp(stock.plan.tp1)} (+{stock.plan.tp1_pct}%)</b></div>
                      <div className="flex justify-between text-cyan-300"><span>Target 2:</span><b>{fmtRp(stock.plan.tp2)} (+{stock.plan.tp2_pct}%)</b></div>
                    </div>
                    <p className="text-[11px] text-slate-400 pt-2 border-t border-slate-800">{report.fund_audit}</p>
                  </div>

                  <div className="glass rounded-2xl p-4 space-y-2">
                    <div className="text-xs font-bold uppercase text-amber-300">Risiko & Skenario</div>
                    <ul className="space-y-1.5 text-[11px] text-slate-300 list-disc pl-4">
                      {(report.risk_flags || []).map((rf, idx) => <li key={idx}>{rf}</li>)}
                    </ul>
                    {report.scenarios && (
                      <div className="pt-2 border-t border-slate-800 space-y-1.5 text-[11px] text-slate-300">
                        <div><b className="text-emerald-300">Bullish:</b> {report.scenarios.bullish}</div>
                        <div><b className="text-cyan-300">Base:</b> {report.scenarios.base}</div>
                        <div><b className="text-rose-300">Bearish:</b> {report.scenarios.bearish}</div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      );
    }

    function App() {
      const [market, setMarket] = useState(null);
      const [selectedTicker, setSelectedTicker] = useState("BRIS");
      const [interval, setInterval] = useState("D");
      const [expanded, setExpanded] = useState(false);
      const [activeTab, setActiveTab] = useState("ai");

      const loadMarket = async (force = false) => {
        try {
          const r = await fetch(`/api/scan?force=${force ? 1 : 0}`);
          const d = await r.json();
          if (!d.error) setMarket(d);
        } catch (_) {}
      };

      useEffect(() => {
        loadMarket(false);
        const id = setInterval(() => loadMarket(false), 20000);
        return () => clearInterval(id);
      }, []);

      const stocks = market?.stocks || [];
      const currentStock = useMemo(
        () => stocks.find((x) => x.ticker === selectedTicker) || stocks[0] || null,
        [stocks, selectedTicker]
      );

      return (
        <div className="min-h-screen flex flex-col">
          <TickerTape />
          <header className="glass sticky top-0 z-20 px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="font-extrabold tracking-tight text-white text-base">ALPHA IDX</span>
              {market?.updated_at && (
                <span className="text-[11px] font-mono text-slate-400">{market.updated_at}</span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => setActiveTab("ai")}
                className={`h-8 px-3 rounded-lg text-xs font-bold ${activeTab === "ai" ? "bg-violet-500 text-white" : "bg-slate-800 text-slate-300"}`}
              >
                🤖 AI Analyst
              </button>
              <button
                onClick={() => setActiveTab("chart")}
                className={`h-8 px-3 rounded-lg text-xs font-bold ${activeTab === "chart" ? "bg-emerald-500 text-slate-950" : "bg-slate-800 text-slate-300"}`}
              >
                📈 Chart & Teknikal
              </button>
              <button
                onClick={() => setActiveTab("sectors")}
                className={`h-8 px-3 rounded-lg text-xs font-bold ${activeTab === "sectors" ? "bg-cyan-500 text-slate-950" : "bg-slate-800 text-slate-300"}`}
              >
                🧭 Sektor RRG
              </button>
              <button
                onClick={() => loadMarket(true)}
                className="h-8 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-emerald-300"
              >
                ↻ Scan
              </button>
            </div>
          </header>

          <main className="flex-1 p-4 max-w-[1440px] w-full mx-auto space-y-5">
            {activeTab === "ai" && (
              <DeepAiView
                stock={currentStock}
                allStocks={stocks}
                onSelectTicker={(t) => setSelectedTicker(t)}
                onBackToChart={() => setActiveTab("chart")}
              />
            )}

            {activeTab === "chart" && (
              <div className="space-y-4">
                <div className="glass rounded-2xl p-3.5 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Emiten:</span>
                    <select
                      value={currentStock?.ticker || selectedTicker}
                      onChange={(e) => setSelectedTicker(e.target.value)}
                      className="h-8 bg-slate-900 border border-slate-700 rounded-lg px-2.5 text-xs font-mono text-white"
                    >
                      {stocks.slice(0, 200).map((s) => (
                        <option key={s.ticker} value={s.ticker}>{s.ticker} ({fmtRp(s.close)})</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {[["15", "15m"], ["60", "1H"], ["D", "1D"], ["W", "1W"]].map(([iv, lbl]) => (
                      <button
                        key={iv}
                        onClick={() => setInterval(iv)}
                        className={`h-8 px-2.5 rounded-lg text-xs font-mono font-bold ${interval === iv ? "bg-emerald-500 text-slate-950" : "bg-slate-800 text-slate-300"}`}
                      >
                        {lbl}
                      </button>
                    ))}
                    <button
                      onClick={() => setExpanded(!expanded)}
                      className="h-8 px-2.5 rounded-lg bg-slate-800 text-xs font-semibold text-slate-200"
                    >
                      {expanded ? "Normal" : "Perbesar"}
                    </button>
                  </div>
                </div>

                <div className="glass rounded-2xl overflow-hidden">
                  <TradingViewChart
                    ticker={currentStock?.ticker || selectedTicker}
                    interval={interval}
                    expanded={expanded}
                  />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="glass rounded-2xl overflow-hidden">
                    <TradingViewGauge ticker={currentStock?.ticker || selectedTicker} />
                  </div>
                  <div className="glass rounded-2xl overflow-hidden">
                    <TradingViewFinancialsWidget ticker={currentStock?.ticker || selectedTicker} />
                  </div>
                </div>
              </div>
            )}

            {activeTab === "sectors" && (
              <SectorRotationView
                onJumpTicker={(t) => {
                  setSelectedTicker(t);
                  setActiveTab("chart");
                }}
              />
            )}
          </main>
        </div>
      );
    }

    ReactDOM.createRoot(document.getElementById("root")).render(<App />);
  </script>
</body>
</html>
