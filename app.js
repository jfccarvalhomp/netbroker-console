const fallbackState = {
  queueDepth: 2416,
  devices: [
    { host: "SW-MTZ-CORE-01", ip: "10.10.0.2", vendor: "Cisco", model: "Catalyst 9500", site: "Matriz", status: "UP", cpu: 34, backup: "Hoje" },
    { host: "RTR-MTZ-WAN-01", ip: "10.10.0.1", vendor: "Juniper", model: "MX204", site: "Matriz", status: "UP", cpu: 41, backup: "Hoje" },
    { host: "FW-DC-EDGE-01", ip: "10.20.0.5", vendor: "Fortinet", model: "FortiGate 200F", site: "Datacenter", status: "ALERTA", cpu: 76, backup: "Ontem" },
    { host: "AP-FIL-03-12", ip: "10.31.12.9", vendor: "Aruba", model: "AP-515", site: "Filial 03", status: "UP", cpu: 19, backup: "Hoje" },
    { host: "RTR-REM-07", ip: "10.44.7.1", vendor: "Mikrotik", model: "CCR2004", site: "Remoto 07", status: "DOWN", cpu: 0, backup: "3 dias" },
    { host: "SW-DC-TOR-06", ip: "10.20.6.2", vendor: "Cisco", model: "Nexus 93180", site: "Datacenter", status: "UP", cpu: 53, backup: "Hoje" },
    { host: "FW-FIL-02", ip: "10.32.0.5", vendor: "Fortinet", model: "FortiGate 80F", site: "Filial 02", status: "UP", cpu: 48, backup: "Hoje" },
    { host: "SW-FIL-05-AC", ip: "10.35.0.2", vendor: "Aruba", model: "CX 6200", site: "Filial 05", status: "ALERTA", cpu: 68, backup: "Ontem" }
  ],
  alarms: [
    { id: 1, severity: "critical", device: "RTR-REM-07", text: "Site remoto sem resposta SNMP e ICMP ha 9 minutos.", source: "Monitoring Service" },
    { id: 2, severity: "warning", device: "FW-DC-EDGE-01", text: "CPU acima de 75% durante cinco coletas consecutivas.", source: "Fortinet Adapter" },
    { id: 3, severity: "warning", device: "SW-FIL-05-AC", text: "Interface uplink com descarte crescente de pacotes.", source: "Aruba Adapter" },
    { id: 4, severity: "info", device: "SW-MTZ-CORE-01", text: "Backup de configuracao concluido com sucesso.", source: "Backup Service" }
  ],
  jobs: [
    { name: "Backup de configuracoes", desc: "Coleta configs via SSH, REST ou NETCONF e persiste no PostgreSQL.", queue: "config.backup" },
    { name: "Descoberta multivendor", desc: "Varre sub-redes, identifica fabricante e cria Device canonico.", queue: "device.discovery" },
    { name: "Atualizacao de inventario", desc: "Normaliza interfaces, versoes e modelos para o dominio central.", queue: "inventory.sync" },
    { name: "Remediacao de alarme", desc: "Executa playbooks aprovados para eventos operacionais conhecidos.", queue: "alarm.remediate" }
  ],
  events: [
    ["10:42", "command.config.backup publicado pelo Configuration Service"],
    ["10:43", "Cisco Adapter converteu interfaces para modelo canonico"],
    ["10:44", "Monitoring Service correlacionou alarme de CPU no FW-DC-EDGE-01"],
    ["10:45", "OpenTelemetry fechou trace distribuido do job inventory.sync"]
  ]
};

const diagrams = [
  "image10.png", "image11.png", "image12.png", "image13.png", "image14.png", "image15.png",
  "image16.png", "image17.png", "image18.png", "image19.png", "image20.png", "image21.png"
];

const titles = {
  dashboard: "Visao operacional",
  inventory: "Inventario canonico",
  alarms: "NOC e alarmes",
  automation: "Automacao e integracao",
  architecture: "Arquitetura proposta",
  security: "Seguranca e governanca"
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

let state = structuredClone(fallbackState);
let currentVendor = "Todos";
let searchTerm = "";
let apiOnline = false;

async function init() {
  bindEvents();
  setupPayload();
  renderTopology();
  renderDiagrams();
  await loadState();
  openView(location.hash.replace("#", "") || "dashboard");
}

function bindEvents() {
  $$(".nav-link").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      openView(link.dataset.view);
    });
  });

  $$("[data-open-view]").forEach((button) => {
    button.addEventListener("click", () => openView(button.dataset.openView));
  });

  $("#globalSearch").addEventListener("input", (event) => {
    searchTerm = event.target.value.trim().toLowerCase();
    renderDevices();
  });

  $$(".segmented button").forEach((button) => {
    button.addEventListener("click", () => {
      currentVendor = button.dataset.vendor;
      $$(".segmented button").forEach((item) => item.classList.toggle("active", item === button));
      renderDevices();
    });
  });

  $("#simulateTick").addEventListener("click", simulateTelemetry);
  $("#discoverDevices").addEventListener("click", discoverDevices);
  $("#ackAll").addEventListener("click", acknowledgeAlarms);
  $("#convertPayload").addEventListener("click", convertPayload);
}

