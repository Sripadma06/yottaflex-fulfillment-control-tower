import React, { useEffect, useState } from "react";

import { createRoot } from "react-dom/client";

import {

  AlertCircle,

  AlertTriangle,

  Bell,

  Boxes,

  Check,

  ChevronDown,

  ChevronLeft,

  ChevronRight,

  CircleAlert,

  CircleCheck,

  Clock3,

  Database,

  ExternalLink,

  FileWarning,

  LayoutDashboard,

  LogOut,

  Package,

  Search,

  ShieldCheck,

  Truck,

  UserRound,

  X,

} from "lucide-react";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import "./style.css";



const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";



type User = { name?: string; email?: string; picture?: string };

type Metrics = {

  total_orders: number;

  allocated_orders: number;

  unallocated_orders: number;

  on_time_delivery_pct: number | null;

  delivery_rate_pct: number | null;

  exception_count: number;

  shipped_orders: number;

  allocation_rate_pct: number | null;

  status_counts: Record<string, number>;

};

type OrderRow = { id: string; status: string; total: number; zone: string; service_level: string; order_ts: string };

type ShipmentRow = { id: string; order_id: string; status: string; dispatch_at: string | null; delivered_at: string | null };

type Allocation = { selected: boolean; score: number | null; reason: string; candidates: Record<string, string[]>; created_at?: string };

type Quality = { total_orders: number; total_shipments: number; total_tracking_events: number; valid_records_pct: number; anomaly_count: number; warning_count: number; checks: { name: string; count: number; rate: number; status: string }[] };



type Section = "Overview" | "Orders" | "Shipments" | "Exceptions" | "Data Quality";



function Logo({ dark = false }: { dark?: boolean }) {

  return (

    <div className={`logo ${dark ? "logo-dark" : ""}`}>

      <span className="logo-mark"><i/><i/><i/></span>

      <strong>YottaFlex</strong>

    </div>

  );

}



function formatDate(value?: string | null) {

  if (!value) return "N/A";

  return new Date(value).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

}



function shortDate(value?: string | null) {

  if (!value) return "N/A";

  return new Date(value).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });

}



function money(value: number) {

  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value);

}



function StatusBadge({ status }: { status: string }) {

  const normalized = status.toLowerCase().replaceAll("_", "-");

  return <span className={`status-badge status-${normalized}`}>{status.replaceAll("_", " ")}</span>;

}



function Login({ error }: { error?: string }) {

  return (

    <div className="login-screen">

      <div className="login-brand"><Logo dark /></div>

      <div className="warehouse-glow glow-one" />

      <div className="warehouse-glow glow-two" />

      <div className="login-card">

        <div className="cube-icon"><Boxes size={40} strokeWidth={1.5}/></div>

        <h1>Fulfillment Control Tower</h1>

        <h2>Order &amp; Supply Chain Intelligence</h2>

        <p>Real-time visibility, allocation, shipment tracking,<br/>and exception management — in one place.</p>

        <a className="google-button" href={`${API}/auth/login`}>

          <span className="google-g">G</span>

          Continue with Google

        </a>

        {error === "oauth_not_configured" && <div className="login-error">Google OAuth is not configured. Add the credentials to the backend <code>.env</code>.</div>}

        {error === "authentication_failed" && <div className="login-error">Google authentication failed. Check the redirect URI and OAuth credentials.</div>}

        <div className="secure-login"><ShieldCheck size={15}/> Secure enterprise access with Google OAuth</div>

      </div>

    </div>

  );

}



function Topbar({ user, onLogout }: { user: User; onLogout: () => void }) {

  const [open, setOpen] = useState(false);

  return (

    <header className="topbar">

      <div className="topbar-right">

        <button className="icon-button" aria-label="Notifications"><Bell size={18}/><span className="notification-dot"/></button>

        <button className="profile-button" onClick={() => setOpen(v => !v)}>

          {user.picture ? <img src={user.picture} alt=""/> : <span className="avatar-fallback"><UserRound size={15}/></span>}

          <span>{user.name || user.email || "User"}</span>

          <ChevronDown size={15}/>

        </button>

        {open && <div className="profile-menu"><div className="profile-meta"><strong>{user.name || "User"}</strong><span>{user.email}</span></div><button onClick={onLogout}><LogOut size={15}/> Sign out</button></div>}

      </div>

    </header>

  );

}



