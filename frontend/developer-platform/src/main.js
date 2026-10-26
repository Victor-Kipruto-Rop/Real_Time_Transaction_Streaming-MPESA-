import "./style.css";

const sections = [["API Explorer","Inspect versioned endpoints and preview requests in the sandbox."],["API credentials","Manage sandbox credentials. Production access requires approval."],["Webhooks","Configure signed event delivery and inspect delivery history."],["SDKs & guides","Find integration patterns, examples and API references."]];
const nav = ["Overview","API Explorer","API keys","Webhooks","Events","SDKs","Usage"];
document.querySelector("#app").innerHTML = `
<div class="shell">
<aside class="sidebar"><a class="brand" href="#"><span class="mark">P</span><span>PesaGuard<small>DEVELOPER PLATFORM</small></span></a><div class="workspace-label">DEVELOPER CONSOLE</div><nav>${nav.map((n,i)=>`<button class="nav-item ${i===0?"active":""}" data-nav="${n}"><span class="nav-dot"></span>${n}</button>`).join("")}</nav><div class="sidebar-bottom"><span class="status-dot"></span> Sandbox environment <small>Demo UI · no live credentials</small></div></aside>
<main><header><div class="crumb">Developer platform <span>/</span> Overview</div><div class="header-right"><span class="env">SANDBOX</span><button class="avatar" aria-label="Account menu">VK</button></div></header><section class="hero"><div><p class="eyebrow">BUILD WITH PESAGUARD</p><h1>Financial infrastructure, built for developers.</h1><p class="lead">Integrate transaction visibility, reconciliation signals and risk events into your products with clear APIs and predictable workflows.</p><button class="primary" id="main-cta">Open API Explorer <span>↗</span></button></div><div class="code-card"><div class="code-head"><span class="lights">● ● ●</span><span>request.js</span><span class="code-tag">SANDBOX</span></div><pre><code><span class="muted">// Example request structure</span>
<span class="pink">const</span> response = <span class="blue">await</span> fetch(
  <span class="green">"${API_BASE_URL}/api/v1/transactions"</span>,
  {
    headers: {
      <span class="green">"Authorization"</span>: <span class="green">`Bearer ${token}`</span>
    }
  }
);</code></pre><div class="code-foot">Use sandbox credentials only in this example.</div></div></section><section class="section-head"><div><p class="eyebrow">YOUR TOOLKIT</p><h2>Everything to build and operate</h2></div><span class="muted">Explore the workspace</span></section><div class="card-grid">${sections.map((c,i)=>`<button class="feature-card" data-card="${c[0]}"><span class="feature-index">0${i+1}</span><h3>${c[0]}</h3><p>${c[1]}</p><span class="arrow">Explore ↗</span></button>`).join("")}</div><footer><span>© PesaGuard · Developer infrastructure</span><span>API contracts · Security · Support</span></footer></main></div>`;
document.querySelectorAll("[data-nav], [data-card], #main-cta").forEach(el=>el.addEventListener("click",()=>{const label=el.dataset.nav||el.dataset.card||"Open API Explorer";document.querySelectorAll("[data-nav]").forEach(n=>n.classList.toggle("active",n===el));document.querySelector(".crumb").innerHTML="Developer platform <span>/</span> "+label;document.querySelector("h2").textContent=label;document.querySelector(".section-head .muted").textContent="Connect this section to the authenticated API to enable live data.";document.querySelector(".section-head").scrollIntoView({behavior:"smooth",block:"start"});}));
