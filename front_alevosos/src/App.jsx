import React, { useState, useEffect, useMemo, useCallback } from "react";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import esLocale from "@fullcalendar/core/locales/es";
import "./index.css";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/* ====================== Utils ====================== */
async function api(path, { method = "GET", token, body, isForm = false } = {}) {
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isForm) headers["Content-Type"] = "application/json";
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `HTTP ${res.status}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}
function clsx(...args) { return args.filter(Boolean).join(" "); }
function formatCurrency(n) {
  if (typeof n !== "number") return "-";
  try {
    return new Intl.NumberFormat("es-UY", { style: "currency", currency: "UYU", maximumFractionDigits: 0 }).format(n);
  } catch { return `${n}`; }
}
function localISODate() {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 10);
}
function parseMonto(val) {
  let s = String(val ?? "").trim();
  s = s.replace(/\./g, "").replace(",", ".");
  const n = Number(s);
  return Number.isFinite(n) ? n : 0;
}
function toast(msg, type = "ok") {
  const el = document.createElement("div");
  el.className = clsx(
    "fixed right-4 top-4 z-50 rounded-xl px-4 py-2 shadow text-sm",
    type === "ok" && "bg-emerald-600 text-white",
    type === "err" && "bg-red-600 text-white"
  );
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

/* ====================== UI base ====================== */
function Topbar({ userEmail, onLogout }) {
  return (
    <div className="w-full border-b bg-white/60 backdrop-blur sticky top-0 z-20">
      <div className="mx-auto max-w-6xl px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-2xl bg-black text-white grid place-content-center font-bold">AS</div>
          <div className="font-bold text-lg">Alevosos Studio</div>
        </div>
        <div className="flex items-center gap-3">
          {userEmail && <span className="text-sm text-gray-600 hidden sm:inline">{userEmail}</span>}
          {onLogout && <button onClick={onLogout} className="px-3 py-1.5 rounded-xl text-sm bg-gray-900 text-white hover:bg-gray-800">Salir</button>}
        </div>
      </div>
    </div>
  );
}
function Card({ title, actions, children }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-lg">{title}</h3>
        {actions}
      </div>
      {children}
    </div>
  );
}
function Field({ label, children, error }) {
  return (
    <label className="block">
      <span className="text-sm text-gray-700">{label}</span>
      <div className="mt-1">{children}</div>
      {error && <div className="text-xs text-red-600 mt-1">{error}</div>}
    </label>
  );
}
function Tabs({ value, onChange, items }) {
  return (
    <div className="flex gap-2 mb-4 flex-wrap">
      {items.map((it) => (
        <button
          key={it.value}
          onClick={() => onChange(it.value)}
          className={clsx(
            "px-3 py-1.5 rounded-xl text-sm border",
            value === it.value ? "bg-gray-900 text-white border-gray-900" : "bg-white hover:bg-gray-50"
          )}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}

/* ====================== Login ====================== */
function LoginView({ onLogin }) {
  const [username, setUsername] = useState("admin@alevosos.local");
  const [password, setPassword] = useState("admin123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      const form = new URLSearchParams();
      form.append("username", username);
      form.append("password", password);
      const data = await api("/auth/login", { method: "POST", isForm: true, body: form });
      onLogin(data.access_token, username);
      toast("Ingreso correcto");
    } catch (err) {
      console.error(err);
      setError("Usuario o contraseña incorrectos");
      toast("Error de login", "err");
    } finally { setLoading(false); }
  };
  return (
    <div className="min-h-[70vh] grid place-items-center">
      <form onSubmit={submit} className="w-full max-w-sm bg-white p-6 rounded-2xl border shadow-sm">
        <h2 className="text-xl font-bold mb-1">Ingresar</h2>
        <p className="text-sm text-gray-500 mb-6">Alevosos Studio · API</p>
        <div className="space-y-4">
          <Field label="Email"><input value={username} onChange={(e) => setUsername(e.target.value)} required type="email" className="w-full px-3 py-2 rounded-xl border focus:outline-none focus:ring-2 focus:ring-gray-900" /></Field>
          <Field label="Contraseña"><input value={password} onChange={(e) => setPassword(e.target.value)} required type="password" className="w-full px-3 py-2 rounded-xl border focus:outline-none focus:ring-2 focus:ring-gray-900" /></Field>
          {error && <div className="text-sm text-red-600">{error}</div>}
          <button disabled={loading} className="w-full px-4 py-2 rounded-xl bg-gray-900 text-white hover:bg-gray-800">
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </div>
        <div className="text-xs text-gray-400 mt-4">
          Tip: por defecto existe <b>admin@alevosos.local</b> / <b>admin123</b>
        </div>
      </form>
    </div>
  );
}

/* ====================== Clientes ====================== */
function Clientes({ token }) {
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [f, setF] = useState({ nombre: "", apellido: "", email: "", edad: "", celular: "" });
  const load = async () => {
    setLoading(true);
    try { setList(await api("/clientes/", { token })); }
    catch { toast("No se pudo cargar clientes", "err"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const crear = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        nombre: f.nombre, apellido: f.apellido, email: f.email || null,
        edad: f.edad ? Number(f.edad) : null, celular: f.celular || null,
      };
      await api("/clientes/", { method: "POST", token, body: payload });
      setF({ nombre: "", apellido: "", email: "", edad: "", celular: "" });
      await load(); toast("Cliente creado");
    } catch { toast("Error al crear cliente", "err"); }
  };
  return (
    <div className="grid md:grid-cols-2 gap-6">
      <Card title="Nuevo cliente">
        <form onSubmit={crear} className="grid gap-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Nombre"><input value={f.nombre} onChange={(e)=>setF({...f, nombre:e.target.value})} required className="w-full px-3 py-2 rounded-xl border"/></Field>
            <Field label="Apellido"><input value={f.apellido} onChange={(e)=>setF({...f, apellido:e.target.value})} required className="w-full px-3 py-2 rounded-xl border"/></Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Email"><input value={f.email} onChange={(e)=>setF({...f, email:e.target.value})} type="email" className="w-full px-3 py-2 rounded-xl border"/></Field>
            <Field label="Edad"><input value={f.edad} onChange={(e)=>setF({...f, edad:e.target.value})} type="number" className="w-full px-3 py-2 rounded-xl border"/></Field>
          </div>
          <Field label="Celular"><input value={f.celular} onChange={(e)=>setF({...f, celular:e.target.value})} className="w-full px-3 py-2 rounded-xl border"/></Field>
          <div className="flex justify-end">
            <button className="px-4 py-2 rounded-xl bg-gray-900 text-white hover:bg-gray-800">Guardar</button>
          </div>
        </form>
      </Card>
      <Card title="Listado de clientes">
        {loading ? <div className="text-sm text-gray-500">Cargando...</div> : (
          <div className="max-h-[420px] overflow-auto rounded-xl border">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr><th className="text-left p-2">ID</th><th className="text-left p-2">Nombre</th><th className="text-left p-2">Email</th><th className="text-left p-2">Celular</th></tr>
              </thead>
              <tbody>
                {list.map((c) => (
                  <tr key={c.id} className="border-t hover:bg-gray-50">
                    <td className="p-2">{c.id}</td>
                    <td className="p-2">{c.nombre} {c.apellido}</td>
                    <td className="p-2">{c.email || "-"}</td>
                    <td className="p-2">{c.celular || "-"}</td>
                  </tr>
                ))}
                {list.length === 0 && (<tr><td className="p-3 text-gray-500" colSpan={4}>No hay clientes aún</td></tr>)}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

/* ====================== Ventas ====================== */
function Ventas({ token }) {
  const [clientes, setClientes] = useState([]);
  const [servicios, setServicios] = useState([]);
  const [list, setList] = useState([]);
  const [f, setF] = useState({
    cliente_id: "", servicio_id: "", monto: "", medio_pago: "efectivo", fecha: localISODate(), nota: ""
  });
  const [loading, setLoading] = useState(true);
  const load = async () => {
    setLoading(true);
    try {
      const [cl, sv, ve] = await Promise.all([
        api("/clientes/", { token }),
        api("/servicios/", { token }),
        api("/ventas/", { token }),
      ]);
      setClientes(cl); setServicios(sv); setList(ve);
      if (!f.servicio_id && sv[0]) setF((x) => ({ ...x, servicio_id: sv[0].id }));
    } catch { toast("Error cargando datos", "err"); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  const crear = async (e) => {
    e.preventDefault();
    try {
      if (!f.servicio_id || !f.monto || !f.fecha) throw new Error("Faltan datos");
      const payload = {
        cliente_id: f.cliente_id ? Number(f.cliente_id) : null,
        servicio_id: Number(f.servicio_id),
        monto: parseMonto(f.monto),
        medio_pago: f.medio_pago,
        fecha: f.fecha,
        nota: f.nota || null,
      };
      await api("/ventas/", { method: "POST", token, body: payload });
      setF(x => ({ ...x, cliente_id: "", monto: "", nota: "", fecha: localISODate() }));
      await load(); toast("Venta registrada");
    } catch (e) { toast(e.message || "No se pudo registrar la venta", "err"); }
  };
  return (
    <div className="grid md:grid-cols-2 gap-6">
      <Card title="Registrar venta">
        <form onSubmit={crear} className="grid gap-3">
          <Field label="Cliente (opcional)">
            <select value={f.cliente_id} onChange={(e)=>setF({...f, cliente_id:e.target.value})} className="w-full px-3 py-2 rounded-xl border">
              <option value="">Sin cliente</option>
              {clientes.map(c => <option key={c.id} value={c.id}>{c.nombre} {c.apellido}</option>)}
            </select>
          </Field>
          <Field label="Servicio">
            <select value={f.servicio_id} onChange={(e)=>setF({...f, servicio_id:e.target.value})} required className="w-full px-3 py-2 rounded-xl border">
              <option value="">Elegí...</option>
              {servicios.map(s => <option key={s.id} value={s.id}>{s.nombre}</option>)}
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Monto"><input type="text" value={f.monto} onChange={(e)=>setF({...f, monto:e.target.value})} placeholder="Ej: 3.123" className="w-full px-3 py-2 rounded-xl border"/></Field>
            <Field label="Fecha"><input type="date" value={f.fecha} onChange={(e)=>setF({...f, fecha:e.target.value})} required className="w-full px-3 py-2 rounded-xl border"/></Field>
          </div>
          <Field label="Medio de pago">
            <div className="flex gap-2">
              {["efectivo","transferencia","handy"].map(m => (
                <label key={m} className={clsx("px-3 py-1.5 rounded-xl border cursor-pointer", f.medio_pago===m?"bg-gray-900 text-white border-gray-900":"bg-white hover:bg-gray-50") }>
                  <input type="radio" name="medio" className="hidden" checked={f.medio_pago===m} onChange={()=>setF({...f, medio_pago:m})}/>
                  {m}
                </label>
              ))}
            </div>
          </Field>
          <Field label="Nota"><textarea value={f.nota} onChange={(e)=>setF({...f, nota:e.target.value})} rows={2} className="w-full px-3 py-2 rounded-xl border"/></Field>
          <div className="flex justify-end"><button className="px-4 py-2 rounded-xl bg-gray-900 text-white hover:bg-gray-800">Guardar</button></div>
        </form>
      </Card>
      <Card title="Últimas ventas">
        {loading ? <div className="text-sm text-gray-500">Cargando...</div> : (
          <div className="max-h-[420px] overflow-auto rounded-xl border">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr><th className="text-left p-2">Fecha</th><th className="text-left p-2">Servicio</th><th className="text-left p-2">Monto</th><th className="text-left p-2">Medio</th></tr>
              </thead>
              <tbody>
                {list.map(v => (
                  <tr key={v.id} className="border-t hover:bg-gray-50">
                    <td className="p-2">{v.fecha}</td>
                    <td className="p-2">#{v.servicio_id}</td>
                    <td className="p-2">{formatCurrency(v.monto)}</td>
                    <td className="p-2 uppercase">{v.medio_pago}</td>
                  </tr>
                ))}
                {list.length === 0 && (<tr><td className="p-3 text-gray-500" colSpan={4}>No hay ventas</td></tr>)}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

/* ====================== Reportes ====================== */
function toYMDLocal(d) { const x = new Date(d); x.setMinutes(x.getMinutes() - x.getTimezoneOffset()); return x.toISOString().slice(0, 10); }
function fromYMDLocal(s) { const [y,m,d] = s.split("-").map(Number); return new Date(y, m-1, d); }
function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate() + n); return x; }
function addMonths(d, n) { const x = new Date(d); const day = x.getDate(); x.setMonth(x.getMonth() + n, 1); const last = new Date(x.getFullYear(), x.getMonth()+1, 0).getDate(); x.setDate(Math.min(day, last)); return x; }
function startOfWeekMon(d) { const x = new Date(d); const dow = (x.getDay() + 6) % 7; return addDays(new Date(x.getFullYear(), x.getMonth(), x.getDate()), -dow); }
function endOfWeekMon(d) { return addDays(startOfWeekMon(d), 6); }
function firstOfMonth(d) { return new Date(d.getFullYear(), d.getMonth(), 1); }
function lastOfMonth(d) { return new Date(d.getFullYear(), d.getMonth() + 1, 0); }

function Reportes({ token }) {
  const [modo, setModo] = useState("diario");
  const [ancla, setAncla] = useState(() => new Date());
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const rango = useMemo(() => {
    if (modo === "diario") {
      const d = toYMDLocal(ancla);
      return { desde: d, hasta: d, etiqueta: d };
    }
    if (modo === "semanal") {
      const ini = startOfWeekMon(ancla); const fin = endOfWeekMon(ancla);
      return { desde: toYMDLocal(ini), hasta: toYMDLocal(fin), etiqueta: `${toYMDLocal(ini)} → ${toYMDLocal(fin)}` };
    }
    const ini = firstOfMonth(ancla); const fin = lastOfMonth(ancla);
    return { desde: toYMDLocal(ini), hasta: toYMDLocal(fin), etiqueta: `${toYMDLocal(ini)} → ${toYMDLocal(fin)}` };
  }, [modo, ancla]);
  const cargar = async () => {
    setLoading(true);
    try { setData(await api(`/reportes/resumen?desde=${rango.desde}&hasta=${rango.hasta}`, { token })); }
    catch { toast("No se pudo cargar el reporte", "err"); }
    finally { setLoading(false); }
  };
  useEffect(() => { cargar(); }, [rango.desde, rango.hasta]);
  const goPrev = () => setAncla(a => (modo === "diario" ? addDays(a, -1) : modo === "semanal" ? addDays(a, -7) : addMonths(a, -1)));
  const goNext = () => setAncla(a => (modo === "diario" ? addDays(a, 1) : modo === "semanal" ? addDays(a, 7) : addMonths(a, 1)));
  const goToday = () => setAncla(new Date());
  const medioArr = useMemo(() => !data ? [] : Object.entries(data.por_medio || {}).map(([k, v]) => ({ medio: k, total: v })), [data]);

  return (
    <div className="grid gap-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <Tabs value={modo} onChange={(v) => { setModo(v); setAncla(new Date()); }}
          items={[{ value: "diario", label: "Diario" }, { value: "semanal", label: "Semanal" }, { value: "mensual", label: "Mensual" }]} />
        <div className="flex items-center gap-2">
          <button onClick={goPrev} className="px-3 py-1.5 rounded-xl border">◀</button>
          <input type="date" value={toYMDLocal(ancla)} onChange={(e) => setAncla(fromYMDLocal(e.target.value))} className="px-3 py-1.5 rounded-xl border"/>
          <button onClick={goNext} className="px-3 py-1.5 rounded-xl border">▶</button>
          <button onClick={goToday} className="px-3 py-1.5 rounded-xl border">Hoy</button>
          <button onClick={cargar} className="px-3 py-1.5 rounded-xl border">Actualizar</button>
        </div>
      </div>
      <div className="text-sm text-gray-600">{modo === "diario" ? `Día: ${rango.etiqueta}` : `Rango: ${rango.etiqueta}`}</div>
      {loading ? <div className="text-sm text-gray-500">Cargando...</div> : data ? (
        <div className="grid md:grid-cols-3 gap-6">
          <Card title="Ingresos"><div className="text-3xl font-bold">{formatCurrency(data.ingresos)}</div><div className="text-xs text-gray-500 mt-1">{rango.desde} → {rango.hasta}</div></Card>
          <Card title="Gastos"><div className="text-3xl font-bold">{formatCurrency(data.gastos)}</div><div className="text-xs text-gray-500 mt-1">{rango.desde} → {rango.hasta}</div></Card>
          <Card title="Neto"><div className={clsx("text-3xl font-bold", (data.neto ?? 0) >= 0 ? "text-emerald-600" : "text-red-600")}>{formatCurrency(data.neto ?? 0)}</div><div className="text-xs text-gray-500 mt-1">{rango.desde} → {rango.hasta}</div></Card>
          <Card title="Ingresos por medio de pago">
            <div className="grid gap-2">
              {medioArr.map((m) => (<div key={m.medio} className="flex items-center justify-between text-sm"><span className="uppercase text-gray-600">{m.medio}</span><span className="font-semibold">{formatCurrency(m.total)}</span></div>))}
              {medioArr.length === 0 && <div className="text-sm text-gray-500">Sin datos</div>}
            </div>
          </Card>
        </div>
      ) : <div className="text-sm text-gray-500">Sin datos</div>}
    </div>
  );
}

/* ====================== Agenda (FullCalendar) ====================== */
function CalendarView() {
  const calRef = React.useRef(null);
  const [title, setTitle] = React.useState('');
  const [viewName, setViewName] = React.useState('timeGridWeek');

  // Header de días (DOW + número)
  const renderDayHeader = (arg) => {
    const d = arg.date;
    const dow = d.toLocaleDateString('es-ES', { weekday: 'short' }).replace('.', '').toUpperCase();
    const day = d.getDate();
    return { html: `<div class="fc-dow">${dow}</div><div class="fc-daynum">${day}</div>` };
  };

  const roundToStep = (d, step = 15) => new Date(Math.ceil(d.getTime() / (step*60000)) * (step*60000));
  const gotoPrev  = () => calRef.current?.getApi().prev();
  const gotoNext  = () => calRef.current?.getApi().next();
  const gotoToday = () => calRef.current?.getApi().today();
  const changeView = (v) => { setViewName(v); calRef.current?.getApi().changeView(v); };

  const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const token = typeof window !== "undefined" ? (localStorage.getItem("alev.token") || localStorage.getItem("token") || "") : "";

  const [events, setEvents] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [barberId, setBarberId] = React.useState("");
  const [range, setRange] = React.useState({ start: null, end: null });

  const [services, setServices] = React.useState([]);
  React.useEffect(() => {
    if (!token) return;
    fetch(`${API}/servicios/`, { headers:{ Authorization:`Bearer ${token}` }}).then(r => r.ok ? r.json() : [])
      .then(d => setServices(Array.isArray(d) ? d : []))
      .catch(() => setServices([]));
  }, [API, token]);

  const [clients, setClients] = React.useState([]);
  React.useEffect(() => {
    if (!token) return;
    fetch(`${API}/clientes/`, { headers:{ Authorization:`Bearer ${token}` }}).then(r => r.ok ? r.json() : [])
      .then(d => setClients(Array.isArray(d) ? d : []))
      .catch(() => setClients([]));
  }, [API, token]);

  const plugins = React.useMemo(() => [timeGridPlugin, dayGridPlugin, interactionPlugin], []);
  const locales = React.useMemo(() => [esLocale], []);
  const tokenRef  = React.useRef(token);
  const barberRef = React.useRef(barberId);
  React.useEffect(() => { tokenRef.current = token; }, [token]);
  React.useEffect(() => { barberRef.current = barberId; }, [barberId]);

  // Clases por estado (se mantienen) y tono Notion (nuevo)
  const stateClass = React.useCallback((s) => {
    const v = (s || "").toLowerCase();
    if (v === "cancelada") return ["fc-ev-cancel"];
    if (["no_show","no show","noshow"].includes(v)) return ["fc-ev-noshow"];
    if (["confirmada","completada"].includes(v)) return ["fc-ev-ok"];
    return [];
  }, []);
  const eventClassNames = React.useCallback((arg) => {
    const xp = arg.event.extendedProps || {};
    let tone = xp.tone;
    if (!tone) {
      const est = (xp.estado || "").toLowerCase();
      if (["confirmada","completada"].includes(est)) tone = "green";
      else if (est === "cancelada") tone = "red";
      else if (["no_show","no show","noshow"].includes(est)) tone = "yellow";
      else tone = "blue";
    }
    return [`tone-${tone}`, ...stateClass(xp.estado)];
  }, [stateClass]);

  function toLocalSQL(d) {
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }
  // Helpers (arriba de fetchEvents)
  const toDateSafe = (v) => {
    if (v instanceof Date) return v;
    if (typeof v === "number") return new Date(v);
    if (typeof v === "string") {
      let s = v.trim();
      // "YYYY-MM-DD HH:mm:ss" -> "YYYY-MM-DDTHH:mm:ss" (FullCalendar/Date lo entiende)
      if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(s)) s = s.replace(" ", "T");
      // si viene sin segundos
      if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(s)) s += ":00";
      const d = new Date(s);
      return isNaN(d) ? null : d;
    }
    return null;
  };
  const toMinutes = (m, fallback = 30) => {
    if (typeof m === "number") return m;
    const n = parseInt(String(m ?? "").replace(/[^\d]/g, ""), 10);
    return Number.isFinite(n) ? n : fallback;
  };
  const fetchEvents = React.useCallback(async (start, end) => {
    if (!tokenRef.current || !start || !end) return;
    setLoading(true);
    try {
      const url = new URL(`${API}/citas/calendario`);
      url.searchParams.set("desde", toLocalSQL(start));
      url.searchParams.set("hasta", toLocalSQL(end));
      if (barberRef.current) url.searchParams.set("barber_id", barberRef.current);
      const res  = await fetch(url.toString(), { headers:{ Authorization:`Bearer ${tokenRef.current}` }});
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      setEvents(
        data.map((ev) => {
          const start = toDateSafe(ev.start);
          let end = toDateSafe(ev.end);
          const mins = toMinutes(ev.duracion_min, 30);

          if (!end && start) end = new Date(start.getTime() + mins * 60000);

          const dur = start && end ? Math.max(5, Math.round((end - start) / 60000)) : mins;

          return {
            id: String(ev.id),
            title: ev.title || "Cita",
            start, end,
            extendedProps: {
              estado: ev.estado,
              barber: ev.barber,
              medio: ev.medio_reserva,
              notas: ev.notas,
              duracion_min: dur,
              barber_id: ev.barber_id,
              tone: ev.tone || null,
            },
          };
        })
      );
    } catch (e) {
      console.error(e);
      setEvents([]);
    } finally { setLoading(false); }
  }, [API, stateClass]);

  const onDatesSet = React.useCallback((arg) => {
    setRange({ start: arg.start, end: arg.end });
    setTitle(arg.view.title);
    setViewName(arg.view.type);         // <— mantiene sync la vista actual
    fetchEvents(arg.start, arg.end);
  }, [fetchEvents]);

  React.useEffect(() => {
    if (range.start && range.end) fetchEvents(range.start, range.end);
  }, [barberId]); // eslint-disable-line

  // Popover edición (igual que tenías)
  const [pop, setPop] = React.useState({ open:false, ev:null, pos:{x:0,y:0,side:"right"} });
  const onEventClick = React.useCallback((info) => {
    const e  = info.event;
    const xp = e.extendedProps || {};
    const d  = new Date(e.start);
    const pad = (n)=> String(n).padStart(2,'0');
    const inicio = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    const rect = info.el.getBoundingClientRect();
    const GAP = 12, cardW = 340, cardH = 300;
    const preferRight = rect.right + cardW + GAP < window.innerWidth;
    let x = preferRight ? rect.right + GAP : rect.left - cardW - GAP;
    let y = rect.top;
    const minX = 8, minY = 8, maxX = window.innerWidth - cardW - 8, maxY = window.innerHeight - cardH - 8;
    x = Math.max(minX, Math.min(x, maxX)); y = Math.max(minY, Math.min(y, maxY));
    setPop({ open: true, pos: { x, y, side: preferRight ? "right" : "left" },
      ev: { id: e.id, barber_id: xp.barber_id || 1, inicio,
            duracion_min: xp.duracion_min || (e.end ? Math.round((e.end - e.start)/60000) : 30),
            estado: xp.estado || "agendada", notas: xp.notas || "" }});
  }, []);

  // Modal nueva cita (igual que tenías)
  const [open, setOpen] = React.useState(false);
  const [form, setForm] = React.useState({ inicio: "", cliente_id: "", servicio_id: "", duracion_min: 30, barber_id: "", notas: "" });
  const fmtLocal = (d) => { const z = new Date(d.getTime() - d.getTimezoneOffset() * 60000); return z.toISOString().slice(0, 16); };
  const onSelect = React.useCallback((arg) => {
    const start = arg.start;
    const end   = arg.end && arg.end > start ? arg.end : new Date(start.getTime() + 30*60000);
    const mins  = Math.max(15, Math.round((end - start)/60000));
    setForm(f => ({ ...f, inicio: fmtLocal(start), duracion_min: mins, barber_id: barberRef.current || "" }));
    setOpen(true);
  }, []);
  React.useEffect(() => {
    const s = services.find(x => String(x.id) === String(form.servicio_id));
    if (s && s.duracion_min) setForm(f => ({ ...f, duracion_min: s.duracion_min }));
  }, [form.servicio_id]); // eslint-disable-line
  const crearCita = async () => {
    try {
      const body = {
        cliente_id: form.cliente_id ? Number(form.cliente_id) : null,
        servicio_id: form.servicio_id ? Number(form.servicio_id) : null,
        barber_id: form.barber_id ? Number(form.barber_id) : (barberRef.current ? Number(barberRef.current) : 1),
        inicio: toLocalSQL(new Date(form.inicio)),
        duracion_min: Number(form.duracion_min),
        medio_reserva: "online",
        notas: form.notas || ""
      };
      const res = await fetch(`${API}/citas`, {
        method: "POST",
        headers: { "Content-Type":"application/json", Authorization:`Bearer ${tokenRef.current}` },
        body: JSON.stringify(body)
      });
      if (!res.ok) throw new Error(await res.text());
      setOpen(false);
      if (range.start && range.end) fetchEvents(range.start, range.end);
    } catch (e) { console.error(e); alert(e.message || "No se pudo crear la cita"); }
  };

  // Render de eventos + DnD (igual que tenías)
  const Pill = ({children}) => <span className="ev-chip">{children}</span>;
  const renderNiceEvent = (arg) => {
    const e  = arg.event;
    const xp = e.extendedProps || {};
    const mins = xp.duracion_min ?? Math.round((e.end - e.start)/60000);
    const small  = mins < 45;
    const medium = mins >= 45 && mins < 90;
    const large  = mins >= 90;
    const hhmm = (d) => d?.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    return (
      <div className="ev-card">
        <div className="ev-top">
          <span className="ev-time">{hhmm(e.start)}</span>
          {e.end && <><span className="ev-dot">•</span><span className="ev-time">{hhmm(e.end)}</span></>}
        </div>
        <div className="ev-title">{e.title}</div>
        {!small && <div className="ev-sub">Barbero: {xp.barber || '—'}</div>}
        {(medium || large) && (
          <div className="ev-chips">
            {xp.estado && <Pill>{xp.estado}</Pill>}
            {xp.medio  && <Pill>{xp.medio}</Pill>}
            <Pill>{mins} min</Pill>
          </div>
        )}
        {large && xp.notas && <div className="ev-notes">{xp.notas}</div>}
      </div>
    );
  };
  const handleDrop = async (info) => {
    try {
      const id = info.event.id;
      const inicio = toLocalSQL(info.event.start);
      const duracion = info.event.end
        ? Math.round((info.event.end - info.event.start) / 60000)
        : Number(info.event.extendedProps.duracion_min || 30);
      const body = { inicio, duracion_min: duracion, barber_id: Number(info.event.extendedProps.barber_id || 1) };
      const res = await fetch(`${API}/citas/${id}`, {
        method: "PUT",
        headers: { "Content-Type":"application/json", Authorization: `Bearer ${tokenRef.current}` },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      toast("Cita actualizada");
    } catch (e) {
      console.error(e); toast("Error actualizando cita", "err"); info.revert();
    }
  };
  const eventDidMount = (info) => {
    const p = info.event.extendedProps || {};
    const fmt = (d) => d ? d.toLocaleString() : '';
    info.el.title =
      `${info.event.title}\n` +
      `${fmt(info.event.start)} — ${fmt(info.event.end)}\n` +
      (p.barber ? `Barbero: ${p.barber}\n` : '') +
      (p.estado ? `Estado: ${p.estado}\n` : '') +
      (p.medio  ? `Medio: ${p.medio}\n` : '') +
      (p.notas  ? `Notas: ${p.notas}` : '');
  };
  const handleResize = (info) => handleDrop(info);

  /* ===== Mini calendario ===== */
  const miniRef = React.useRef(null);
  const [miniSelected, setMiniSelected] = React.useState(new Date());
  const sameDate = (a, b) => a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
  const [miniMonthLabel, setMiniMonthLabel] = React.useState('');
  const onMiniDatesSet = (arg) => {
    const m = arg.start.toLocaleDateString('es-ES', { month: 'long' });
    setMiniMonthLabel(m.charAt(0).toUpperCase() + m.slice(1));
  };
  const miniPrev = () => miniRef.current?.getApi().prev();
  const miniNext = () => miniRef.current?.getApi().next();

  // si ya lo tenés, reusalo
  const isMonth = viewName === "dayGridMonth";

  // wrapper: alto y scroll sólo en Día/Semana
  const wrapStyle = React.useMemo(
    () => (isMonth ? undefined : { height: "calc(100vh - 180px)", overflowY: "auto" }),
    [isMonth]
  );

  // altura que FullCalendar debe usar dentro del wrapper
  const fcHeight = isMonth ? "auto" : "100%";



  return (
    <div className="p-4">
      {/* Filtros simples */}
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <div className="text-lg font-semibold">Agenda</div>
        <div className="flex items-center gap-2">
          <label className="text-sm">Barbero (ID)</label>
          <input type="number" min={1} placeholder="(todos)" className="border rounded px-2 py-1 w-28" value={barberId} onChange={(e)=> setBarberId(e.target.value)} />
        </div>
        {loading && <div className="text-sm opacity-70">Cargando…</div>}
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Sidebar */}
        <aside className="col-span-12 lg:col-span-3 xl:col-span-2">
          <div className="bg-white rounded-2xl border shadow-sm p-3 mb-3">
            <button
              onClick={() => {
                const start = roundToStep(new Date(), 15);
                setForm(f => ({ ...f, inicio: fmtLocal(start), duracion_min: f.duracion_min || 30, barber_id: barberRef.current || '' }));
                setOpen(true);
              }}
              className="w-full px-3 py-2 rounded-xl bg-gray-900 text-white hover:bg-gray-800"
            >Crear</button>
          </div>

          <div className="bg-white rounded-2xl border shadow-sm mini-cal-wrap">
            <div className="flex items-center justify-between mb-2">
              <div className="mini-cal-title">{miniMonthLabel || '—'}</div>
              <div className="mini-cal-nav flex items-center gap-1">
                <button onClick={miniPrev} aria-label="Mes anterior">‹</button>
                <button onClick={miniNext} aria-label="Mes siguiente">›</button>
              </div>
            </div>

            <div className="mini-cal">
              <FullCalendar
                ref={miniRef}
                plugins={[dayGridPlugin, interactionPlugin]}
                locale="es"
                locales={locales}
                headerToolbar={false}
                initialView="dayGridMonth"
                fixedWeekCount={false}
                showNonCurrentDates={true}
                height="auto"
                dayHeaderFormat={{ weekday: 'narrow' }}
                events={[]}
                datesSet={onMiniDatesSet}
                dayCellClassNames={(arg) => sameDate(arg.date, miniSelected) ? 'is-selected' : ''}
                dateClick={(info) => {
                  setMiniSelected(info.date);
                  calRef.current?.getApi().gotoDate(info.date);
                  if (viewName !== 'timeGridWeek') changeView('timeGridWeek');
                }}
              />
            </div>
          </div>
        </aside>

        {/* Calendario principal */}
        <div className="col-span-12 lg:col-span-9 xl:col-span-10">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <button onClick={gotoPrev} className="px-2.5 py-1.5 rounded-xl border">‹</button>
              <button onClick={gotoNext} className="px-2.5 py-1.5 rounded-xl border">›</button>
              <button onClick={gotoToday} className="px-3 py-1.5 rounded-xl border">Hoy</button>
              <div className="ml-2 text-lg font-semibold">{title || 'Agenda'}</div>
            </div>
            <div className="flex items-center gap-1 bg-gray-100 rounded-xl p-1">
              <button onClick={() => changeView('timeGridDay')}   className={`px-3 py-1.5 rounded-lg text-sm ${viewName==='timeGridDay'   ? 'bg-white shadow' : ''}`}>Día</button>
              <button onClick={() => changeView('timeGridWeek')}  className={`px-3 py-1.5 rounded-lg text-sm ${viewName==='timeGridWeek'  ? 'bg-white shadow' : ''}`}>Semana</button>
              <button onClick={() => changeView('dayGridMonth')}  className={`px-3 py-1.5 rounded-lg text-sm ${viewName==='dayGridMonth'  ? 'bg-white shadow' : ''}`}>Mes</button>
            </div>
          </div>

          {/* Wrap de scroll vertical SOLO en mes */}
          <div className={isMonth ? "calendar-month-wrap" : ""} style={wrapStyle}>
            <div className="calendar-scroll rounded-xl shadow ring-1 ring-black/5 overflow-hidden bg-white big-cal">
              <FullCalendar
                ref={calRef}
                dayHeaderContent={renderDayHeader}
                timeZone="local"
                className="big-cal"
                plugins={plugins}
                locales={locales}
                locale="es"
                initialView="timeGridWeek"
                allDaySlot={false}
                slotMinTime="08:00:00"
                slotMaxTime="21:00:00"
                slotDuration="00:30:00"
                nowIndicator={true}
                weekends={true}

                /* 👇 clave: usar toda la altura del wrapper en día/semana */
                height={fcHeight}

                headerToolbar={false}
                events={events}
                datesSet={onDatesSet}
                selectable={true}
                selectMirror={true}
                select={onSelect}
                editable={true}
                eventDurationEditable={true}
                eventDrop={handleDrop}
                eventResize={handleResize}
                eventClick={onEventClick}
                eventContent={renderNiceEvent}
                eventDidMount={eventDidMount}
                dayMaxEventRows={3}
                moreLinkClick="popover"
                firstDay={1}
                expandRows={true}
                eventClassNames={eventClassNames}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Modal nueva cita */}
      {open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-4 space-y-3">
            <div className="text-lg font-semibold">Nueva cita</div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm">Inicio</label>
                <input type="datetime-local" className="border rounded px-2 py-1 w-full"
                  value={form.inicio}
                  onChange={e=> setForm(f=>({...f, inicio:e.target.value}))}/>
              </div>
              <div>
                <label className="text-sm">Duración (min)</label>
                <input type="number" min={5} step={5} className="border rounded px-2 py-1 w-full"
                  value={form.duracion_min}
                  onChange={e=> setForm(f=>({...f, duracion_min:e.target.value}))}/>
              </div>
              <div className="col-span-2">
                <label className="text-sm">Servicio</label>
                <select className="border rounded px-2 py-1 w-full"
                  value={form.servicio_id}
                  onChange={e=> setForm(f=>({...f, servicio_id:e.target.value}))}>
                  <option value="">(sin servicio)</option>
                  {services.map(s => <option key={s.id} value={s.id}>{s.nombre} · {s.duracion_min} min</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm">Cliente</label>
                <select className="border rounded px-2 py-1 w-full"
                  value={form.cliente_id}
                  onChange={e=> setForm(f=>({...f, cliente_id:e.target.value}))}>
                  <option value="">(sin cliente)</option>
                  {clients.map(c => <option key={c.id} value={c.id}>{c.nombre} {c.apellido || ""} #{c.id}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm">Barbero (ID)</label>
                <input type="number" min={1} className="border rounded px-2 py-1 w-full"
                  value={form.barber_id}
                  onChange={e=> setForm(f=>({...f, barber_id:e.target.value}))}/>
              </div>
              <div className="col-span-2">
                <label className="text-sm">Notas</label>
                <textarea className="border rounded px-2 py-1 w-full" rows={2}
                  value={form.notas}
                  onChange={e=> setForm(f=>({...f, notas:e.target.value}))}/>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={()=>setOpen(false)} className="px-3 py-1 rounded border">Cancelar</button>
              <button onClick={crearCita} className="px-3 py-1 rounded bg-blue-600 text-white">Crear</button>
            </div>
          </div>
        </div>
      )}

     
      {pop.open && pop.ev && (
        <div
          className="fixed inset-0 z-50"
          onClick={() =>
            setPop({ open: false, ev: null, pos: { x: 0, y: 0, side: "right" } })
          }
        >
          <div
            className="absolute bg-white shadow-xl rounded-xl border p-3 w-[340px]"
            style={{ top: pop.pos.y, left: pop.pos.x }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-1">
              <div className="font-semibold">Editar cita #{pop.ev.id}</div>
              <button
                onClick={() =>
                  setPop({ open: false, ev: null, pos: { x: 0, y: 0, side: "right" } })
                }
                className="px-2 py-1 rounded hover:bg-gray-100"
              >
                ✕
              </button>
            </div>

            <div className="grid gap-2">
              <div>
                <label className="text-xs">Inicio</label>
                <input
                  type="datetime-local"
                  className="border rounded px-2 py-1 w-full"
                  value={pop.ev.inicio.slice(0, 16)}
                  onChange={(e) =>
                    setPop((p) => ({
                      ...p,
                      ev: { ...p.ev, inicio: e.target.value + ":00" },
                    }))
                  }
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs">Duración</label>
                  <input
                    type="number"
                    min={5}
                    step={5}
                    className="border rounded px-2 py-1 w-full"
                    value={pop.ev.duracion_min}
                    onChange={(e) =>
                      setPop((p) => ({
                        ...p,
                        ev: { ...p.ev, duracion_min: Number(e.target.value) },
                      }))
                    }
                  />
                </div>
                <div>
                  <label className="text-xs">Estado</label>
                  <select
                    className="border rounded px-2 py-1 w-full"
                    value={pop.ev.estado}
                    onChange={(e) =>
                      setPop((p) => ({ ...p, ev: { ...p.ev, estado: e.target.value } }))
                    }
                  >
                    <option value="agendada">Agendada</option>
                    <option value="confirmada">Confirmada</option>
                    <option value="completada">Completada</option>
                    <option value="cancelada">Cancelada</option>
                    <option value="no_show">No show</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs">Notas</label>
                <textarea
                  rows={2}
                  className="border rounded px-2 py-1 w-full"
                  value={pop.ev.notas}
                  onChange={(e) =>
                    setPop((p) => ({ ...p, ev: { ...p.ev, notas: e.target.value } }))
                  }
                />
              </div>

              <div className="flex gap-2 pt-1">
                <button
                  onClick={async () => {
                    try {
                      const qs = new URLSearchParams({
                        barber_id: String(pop.ev.barber_id),
                        inicio: pop.ev.inicio,
                        duracion_min: String(pop.ev.duracion_min),
                        excluir_id: String(pop.ev.id),
                      });
                      const pre = await fetch(`${API}/citas/conflictos?${qs.toString()}`, {
                        headers: { Authorization: `Bearer ${tokenRef.current}` },
                      }).then((r) => r.json());
                      if (pre.conflicto) {
                        alert(
                          `Conflicto con cita #${pre.con.id} (${pre.con.inicio} → ${pre.con.fin})`
                        );
                        return;
                      }
                      const body = {
                        inicio: pop.ev.inicio,
                        duracion_min: pop.ev.duracion_min,
                        barber_id: pop.ev.barber_id,
                        estado: pop.ev.estado,
                        notas: pop.ev.notas || null,
                      };
                      const res = await fetch(`${API}/citas/${pop.ev.id}`, {
                        method: "PUT",
                        headers: {
                          "Content-Type": "application/json",
                          Authorization: `Bearer ${tokenRef.current}`,
                        },
                        body: JSON.stringify(body),
                      });
                      if (!res.ok) throw new Error(await res.text());
                      setPop({ open: false, ev: null, pos: { x: 0, y: 0, side: "right" } });
                      if (range.start && range.end) fetchEvents(range.start, range.end);
                    } catch (e) {
                      console.error(e);
                      alert("Error al guardar");
                    }
                  }}
                  className="px-3 py-1.5 rounded bg-blue-600 text-white text-sm"
                >
                  Guardar
                </button>

                <button
                  onClick={async () => {
                    if (!confirm("¿Eliminar esta cita?")) return;
                    try {
                      const res = await fetch(`${API}/citas/${pop.ev.id}`, {
                        method: "DELETE",
                        headers: { Authorization: `Bearer ${tokenRef.current}` },
                      });
                      if (!res.ok) throw new Error(await res.text());
                      setPop({ open: false, ev: null, pos: { x: 0, y: 0, side: "right" } });
                      if (range.start && range.end) fetchEvents(range.start, range.end);
                    } catch (e) {
                      console.error(e);
                      alert("No se pudo eliminar");
                    }
                  }}
                  className="px-3 py-1.5 rounded border text-sm"
                >
                  Eliminar
                </button>
              </div>
            </div>

            <div
              className="absolute w-3 h-3 bg-white border rotate-45"
              style={{
                top: 10,
                left: pop.pos.side === "right" ? -6 : undefined,
                right: pop.pos.side === "left" ? -6 : undefined,
                borderTopColor: "transparent",
                borderLeftColor: "transparent",
              }}
            />
          </div>
        </div>
      )}
  </div>   
  );
}