async function loadState() {
  try {
    const data = await apiGet("/api/state");
    state = normalizeState(data);
    apiOnline = true;
  } catch (error) {
    apiOnline = false;
    toast("API indisponivel. Rodando em modo local somente leitura.");
  }

  renderAll();
}

function normalizeState(data) {
  return {
    queueDepth: data.queueDepth ?? data.queue_depth ?? fallbackState.queueDepth,
    devices: data.devices ?? fallbackState.devices,
    alarms: data.alarms ?? fallbackState.alarms,
    jobs: data.jobs ?? fallbackState.jobs,
    events: data.events ?? fallbackState.events
  };
}

function renderAll() {
  renderKpis();
  renderEvents();
  renderDevices();
  renderAlarms();
  renderJobs();
  $("#queueDepth").textContent = new Intl.NumberFormat("pt-BR").format(state.queueDepth);
  $("#brokerState").textContent = apiOnline ? "API + broker operacional" : "Modo estatico local";
}

async function apiGet(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`GET ${path} retornou ${response.status}`);
  return response.json();
}

async function apiPost(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(`POST ${path} retornou ${response.status}`);
  return response.json();
}

function openView(view) {
  if (!titles[view]) view = "dashboard";
  $$(".view").forEach((section) => section.classList.toggle("active", section.id === view));
  $$(".nav-link").forEach((link) => link.classList.toggle("active", link.dataset.view === view));
  $("#viewTitle").textContent = titles[view];
  history.replaceState(null, "", `#${view}`);
}

function filteredDevices() {
  return state.devices.filter((device) => {
    const vendorMatch = currentVendor === "Todos" || device.vendor === currentVendor;
    const haystack = `${device.host} ${device.ip} ${device.vendor} ${device.site} ${device.model}`.toLowerCase();
    return vendorMatch && haystack.includes(searchTerm);
  });
}

function renderKpis() {
  const up = state.devices.filter((device) => device.status === "UP").length;
  const availability = state.devices.length ? Math.round((up / state.devices.length) * 1000) / 10 : 0;
  const critical = state.alarms.filter((alarm) => alarm.severity === "critical").length;
  $("#kpiDevices").textContent = state.devices.length;
  $("#kpiAvailability").textContent = `${availability}%`;
  $("#kpiCritical").textContent = critical;
}

function renderTopology() {
  const sites = [
    { name: "Matriz", meta: "Cisco + Juniper", x: 8, y: 11 },
    { name: "Datacenter", meta: "Nexus + Fortinet", x: 58, y: 12 },
    { name: "Filiais", meta: "Aruba + Fortinet", x: 18, y: 58 },
    { name: "Remotos", meta: "Mikrotik", x: 62, y: 58 },
    { name: "Broker", meta: "RabbitMQ / Kafka", x: 39, y: 35 }
  ];
  $("#topology").innerHTML = sites.map((site) => `
    <div class="node" style="left:${site.x}%;top:${site.y}%">
      <strong>${site.name}</strong>
      <span>${site.meta}</span>
    </div>
  `).join("");
}

function renderEvents() {
  $("#eventStream").innerHTML = state.events.map(([time, text]) => `
    <article class="event"><time>${time}</time><span>${text}</span></article>
  `).join("");
}

function renderDevices() {
  const rows = filteredDevices();
  $("#inventoryCount").textContent = `${rows.length} itens`;
  $("#deviceTable").innerHTML = rows.map((device) => `
    <tr>
      <td><strong>${device.host}</strong><br><small>${device.model}</small></td>
      <td>${device.ip}</td>
      <td>${device.vendor}</td>
      <td>${device.site}</td>
      <td><span class="status ${statusClass(device.status)}">${device.status}</span></td>
      <td>${device.cpu}%</td>
      <td>${device.backup}</td>
    </tr>
  `).join("");
}

function renderAlarms() {
  $("#alarmList").innerHTML = state.alarms.map((alarm) => `
    <article class="alarm">
      <input type="checkbox" value="${alarm.id}" aria-label="Selecionar alarme ${alarm.id}">
      <div>
        <span class="pill ${severityClass(alarm.severity)}">${alarm.severity.toUpperCase()}</span>
        <h2>${alarm.device}</h2>
        <p>${alarm.text}</p>
      </div>
      <small>${alarm.source}</small>
    </article>
  `).join("");
}

