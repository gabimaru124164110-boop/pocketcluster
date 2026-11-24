PAGE = r"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PocketCluster</title>
<style>
body{font:16px system-ui,sans-serif;margin:0;padding:16px;background:#111;color:#eee}
h1{font-size:20px;margin:0 0 12px}
.card{background:#1c1c1c;border-radius:10px;padding:12px;margin:10px 0}
.bar{height:14px;background:#333;border-radius:7px;overflow:hidden;margin-top:10px}
.bar>div{height:100%;background:#4ade80;width:0;transition:width .3s}
table{width:100%;border-collapse:collapse}
td,th{text-align:left;padding:6px 4px;font-size:14px}
.on{color:#4ade80}.off{color:#f87171}
</style>
<h1>PocketCluster</h1>
<div class="card"><div id="sum">connecting...</div><div class="bar"><div id="fill"></div></div></div>
<div class="card"><table><thead><tr><th>Worker</th><th>Host</th><th>State</th><th>Tasks done</th></tr></thead><tbody id="rows"></tbody></table></div>
<script>
const tok = new URLSearchParams(location.search).get("token") || prompt("Cluster token:") || "";
const esc = t => String(t).replace(/[&<>"']/g, c => "&#" + c.charCodeAt(0) + ";");
async function tick() {
  const sum = document.getElementById("sum");
  try {
    const r = await fetch("/status?token=" + encodeURIComponent(tok));
    if (!r.ok) { sum.textContent = "bad token"; return; }
    const s = await r.json();
    const total = s.queued + s.running + s.done;
    if (total) {
      sum.textContent = s.workers_online + " workers online | " + s.done + "/" + total +
        " tasks done | " + s.queued + " queued, " + s.running + " running";
    } else {
      sum.textContent = s.workers_online + " workers online | idle | " + s.completed_total + " tasks completed so far";
    }
    document.getElementById("fill").style.width = (total ? 100 * s.done / total : 0) + "%";
    document.getElementById("rows").innerHTML = s.workers.map(w =>
      "<tr><td>" + esc(w.id) + "</td><td>" + esc(w.host) + "</td><td class=\"" +
      (w.online ? "on" : "off") + "\">" + (w.online ? (w.busy ? "working" : "idle") : "offline") +
      "</td><td>" + w.done + "</td></tr>").join("");
  } catch (e) {
    sum.textContent = "coordinator unreachable";
  }
}
tick();
setInterval(tick, 1000);
</script>
"""