/* ====================== App ====================== */
export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("alev.token") || "");
  const [userEmail, setUserEmail] = useState(() => localStorage.getItem("alev.user") || "");
  const [tab, setTab] = useState("clientes");

  const handleLogin = (tk, email) => {
    localStorage.setItem("alev.token", tk);
    localStorage.setItem("alev.user", email);
    setToken(tk); setUserEmail(email);
  };
  const handleLogout = () => {
    localStorage.removeItem("alev.token");
    localStorage.removeItem("alev.user");
    setToken(""); setUserEmail("");
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100">
        <div className="mx-auto max-w-6xl px-4 py-6">
          <Topbar userEmail={null} onLogout={null} />
          <LoginView onLogin={handleLogin} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100">
      <Topbar userEmail={userEmail} onLogout={handleLogout} />
      <div className="mx-auto max-w-6xl px-4 py-6">
        <Tabs value={tab} onChange={setTab} items={[
          { value: "agenda",   label: "Agenda" },
          { value: "clientes", label: "Clientes" },
          { value: "ventas",   label: "Ventas" },
          { value: "reportes", label: "Reportes" },
          { value: "caja",     label: "Caja" },
        ]} />
        {tab === "agenda"   && <CalendarView />}
        {tab === "clientes" && <Clientes token={token} />}
        {tab === "ventas"   && <Ventas token={token} />}
        {tab === "reportes" && <Reportes token={token} />}
        {tab === "caja"     && <Caja token={token} />}
      </div>
    </div>
  );
}

// Nota: el CSS que tenías pegado al final del archivo se movió a index.css