function Sidebar({ section, setSection }: { section: Section; setSection: (section: Section) => void }) {

  const items: { label: Section; icon: React.ReactNode }[] = [

    { label: "Overview", icon: <LayoutDashboard size={17}/> },

    { label: "Orders", icon: <Package size={17}/> },

    { label: "Shipments", icon: <Truck size={17}/> },

    { label: "Exceptions", icon: <AlertTriangle size={17}/> },

    { label: "Data Quality", icon: <Database size={17}/> },

  ];

  return (

    <aside className="sidebar">

      <div className="sidebar-brand"><Logo dark /></div>

      <nav>{items.map(item => <button key={item.label} className={section === item.label ? "side-link active" : "side-link"} onClick={() => setSection(item.label)}>{item.icon}<span>{item.label}</span></button>)}</nav>

      <div className="sidebar-bottom"><div className="api-state"><span className="online-dot"/> API connected</div><div className="sidebar-footer">Fulfillment Control Tower<br/><span>Operational workspace</span></div></div>

    </aside>

  );

}



function MetricCard({ icon, label, value, sub, tone = "blue" }: { icon: React.ReactNode; label: string; value: React.ReactNode; sub?: string; tone?: string }) {

  return <article className="metric"><div className={`metric-icon ${tone}`}>{icon}</div><div className="metric-label">{label}</div><div className="metric-value">{value}</div>{sub && <div className="metric-sub">{sub}</div>}</article>;

}



function Overview({ metrics, setSection, userName, period, setPeriod }: { metrics: Metrics; setSection: (s: Section) => void; userName?: string; period: string; setPeriod: (p: string) => void }) {

  const allocatedPct = metrics.allocation_rate_pct ?? 0;

  const deliveredPct = metrics.delivery_rate_pct ?? 0;

  const donut = [

    { name: "Allocated", value: metrics.allocated_orders },

    { name: "Unallocated", value: metrics.unallocated_orders },

  ];

  return (

    <div className="page">

      <div className="page-heading">
        <div>
          <h1>Fulfillment Control Tower</h1>
          <h2>Good afternoon, <strong>{userName?.split(" ")[0] || "there"}</strong></h2>
          <p>Here's what's happening with your fulfillment operations today.</p>
        </div>
        <select
          className="date-filter"
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          aria-label="Dashboard date range"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
          <option value="all">All time</option>
        </select>
      </div>

      <section className="metrics-row">

        <MetricCard icon={<Boxes size={19}/>} label="Total Orders" value={metrics.total_orders.toLocaleString("en-IN")} tone="blue"/>

        <MetricCard icon={<Check size={19}/>} label="Allocated" value={metrics.allocated_orders.toLocaleString("en-IN")} sub={`${allocatedPct}%`} tone="green"/>

        <MetricCard icon={<AlertCircle size={19}/>} label="Unallocated" value={metrics.unallocated_orders.toLocaleString("en-IN")} sub={metrics.total_orders ? `${((metrics.unallocated_orders / metrics.total_orders) * 100).toFixed(2)}%` : undefined} tone="red"/>

        <MetricCard icon={<Truck size={19}/>} label="Delivery Rate" value={metrics.delivery_rate_pct != null ? `${metrics.delivery_rate_pct}%` : "N/A"} tone="blue"/>

        <MetricCard icon={<FileWarning size={19}/>} label="Exceptions" value={metrics.exception_count.toLocaleString("en-IN")} tone="red"/>

      </section>

      <section className="overview-grid">

        <article className="surface allocation-health"><div className="surface-head"><div><h3>Allocation Health</h3><p>{allocatedPct}% allocated</p></div><span className="head-pill">Live</span></div><div className="progress-track"><span style={{ width: `${Math.min(100, allocatedPct)}%` }}/></div><div className="health-stats"><span><b>{metrics.allocated_orders.toLocaleString("en-IN")}</b> allocated</span><span><b>{metrics.unallocated_orders.toLocaleString("en-IN")}</b> unallocated</span></div><div className="mini-stat"><div><span>Delivery Performance</span><strong>{deliveredPct}%</strong></div><div className="mini-progress"><span style={{ width: `${Math.min(100, deliveredPct)}%` }}/></div><small>Delivered orders / total orders</small></div></article>

        <article className="surface order-status"><div className="surface-head"><div><h3>Orders by Status</h3><p>Current operational distribution</p></div></div><div className="donut-wrap"><div className="donut"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={donut} dataKey="value" nameKey="name" innerRadius="64%" outerRadius="88%" paddingAngle={2}><Cell fill="#2dbb74"/><Cell fill="#e45c63"/></Pie><Tooltip formatter={(v: number) => v.toLocaleString("en-IN")}/></PieChart></ResponsiveContainer><div className="donut-center"><strong>{metrics.total_orders.toLocaleString("en-IN")}</strong><span>Orders</span></div></div><div className="donut-legend"><span><i className="legend-green"/>Allocated — {metrics.allocated_orders.toLocaleString("en-IN")} ({allocatedPct}%)</span><span><i className="legend-red"/>Unallocated — {metrics.unallocated_orders.toLocaleString("en-IN")} ({metrics.total_orders ? ((metrics.unallocated_orders / metrics.total_orders) * 100).toFixed(2) : "0.00"}%)</span></div></div></article>

        <article className="attention-card-large"><div className="attention-icon"><AlertTriangle size={23}/></div><h3>{metrics.unallocated_orders.toLocaleString("en-IN")} Orders require attention</h3><p>Review unallocated and exception orders to improve fulfillment performance.</p><button onClick={() => setSection("Exceptions")}>View Exceptions <ArrowIcon/></button></article>

      </section>

    </div>

  );

}



