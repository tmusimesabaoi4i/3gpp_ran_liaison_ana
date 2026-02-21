(function() {
  const debugMode = true;
  if (typeof window.LIAISON_DATA === "undefined") {
    console.error("LIAISON_DATA not found. Load data.js first."); return;
  }
  const { meetings: meetingList, edgesByMeeting, edgesTotal } = window.LIAISON_DATA;
  const COLOR_IN = "rgba(31,119,180,0.55)";
  const COLOR_OUT = "rgba(255,127,14,0.55)";
  const state = { dir: "all", meeting: "all", splitOut: false };

  const dirEl = document.getElementById("dir");
  const meetingsEl = document.getElementById("meetings");
  const splitOutEl = document.getElementById("splitOut");
  const chartEl = document.getElementById("chart");
  const modalEl = document.getElementById("modal");
  const modalTitle = document.getElementById("modalTitle");
  const modalFromTo = document.getElementById("modalFromTo");
  const modalTotal = document.getElementById("modalTotal");
  const modalTableBody = document.querySelector("#modalTable tbody");
  function closeModal() { modalEl.classList.add("hidden"); }
  document.getElementById("modalClose").addEventListener("click", closeModal);
  modalEl.addEventListener("click", (e) => { if (e.target === modalEl) closeModal(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !modalEl.classList.contains("hidden")) closeModal(); });

  meetingsEl.innerHTML = "";
  function addRadio(value, label) {
    const lbl = document.createElement("label");
    const inp = document.createElement("input");
    inp.type = "radio"; inp.name = "meeting"; inp.value = value;
    if (value === "all") inp.checked = true;
    const sp = document.createElement("span"); sp.textContent = label;
    lbl.appendChild(inp); lbl.appendChild(sp);
    inp.addEventListener("change", () => { state.meeting = value; render(); });
    meetingsEl.appendChild(lbl);
  }
  addRadio("all", "all");
  meetingList.forEach(m => addRadio(m, m));
  dirEl.addEventListener("change", e => { state.dir = e.target.value; render(); });
  splitOutEl.addEventListener("change", e => { state.splitOut = e.target.checked; render(); });

  function edgesToSankey(edges, dir, useSplit) {
    const edgeMap = {};
    edges.forEach(e => {
      const from_ = e.from, to_ = e.to, ek = e.edge_key;
      const w = dir === "out" && useSplit ? Number(e.weight_split) : Number(e.weight_raw);
      const key = from_ + "|||" + to_;
      if (!edgeMap[key]) {
        edgeMap[key] = { from: from_, to: to_, weight: 0, color: dir === "in" ? COLOR_IN : COLOR_OUT,
          edge_key: ek };
      }
      edgeMap[key].weight += w;
    });
    const edgesArr = Object.values(edgeMap).filter(x => x.weight > 0);
    if (edgesArr.length === 0) {
      return { node: { label: ["RAN"], color: ["#555"] },
        link: { source: [], target: [], value: [], color: [], customdata: [] } };
    }
    const nodeSet = new Set();
    edgesArr.forEach(e => { nodeSet.add(e.from); nodeSet.add(e.to); });
    const labels = ["RAN", ...[...nodeSet].filter(n => n !== "RAN").sort()];
    const idx = Object.fromEntries(labels.map((l, i) => [l, i]));
    const nodeColors = labels.map(l => l === "RAN" ? "#555" :
      l.endsWith("(src)") ? "rgba(31,119,180,0.8)" : "rgba(255,127,14,0.8)");
    const hoverFmt = dir === "out" && useSplit ? "Displayed: %{value:.2f}" : "Displayed: %{value:.0f}";
    return {
      node: { label: labels, color: nodeColors, pad: 20, thickness: 18 },
      link: {
        source: edgesArr.map(e => idx[e.from]),
        target: edgesArr.map(e => idx[e.to]),
        value: edgesArr.map(e => e.weight),
        color: edgesArr.map(e => e.color),
        customdata: edgesArr.map(e => e.edge_key),
        hovertemplate: hoverFmt,
      },
    };
  }

  function buildTraces() {
    const useMeeting = state.meeting;
    const dataSource = useMeeting === "all" ? edgesTotal :
      edgesByMeeting.filter(e => e.meeting === useMeeting);
    const useSplit = state.splitOut;

    if (state.dir === "in") {
      const edgesIn = dataSource.filter(e => e.dir === "in");
      const s = edgesToSankey(edgesIn, "in", false);
      return [{ type: "sankey", orientation: "h", ...s, name: "Inbound", meta: { dir: "in" } }];
    }
    if (state.dir === "out") {
      const edgesOut = dataSource.filter(e => e.dir === "out");
      const s = edgesToSankey(edgesOut, "out", useSplit);
      return [{ type: "sankey", orientation: "h", ...s, name: "Outbound", meta: { dir: "out" } }];
    }
    const edgesIn = dataSource.filter(e => e.dir === "in");
    const edgesOut = dataSource.filter(e => e.dir === "out");
    const sIn = edgesToSankey(edgesIn, "in", false);
    const sOut = edgesToSankey(edgesOut, "out", useSplit);
    return [
      { type: "sankey", orientation: "h", ...sIn, name: "Inbound",
        domain: { x: [0, 0.48], y: [0, 1] }, meta: { dir: "in" } },
      { type: "sankey", orientation: "h", ...sOut, name: "Outbound",
        domain: { x: [0.52, 1], y: [0, 1] }, meta: { dir: "out" } },
    ];
  }

  function getLayout() {
    const twoPanel = state.dir === "all";
    return {
      title: { text: twoPanel ? "Inbound (left) | Outbound (right)" :
        state.dir === "in" ? "Inbound" : "Outbound", font: { size: 16 } },
      font: { size: 11 }, margin: { l: 20, r: 20, t: 50, b: 20 },
      paper_bgcolor: "#f5f6fa", showlegend: false,
    };
  }

  function render() {
    const traces = buildTraces();
    const layout = getLayout();
    Plotly.react(chartEl, traces, layout, { responsive: true }).then(() => {
      if (chartEl.removeAllListeners) chartEl.removeAllListeners("plotly_click");
      chartEl.on("plotly_click", onPlotClick);
    });
  }

  function extractLinkIndex(pt) {
    const trace = pt.data;
    if (!trace || !trace.link || !Array.isArray(trace.link.source)) return -1;
    const n = trace.link.source.length;
    let idx = pt.pointNumber;
    if (typeof idx === "number" && idx >= 0 && idx < n) return idx;
    idx = pt.pointIndex;
    if (typeof idx === "number" && idx >= 0 && idx < n) return idx;
    idx = pt.linkIndex;
    if (typeof idx === "number" && idx >= 0 && idx < n) return idx;
    return -1;
  }

  function extractEdgeKey(pt) {
    if (!pt || !pt.data) return null;
    const trace = pt.data;
    if (!trace.link || !Array.isArray(trace.link.source)) return null;
    const linkIndex = extractLinkIndex(pt);
    if (linkIndex < 0 || linkIndex >= trace.link.source.length) return null;
    if (pt.customdata != null && pt.customdata !== "") return pt.customdata;
    const cd = trace.link.customdata;
    if (Array.isArray(cd) && cd[linkIndex] != null && cd[linkIndex] !== "") return cd[linkIndex];
    return null;
  }

  function onPlotClick(ev) {
    if (typeof console !== "undefined") {
      console.log("plotly_click", ev);
      if (ev.points && ev.points[0]) {
        const p = ev.points[0];
        console.log("pt keys", Object.keys(p));
        console.log("pt.pointNumber", p.pointNumber);
        console.log("has trace.link.customdata", !!(p.data && p.data.link && p.data.link.customdata));
      }
    }
    if (!ev.points || ev.points.length === 0) return;
    const pt = ev.points[0];
    const edgeKey = extractEdgeKey(pt);
    if (debugMode && typeof console !== "undefined") console.log("edgeKey", edgeKey);
    if (!edgeKey) return;
    const trace = pt.data;
    const dir = (trace.meta && trace.meta.dir) || "out";
    const rows = state.meeting === "all" ? edgesByMeeting :
      edgesByMeeting.filter(e => e.meeting === state.meeting);
    const filtered = rows.filter(e => e.edge_key === edgeKey);
    if (filtered.length === 0) {
      modalTitle.textContent = (dir === "in" ? "Inbound" : "Outbound") + " flow detail";
      modalFromTo.textContent = "edge_key: " + edgeKey;
      modalTotal.textContent = "該当データなし";
      modalTableBody.innerHTML = "<tr><td colspan=\"3\">該当データなし</td></tr>";
      modalEl.classList.remove("hidden");
      return;
    }
    const from_ = filtered[0].from, to_ = filtered[0].to;
    let rawSum = 0, dispSum = 0;
    const byMeeting = [];
    filtered.forEach(e => {
      rawSum += Number(e.raw_count);
      const d = state.splitOut && dir === "out" ? Number(e.weight_split) : Number(e.weight_raw);
      dispSum += d;
      byMeeting.push({ meeting: e.meeting, raw: Number(e.raw_count), disp: d });
    });
    modalTitle.textContent = (dir === "in" ? "Inbound" : "Outbound") + " flow detail";
    modalFromTo.textContent = "From: " + from_ + " → To: " + to_;
    modalTotal.textContent = "Raw: " + rawSum + ", Displayed: " + dispSum.toFixed(2);
    modalTableBody.innerHTML = byMeeting.map(r => {
      const disp = r.disp % 1 === 0 ? r.disp : r.disp.toFixed(2);
      return "<tr><td>" + r.meeting + "</td><td>" + r.raw + "</td><td>" + disp + "</td></tr>";
    }).join("");
    modalEl.classList.remove("hidden");
  }

  render();
})();