function renderJobs() {
  $("#jobGrid").innerHTML = state.jobs.map((job) => `
    <article class="job">
      <div>
        <h2>${job.name}</h2>
        <p>${job.desc}</p>
        <small>${job.queue}</small>
      </div>
      <button class="ghost-button" type="button" data-run-job="${job.queue}">Executar</button>
    </article>
  `).join("");

  $$("[data-run-job]").forEach((button) => {
    button.addEventListener("click", () => runJob(button.dataset.runJob));
  });
}

function renderDiagrams() {
  const strip = $("#diagramStrip");
  strip.innerHTML = diagrams.map((name, index) => `
    <button class="${index === 0 ? "active" : ""}" type="button" data-diagram="${name}">
      <img src="./assets/${name}" alt="Miniatura do diagrama ${index + 1}">
    </button>
  `).join("");

  $$("#diagramStrip button").forEach((button) => {
    button.addEventListener("click", () => {
      $("#diagramImage").src = `./assets/${button.dataset.diagram}`;
      $$("#diagramStrip button").forEach((item) => item.classList.toggle("active", item === button));
    });
  });
}

function setupPayload() {
  $("#vendorPayload").value = JSON.stringify({
    hostname: "SW-MTZ-CORE-01",
    mgmtIp: "10.10.0.2",
    vendorName: "Cisco",
    ifName: "Gi0/1",
    operStatus: "up",
    bandwidth: 1000000000
  }, null, 2);
}

async function convertPayload() {
  try {
    const payload = JSON.parse($("#vendorPayload").value);
    const canonical = apiOnline
      ? await apiPost("/api/convert", payload)
      : convertLocally(payload);
    $("#canonicalOutput").textContent = JSON.stringify(canonical, null, 2);
  } catch (error) {
    $("#canonicalOutput").textContent = `Payload invalido: ${error.message}`;
  }
}

function convertLocally(payload) {
  return {
    deviceId: payload.hostname || payload.device || "unknown-device",
    managementIp: payload.mgmtIp || payload.ip || "0.0.0.0",
    vendor: payload.vendorName || payload.vendor || "Generic",
    interfaceName: payload.ifName || payload.interface || "unknown-interface",
    status: String(payload.operStatus || payload.status || "unknown").toUpperCase(),
    speed: payload.bandwidth ? `${payload.bandwidth / 1000000000}Gbps` : "unknown",
    normalizedAt: new Date().toISOString()
  };
}

async function acknowledgeAlarms() {
  const selected = $$("#alarmList input:checked").map((input) => Number(input.value));
  if (!selected.length) {
    toast("Selecione pelo menos um alarme para reconhecer.");
    return;
  }

  try {
    if (apiOnline) {
      const data = await apiPost("/api/alarms/ack", { ids: selected });
      state = normalizeState(data);
    } else {
      state.alarms = state.alarms.filter((alarm) => !selected.includes(alarm.id));
    }
    renderAll();
    toast(`${selected.length} alarme(s) reconhecido(s) e auditado(s).`);
  } catch (error) {
    toast(`Falha ao reconhecer alarmes: ${error.message}`);
  }
}

async function simulateTelemetry() {
  try {
    if (apiOnline) {
      const data = await apiPost("/api/telemetry/simulate");
      state = normalizeState(data);
    } else {
      state.devices.forEach((device) => {
        if (device.status !== "DOWN") {
          device.cpu = Math.max(8, Math.min(92, device.cpu + Math.round(Math.random() * 16 - 8)));
          device.status = device.cpu > 72 ? "ALERTA" : "UP";
        }
      });
      state.queueDepth += Math.floor(Math.random() * 120 + 30);
    }
    renderAll();
    toast("Telemetria simulada: metricas, status e fila atualizados.");
  } catch (error) {
    toast(`Falha na simulacao: ${error.message}`);
  }
}

async function discoverDevices() {
  await runJob("device.discovery");
}

async function runJob(queue) {
  try {
    if (apiOnline) {
      const data = await apiPost("/api/jobs/run", { queue });
      state = normalizeState(data);
      renderAll();
    } else {
      state.queueDepth += Math.floor(Math.random() * 120 + 30);
      $("#queueDepth").textContent = new Intl.NumberFormat("pt-BR").format(state.queueDepth);
    }
    toast(`Comando publicado em ${queue}.`);
  } catch (error) {
    toast(`Falha ao publicar comando: ${error.message}`);
  }
}

function statusClass(status) {
  if (status === "UP") return "ok";
  if (status === "DOWN") return "bad";
  return "warn";
}

function severityClass(severity) {
  if (severity === "critical") return "bad";
  if (severity === "warning") return "warn";
  return "ok";
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("show");
  clearTimeout(window.toastTimer);
  window.toastTimer = setTimeout(() => element.classList.remove("show"), 3200);
}

init();