function ArrowIcon() { return <ChevronRight size={16}/>; }



function OrdersPage({ onOpenOrder }: { onOpenOrder: (id: string) => void }) {

  const [query, setQuery] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const [status, setStatus] = useState("");

  const [allocation, setAllocation] = useState("");

  const [total, setTotal] = useState(0);

  const [loading, setLoading] = useState(false);

  const [page, setPage] = useState(0);

  const [items, setItems] = useState<OrderRow[]>([]);

  const limit = 5;

  async function load() {
    setLoading(true);

    try {
      const params = new URLSearchParams({
        q: searchQuery,
        status,
        allocation,
        limit: String(limit),
        offset: String(page * limit),
      });

      const res = await fetch(`${API}/api/v1/orders?${params.toString()}`, {
        credentials: "include",
      });

      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Orders API ${res.status}: ${body}`);
      }

      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error("Orders load failed:", error);
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [page, status, allocation, searchQuery]);

  return <div className="page"><PageTitle title="Orders" subtitle="Search and view order details, allocation, and fulfillment status."/><div className="filter-row"><div className="search-box"><Search size={17}/><input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && (setPage(0), setSearchQuery(query.trim()))} placeholder="Search order ID"/></div><button className="primary-button" onClick={() => { setPage(0); setSearchQuery(query.trim()); }}>Search</button><select value={status} onChange={e => { setStatus(e.target.value); setPage(0); }}><option value="">Status: All</option><option value="ALLOCATED">Allocated</option><option value="DELIVERED">Delivered</option><option value="EXCEPTION">Exception</option><option value="SHIPPED">Shipped</option></select><select value={allocation} onChange={(e) => { setAllocation(e.target.value); setPage(0); }}><option value="">Allocation: All</option><option value="ALLOCATED">Allocated</option><option value="UNALLOCATED">Unallocated</option></select></div><div className="surface table-surface"><div className="table-scroll"><table><thead><tr><th>Order ID</th><th>Order Date</th><th>Allocation</th><th>Status</th><th>Actions</th></tr></thead><tbody>{loading ? <tr><td colSpan={5} className="table-empty">Loading orders...</td></tr> : items.map(o => <tr key={o.id}><td><strong>{o.id}</strong></td><td>{shortDate(o.order_ts)}</td><td><StatusBadge status={o.status === "EXCEPTION" ? "Unallocated" : "Allocated"}/></td><td><StatusBadge status={o.status}/></td><td><button className="view-button" onClick={() => onOpenOrder(o.id)}>View</button></td></tr>)}{!loading && !items.length && <tr><td colSpan={5} className="table-empty">No orders found.</td></tr>}</tbody></table></div><TablePager page={page} total={total} limit={limit} setPage={setPage}/></div></div>;

}



function PageTitle({ title, subtitle }: { title: string; subtitle: string }) { return <div className="page-heading simple"><div><h1>{title}</h1><p>{subtitle}</p></div></div>; }



function TablePager({ page, total, limit, setPage }: { page: number; total: number; limit: number; setPage: (p: number) => void }) {

  const pages = Math.max(1, Math.ceil(total / limit));

  return <div className="pager"><span>Showing {total ? page * limit + 1 : 0}-{Math.min(total, (page + 1) * limit)} of {total.toLocaleString("en-IN")}</span><div><button disabled={page === 0} onClick={() => setPage(page - 1)}><ChevronLeft size={15}/></button><b>{page + 1}</b><button disabled={page >= pages - 1} onClick={() => setPage(page + 1)}><ChevronRight size={15}/></button></div></div>;

}



function OrderDetails({ orderId, onBack }: { orderId: string; onBack: () => void }) {

  const [order, setOrder] = useState<any>(null);

  const [allocation, setAllocation] = useState<Allocation[]>([]);

  const [tab, setTab] = useState("Allocation");



  useEffect(() => {

    Promise.all([

      fetch(`${API}/api/v1/orders/${orderId}`, { credentials: "include" }).then(r => r.json()),

      fetch(`${API}/api/v1/orders/${orderId}/allocation`, { credentials: "include" }).then(r => r.json())

    ]).then(([o, a]) => {

      setOrder(o);

      setAllocation(a);

    });

  }, [orderId]);



  if (!order) return <div className="loading-inline">Loading order details…</div>;



  const selected = allocation.find(a => a.selected);

  const shipments = order.shipments || [];



  const events = shipments

    .flatMap((shipment: any) =>

      (shipment.events || []).map((event: any) => ({

        ...event,

        shipment_id: shipment.id

      }))

    )

    .sort(

      (a: any, b: any) =>

        new Date(a.event_time).getTime() - new Date(b.event_time).getTime()

    );



  return (

    <div className="page">

      <button className="back-link" onClick={onBack}>

        <ChevronLeft size={16} /> Back to Orders

      </button>



      <div className="detail-heading">

        <div>

          <h1>Order Details</h1>

          <div className="order-id-line">

            <strong>{order.id}</strong>

            <StatusBadge

              status={order.status === "DELIVERED" ? "Fulfilled" : order.status}

            />

          </div>

        </div>

      </div>



      <div className="detail-summary surface">

        <div>

          <span>Order Date</span>

          <strong>{shortDate(order.order_ts)}</strong>

        </div>

        <div>

          <span>Order Value</span>

          <strong>{money(order.total)}</strong>

        </div>

        <div>

          <span>Items</span>

          <strong>N/A</strong>

        </div>

        <div>

          <span>Allocation</span>

          <StatusBadge status={selected ? "Allocated" : "Unallocated"} />

        </div>

      </div>



      <div className="tabs">

        {["Allocation", "Items", "Shipment", "Timeline"].map(t => (

          <button

            className={tab === t ? "active" : ""}

            key={t}

            onClick={() => setTab(t)}

          >

            {t}{t === "Items" ? " (—)" : ""}

          </button>

        ))}

      </div>



      {tab === "Allocation" && (

        <div className="detail-grid-two">

          <article className="surface">

            <h3>Allocation Decision</h3>



            {selected ? (

              <>

                <div className="success-line">

                  <CircleCheck size={18} />

                  <strong>Allocated</strong> to{" "}

                  <b>

                    {(Object.values(selected.candidates || {}).flat()[0] as any)?.node_id ||

                      "fulfillment node"}

                  </b>

                </div>



                <dl className="detail-list">

                  <div>

                    <dt>Fulfillment Node</dt>

                    <dd>

                      {(Object.values(selected.candidates || {}).flat()[0] as any)?.node_id || "N/A"}

                    </dd>

                  </div>

                  <div>

                    <dt>Allocation Method</dt>

                    <dd>Configured weighted score</dd>

                  </div>

                  <div>

                    <dt>Allocation Time</dt>

                    <dd>{formatDate(selected.created_at)}</dd>

                  </div>

                </dl>



                <p className="muted">{selected.reason}</p>

              </>

            ) : (

              <div className="empty-box">

                No allocation decision is recorded for this order.

              </div>

            )}

          </article>



          <article className="surface">

            <h3>Shipment</h3>



            {shipments.length ? (

              <div className="shipment-mini">

                <span>Shipment ID</span>

                <strong>{shipments[0].id}</strong>



                <span>Status</span>

                <StatusBadge status={shipments[0].status} />



                <span>Dispatch</span>

                <strong>{formatDate(shipments[0].dispatch_at)}</strong>

              </div>

            ) : (

              <div className="empty-box">

                No shipment linked to this order.

              </div>

            )}

          </article>

        </div>

      )}



      {tab === "Items" && (

        <div className="surface empty-box tall">

          <CircleAlert size={28} />

          <strong>Items data</strong>

          <span>

            Item-level data is not available in the current operational schema.

          </span>

        </div>

      )}



      {tab === "Shipment" && (

        <div className="detail-grid-two">

          {shipments.length ? (

            shipments.map((shipment: any) => (

              <article className="surface" key={shipment.id}>

                <h3>Shipment</h3>



                <dl className="detail-list">

                  <div>

                    <dt>Shipment ID</dt>

                    <dd>{shipment.id}</dd>

                  </div>

                  <div>

                    <dt>Status</dt>

                    <dd>

                      <StatusBadge status={shipment.status} />

                    </dd>

                  </div>

                  <div>

                    <dt>Dispatch</dt>

                    <dd>{formatDate(shipment.dispatch_at)}</dd>

                  </div>

                  <div>

                    <dt>Delivered</dt>

                    <dd>{formatDate(shipment.delivered_at)}</dd>

                  </div>

                  <div>

                    <dt>Tracking Events</dt>

                    <dd>{(shipment.events || []).length}</dd>

                  </div>

                </dl>

              </article>

            ))

          ) : (

            <div className="surface empty-box tall">

              <CircleAlert size={28} />

              <strong>No shipment linked</strong>

              <span>This order does not currently have a shipment.</span>

            </div>

          )}

        </div>

      )}



      {tab === "Timeline" && (

        <div className="surface">

          <h3>Tracking Timeline</h3>



          {events.length ? (

            <div className="tracking-timeline">

              {events.map((event: any) => (

                <div className="timeline-item" key={event.id}>

                  <div className="timeline-marker">

                    <CircleCheck size={16} />

                  </div>



                  <div className="timeline-content">

                    <div className="timeline-header">

                      <strong>

                        {event.event_type.replaceAll("_", " ")}

                      </strong>

                      <span>{formatDate(event.event_time)}</span>

                    </div>



                    <div className="muted">

                      {event.location} · {event.shipment_id}

                    </div>

                  </div>

                </div>

              ))}

            </div>

          ) : (

            <div className="empty-box tall">

              <CircleAlert size={28} />

              <strong>No tracking events</strong>

              <span>

                No tracking events are currently recorded for this order.

              </span>

            </div>

          )}

        </div>

      )}

    </div>

  );

}

function ShipmentsPage({ onOpenShipment }: { onOpenShipment: (id: string) => void }) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<ShipmentRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(0);
  const limit = 10;

  async function load(targetPage = page) {
    setLoading(true);
    try {
      const res = await fetch(
        `${API}/api/v1/shipments?q=${encodeURIComponent(query)}&limit=${limit}&offset=${targetPage * limit}`,
        { credentials: "include" }
      );
      if (!res.ok) throw new Error("Unable to load shipments");
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(page).catch(() => {
      setItems([]);
      setTotal(0);
    });
  }, [page]);

  return (
    <div className="page">
      <PageTitle
        title="Shipments"
        subtitle="Search and track shipments with real-time status and timeline."
      />

      <div className="filter-row">
        <div className="search-box">
          <Search size={17}/>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter") {
                setPage(0);
                load(0);
              }
            }}
            placeholder="Search shipment or order ID"
          />
        </div>
        <button
          className="primary-button"
          onClick={() => {
            setPage(0);
            load(0);
          }}
        >
          Search
        </button>
      </div>

      <div className="surface shipment-list">
        {loading ? (
          <div className="table-empty">Loading shipments...</div>
        ) : (
          items.map(s => (
            <button
              className="shipment-row"
              key={s.id}
              onClick={() => onOpenShipment(s.id)}
            >
              <div>
                <strong>{s.id}</strong>
                <span>{s.order_id}</span>
              </div>
              <StatusBadge status={s.status}/>
              <div>
                <small>Dispatch</small>
                <span>{formatDate(s.dispatch_at)}</span>
              </div>
              <ChevronRight size={17}/>
            </button>
          ))
        )}

        {!loading && !items.length && (
          <div className="table-empty">No shipments found.</div>
        )}
      </div>

      <TablePager
        page={page}
        total={total}
        limit={limit}
        setPage={setPage}
      />
    </div>
  );
}
function ShipmentDetails({ shipmentId, onBack }: { shipmentId: string; onBack: () => void }) {

  const [data, setData] = useState<any>(null);

  useEffect(() => { fetch(`${API}/api/v1/shipments/${shipmentId}`, { credentials: "include" }).then(r => r.json()).then(setData); }, [shipmentId]);

  if (!data) return <div className="loading-inline">Loading shipment...</div>;

  return <div className="page"><button className="back-link" onClick={onBack}><ChevronLeft size={16}/> Back to Shipments</button><div className="detail-heading"><div><h1>Shipment</h1><div className="order-id-line"><strong>{data.shipment.id}</strong><StatusBadge status={data.shipment.status}/></div></div></div><div className="shipment-summary surface"><div><span>Order ID</span><strong>{data.shipment.order_id}</strong></div><div><span>Fulfillment Node</span><strong>{data.events?.[0]?.location || "N/A"}</strong></div><div><span>Carrier</span><strong>N/A</strong></div><div><span>Dispatch</span><strong>{formatDate(data.shipment.dispatch_at)}</strong></div></div><article className="surface timeline-card"><h3>Tracking Timeline</h3><div className="timeline">{(data.events || []).map((e: any, index: number) => <div className="timeline-item" key={e.id}><div className={`timeline-dot ${index === (data.events.length - 1) ? "current" : "done"}`}>{index === (data.events.length - 1) ? <Clock3 size={12}/> : <Check size={12}/>}</div><div><strong>{e.event_type.replaceAll("_", " ")}</strong><span>{formatDate(e.event_time)}</span><small>{e.location}</small></div></div>)}</div></article></div>;

}



function ExceptionsPage({ setSection }: { setSection: (s: Section) => void }) {
  const [tab, setTab] = useState<"unallocated" | "delayed" | "other">("unallocated");
  const [orders, setOrders] = useState<any[]>([]);
  const [shipments, setShipments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  const pageSize = 25;

  useEffect(() => {
    if (tab !== "unallocated") {
      setLoading(true);
      fetch(API + "/api/v1/shipments?limit=100", { credentials: "include" })
        .then(r => r.json())
        .then(data => setShipments(data.items || []))
        .catch(() => setShipments([]))
        .finally(() => setLoading(false));
      return;
    }

    setLoading(true);

    fetch(
      API + `/api/v1/exceptions?page=${page}&page_size=${pageSize}`,
      { credentials: "include" }
    )
      .then(r => r.json())
      .then(data => {
        setOrders(data.items || []);
        setTotal(data.total || 0);
        setTotalPages(data.total_pages || 0);
      })
      .catch(() => {
        setOrders([]);
        setTotal(0);
        setTotalPages(0);
      })
      .finally(() => setLoading(false));
  }, [tab, page]);

  const delayedShipments = shipments.filter((shipment: any) =>
    shipment.status !== "DELIVERED" && shipment.dispatch_at
  );

  const otherExceptions = shipments.filter((shipment: any) =>
    shipment.status === "EXCEPTION"
  );

  const changeTab = (nextTab: "unallocated" | "delayed" | "other") => {
    setTab(nextTab);
    if (nextTab === "unallocated") {
      setPage(1);
    }
  };

  return <div className="page">
    <PageTitle
      title="Exceptions"
      subtitle="Orders and shipments that require investigation or action."
    />

    <div className="exception-tabs">
      <button
        className={tab === "unallocated" ? "active" : ""}
        onClick={() => changeTab("unallocated")}
      >
        Unallocated Orders ({total.toLocaleString("en-IN")})
      </button>

      <button
        className={tab === "delayed" ? "active" : ""}
        onClick={() => changeTab("delayed")}
      >
        Delayed Shipments ({delayedShipments.length.toLocaleString("en-IN")})
      </button>

      <button
        className={tab === "other" ? "active" : ""}
        onClick={() => changeTab("other")}
      >
        Other Exceptions ({otherExceptions.length.toLocaleString("en-IN")})
      </button>
    </div>

    <div className="surface table-surface">
      {loading ? (
        <div className="table-empty">Loading exceptions...</div>
      ) : tab === "unallocated" ? (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Reason</th>
                  <th>Order Date</th>
                  <th>Zone</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {orders.length > 0 ? (
                  orders.map(item => (
                    <tr key={item.id}>
                      <td><strong>{item.id}</strong></td>
                      <td>{item.reason}</td>
                      <td>{shortDate(item.order_ts)}</td>
                      <td>{item.zone}</td>
                      <td>
                        <button
                          className="view-button"
                          onClick={() => setSection("Orders")}
                        >
                          Review
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5}>
                      <div className="table-empty">No exceptions found.</div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="pagination-button"
                disabled={page <= 1}
                onClick={() => setPage(current => current - 1)}
              >
                Previous
              </button>

              <span className="pagination-info">
                Page {page} of {totalPages}
              </span>

              <button
                className="pagination-button"
                disabled={page >= totalPages}
                onClick={() => setPage(current => current + 1)}
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : tab === "delayed" ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Shipment ID</th>
                <th>Order ID</th>
                <th>Status</th>
                <th>Dispatch</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {delayedShipments.map(shipment => (
                <tr key={shipment.id}>
                  <td><strong>{shipment.id}</strong></td>
                  <td>{shipment.order_id}</td>
                  <td><StatusBadge status={shipment.status}/></td>
                  <td>{formatDate(shipment.dispatch_at)}</td>
                  <td>
                    <button
                      className="view-button"
                      onClick={() => setSection("Shipments")}
                    >
                      Review
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Shipment ID</th>
                <th>Order ID</th>
                <th>Status</th>
                <th>Dispatch</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {otherExceptions.map(shipment => (
                <tr key={shipment.id}>
                  <td><strong>{shipment.id}</strong></td>
                  <td>{shipment.order_id}</td>
                  <td><StatusBadge status={shipment.status}/></td>
                  <td>{formatDate(shipment.dispatch_at)}</td>
                  <td>
                    <button
                      className="view-button"
                      onClick={() => setSection("Shipments")}
                    >
                      Review
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  </div>;
}

function DataQualityPage() {

  const [data, setData] = useState<Quality | null>(null);

  useEffect(() => { fetch(`${API}/api/v1/data-quality`, { credentials: "include" }).then(r => r.json()).then(setData); }, []);

  if (!data) return <div className="loading-inline">Loading data quality...</div>;

  return <div className="page"><PageTitle title="Data Quality" subtitle="Validation results and data anomalies in the operational dataset."/><section className="quality-cards"><MetricCard icon={<CircleCheck size={19}/>} label="Valid Records" value={`${data.valid_records_pct}%`} tone="green"/><MetricCard icon={<AlertCircle size={19}/>} label="Anomalies" value={data.anomaly_count} tone="red"/><MetricCard icon={<AlertTriangle size={19}/>} label="Warnings" value={data.warning_count} tone="orange"/></section><article className="surface table-surface"><div className="surface-head quality-head"><div><h3>Validation &amp; Anomaly Summary</h3><p>Derived from operational database integrity checks.</p></div><span className="source-pill"><Database size={14}/> Live database</span></div><div className="table-scroll"><table><thead><tr><th>Check</th><th>Count</th><th>Rate</th><th>Status</th></tr></thead><tbody>{data.checks.map(check => <tr key={check.name}><td><strong>{check.name}</strong></td><td>{check.count.toLocaleString("en-IN")}</td><td>{check.rate}%</td><td><span className={`quality-status ${check.status.toLowerCase()}`}>{check.status}</span></td></tr>)}</tbody></table></div></article></div>;

}



function App() {

  const [user, setUser] = useState<User | null>(null); const [authLoading, setAuthLoading] = useState(true); const [metrics, setMetrics] = useState<Metrics | null>(null); const [section, setSection] = useState<Section>("Overview"); const [orderId, setOrderId] = useState<string | null>(null); const [shipmentId, setShipmentId] = useState<string | null>(null); const [globalError, setGlobalError] = useState(""); const [period, setPeriod] = useState("30d");

  const loginError = new URLSearchParams(window.location.search).get("error") || undefined;

  useEffect(() => { fetch(`${API}/auth/me`, { credentials: "include" }).then(r => r.json()).then(d => { setUser(d.user || null); setAuthLoading(false); }).catch(() => setAuthLoading(false)); }, []);

  useEffect(() => {
    if (!user) return;
    setMetrics(null);
    fetch(`${API}/api/v1/overview?period=${encodeURIComponent(period)}`, { credentials: "include" })
      .then(async r => {
        if (!r.ok) throw new Error("Unable to load live metrics");
        return r.json();
      })
      .then(setMetrics)
      .catch(e => setGlobalError(e.message));
  }, [user, period]);

  async function logout() { await fetch(`${API}/auth/logout`, { method: "POST", credentials: "include" }); setUser(null); setMetrics(null); }

  if (authLoading) return <div className="loading-screen">Loading secure workspace...</div>;

  if (!user) return <Login error={loginError}/>;

  const content = orderId ? <OrderDetails orderId={orderId} onBack={() => setOrderId(null)}/> : shipmentId ? <ShipmentDetails shipmentId={shipmentId} onBack={() => setShipmentId(null)}/> : section === "Overview" ? (metrics ? <Overview metrics={metrics} setSection={setSection} userName={user.name} period={period} setPeriod={setPeriod}/> : <div className="loading-inline">Loading live metrics...</div>) : section === "Orders" ? <OrdersPage onOpenOrder={setOrderId}/> : section === "Shipments" ? <ShipmentsPage onOpenShipment={setShipmentId}/> : section === "Exceptions" ? <ExceptionsPage setSection={setSection}/> : <DataQualityPage/>;

  return <div className="app-shell"><Sidebar section={section} setSection={(s) => { setOrderId(null); setShipmentId(null); setSection(s); }}/><div className="main-shell"><Topbar user={user} onLogout={logout}/>{globalError && <div className="global-error"><AlertTriangle size={17}/> {globalError}<button onClick={() => setGlobalError("")}><X size={15}/></button></div>}{content}</div></div>;

}



createRoot(document.getElementById("root")!).render(<App/>);

