// Cloudflare Worker — CORS proxy for services.dha.gov.za
// Deploy: wrangler deploy
// Or paste into Cloudflare Dashboard > Workers > Quick Edit

const DHA_API = "https://services.dha.gov.za/api/booking";
const ALLOWED_ORIGINS = ["https://yusuf.kaka.co.za", "https://yusufk.github.io", "http://localhost"];

export default {
  async fetch(request) {
    // Only allow requests from your domains
    const origin = request.headers.get("Origin") || "";
    if (!ALLOWED_ORIGINS.some(o => origin.startsWith(o))) {
      return new Response("Forbidden", { status: 403 });
    }

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders(request) });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/^\//, "");

    if (!path) {
      return new Response(JSON.stringify({ endpoints: [
        "GET  /getbranchdetails/",
        "GET  /servicetypeslist/",
        "GET  /checkappointments/?identification_type=ID&identification_val=...",
        "POST /authenticatedetails/",
        "POST /gettimeslotdetails/",
        "POST /captureappointment/",
      ]}), { headers: { ...corsHeaders(request), "Content-Type": "application/json" }});
    }

    const target = `${DHA_API}/${path}${url.search}`;

    const init = {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
      },
    };

    // Forward cookies for session
    const cookie = request.headers.get("X-DHA-Cookie");
    if (cookie) init.headers["Cookie"] = cookie;

    if (request.method === "POST") {
      init.body = await request.text();
    }

    try {
      const resp = await fetch(target, init);
      const body = await resp.text();

      // Forward set-cookie as custom header (browsers block Set-Cookie from workers)
      const setCookie = resp.headers.get("Set-Cookie");
      const headers = {
        ...corsHeaders(request),
        "Content-Type": "application/json",
      };
      if (setCookie) headers["X-DHA-Set-Cookie"] = setCookie;

      return new Response(body, { status: resp.status, headers });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 502,
        headers: { ...corsHeaders(request), "Content-Type": "application/json" },
      });
    }
  },
};

function corsHeaders(request) {
  const origin = request.headers.get("Origin") || "*";
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-DHA-Cookie",
    "Access-Control-Expose-Headers": "X-DHA-Set-Cookie",
    "Access-Control-Max-Age": "86400",
  };
}
