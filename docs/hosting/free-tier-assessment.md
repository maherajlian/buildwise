# BuildWise: free-tier hosting feasibility

**Provider terms reviewed on 2026-11-20.** Quotas and eligibility can change.
Public plan terms are not an audit of billing settings for owner-provided accounts.

## Public demo budget

The deployed layout requires **$0 in mandatory hosting and $0 in inference**
within these limits. It is best effort, not a production availability commitment.

| Deployed dependency | Free-tier allowance and cost control |
| --- | --- |
| [Cloudflare Pages](https://developers.cloudflare.com/pages/platform/limits/) | Static export, no Workers or Functions, provider subdomain. Pages Free lists 500 builds/month; CI uploads a prebuilt bundle. |
| [Render Free](https://render.com/docs/free) | One service; 750 instance-hours per workspace/month, spin-down after 15 idle minutes. A 31-day month kept warm can consume 744 hours. **Do not add a second service**; disable the keep-warm workflow if approaching quota. |
| [Neon Free](https://neon.com/pricing) | One small PostgreSQL database; 1 GB and 100 CU-hours/project/month, compute wakes on first query after idle. Restrict usage rather than buying more capacity. |
| [Grafana Cloud Free](https://grafana.com/pricing/) | 10k metric series and 50 GB/month each of logs and traces, with 14-day retention. Bound labels, sample traces and disable optional export if necessary. See the [runbook](../operations/observability.md#free-tier-budget). |
| [GitHub Actions](https://docs.github.com/en/billing/concepts/product-billing/github-actions) | Standard hosted runners in a public repository; no larger runners. Short retention for failure artifacts. |

No model API key, paid integration, domain, collector or higher service tier is
needed or provisioned by the demo. Optional paid recommendations are descriptions,
not enabled integrations. Do not enable automatic overages or an upgrade if a
quota is reached. Preserve public health-only pages and use the local Compose
setup if hosted telemetry or the public API is unavailable.

See the [deployment spike](deployment-spike-results.md#resources-plans-and-safety-controls)
for separately verified resource settings and account-level unknowns. The rest
of this assessment compares launch choices and fallback options.

## Primary providers

### Cloudflare Pages and Workers

| Item | Verified quota / behaviour / source |
| --- | --- |
| Workers Free requests and CPU | **100,000 requests/day**, **10 ms CPU per HTTP invocation**, **128 MB memory**. Network waits are not CPU time. Hitting CPU limits can terminate requests. [Workers limits](https://developers.cloudflare.com/workers/platform/limits/). |
| Static requests | Static asset requests are free and unlimited; do not confuse that with dynamic Worker requests. [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/). |
| Pages builds | **500 builds/month**, **1 concurrent build**, **20-minute build timeout** on Free. This is a build-count allowance, not a published monthly build-minute pool. [Pages limits](https://developers.cloudflare.com/pages/platform/limits/). |
| Workers Builds | Separate product: **3,000 build minutes/month**, **1 concurrent build**, **20-minute timeout** on Free. [Builds pricing/limits](https://developers.cloudflare.com/workers/ci-cd/builds/limits-and-pricing/). |
| Card | No card required to start free, per [Cloudflare's official site](https://www.cloudflare.com/). Account-specific anti-abuse checks are unverified. |
| Sleep | Static hosting has no sleeping application process. Workers are request-driven isolates, not a VM with a Render-style inactivity timer; Python uses deployment snapshots to reduce initialization cost. No numerical cold-start guarantee verified. [Python runtime lifecycle](https://developers.cloudflare.com/workers/languages/python/how-python-workers-work/). |

**Next.js:** [OpenNext's official adapter documentation](https://opennext.js.org/cloudflare) explicitly supports `@opennextjs/cloudflare` on Workers using the Next.js **Node.js runtime**, unlike legacy `next-on-pages`' Edge-only approach. This is not arbitrary Node server/container hosting. Today's [Cloudflare Next.js guide](https://developers.cloudflare.com/workers/framework-guides/web-apps/nextjs/) now recommends **vinext**, explicitly in **beta**; OpenNext remains a documented adapter path. Do not silently replace Next.js with vinext. [Pages static Next.js guide](https://developers.cloudflare.com/pages/framework-guides/nextjs/deploy-a-static-nextjs-site/) supports the static-export option. Dynamic feature compatibility and representative SSR CPU use remain unverified until spiked; 10 ms is a substantial free-tier risk.

**Python Workers:** the [current overview](https://developers.cloudflare.com/workers/languages/python/) calls Python first-class and lists FastAPI/Pydantic, requiring `python_workers`. It does **not** label it beta in the retrieved page; explicit current beta-versus-GA release status is **unverified** (absence of the label is not proof of GA). It runs CPython via **Pyodide/WebAssembly**, not a normal Linux CPython environment. [Package docs](https://developers.cloudflare.com/workers/languages/python/packages/) allow pure Python, PyEmscripten and included Pyodide packages, not arbitrary native wheels.

Importantly, do **not** repeat the outdated blanket claim that psycopg cannot work: today's [Hyperdrive Python guide](https://developers.cloudflare.com/hyperdrive/examples/python-workers/) lists **psycopg, pg8000 and asyncpg** as tested drivers with TCP support, requiring compatibility date **2026-09-08 or later**. It explicitly supports **synchronous SQLAlchemy only**; async SQLAlchemy is not supported because greenlet is unavailable. Synchronous DB access requires serialization/locking as documented. Thus FastAPI + synchronous SQLAlchemy/psycopg is a documented possibility, **not a verified BuildWise deployment**. Alembic, full OTel SDK/exporter compatibility, combined dependency bundle and request CPU consumption are unverified. Hyperdrive adds a separate **100,000 database statements/day** Free limit ([pricing](https://developers.cloudflare.com/workers/platform/pricing/)). Prefer Render for ordinary Python semantics initially.

### Render Free web service

All limits in this paragraph are from [Deploy for Free](https://render.com/docs/free): **750 free instance hours/workspace/calendar month**, shared among free services; sleeping hours do not count. Exhaustion suspends free web services until next month. After **15 minutes without inbound HTTP/WebSocket traffic**, the service spins down; the next request wakes it in **about one minute**, not a latency SLA. Filesystem changes disappear on restart/redeploy/sleep; free services cannot attach persistent disks. One free service is sufficient for the modular API; do not add a separate free background worker.

**Card:** not universally required, but can be required for account verification. The official docs explicitly describe operating without a payment method; [Render staff's provider-hosted support reply](https://community.render.com/t/free-tier-payment-error/36531) says that a prompted card is mandatory. This is support evidence, not a blanket no-card contractual guarantee; this particular account's eligibility is **unverified**.

**Risks:** outbound bandwidth and build pipeline allowances also apply. Their current numeric workspace allowances were **not verified**; check the dashboard before deployment. Docs say no-payment accounts suspend free services on bandwidth exhaustion and disable new builds on pipeline exhaustion; accounts with payment methods can incur supplementary charges. External DB calls and OTLP exports count as service-initiated traffic; unusually high traffic can trigger suspension with paid upgrade as the documented restoration route. Do not use pings to claim an always-on guarantee.

**Do not use Render Free Postgres as durable MVP storage:** same [official page](https://render.com/docs/free) gives **1 GB**, **one active free database/workspace**, expiration **30 days after creation**, then **14-day upgrade grace period** before deletion. No backups or managed pooling. Expiration, not merely sleeping, defeats long-lived zero-cost persistence.

### Supabase Free

| Item | Verified quota / source |
| --- | --- |
| Database | **500 MB/project**, shared CPU and **500 MB RAM**, **2 active free projects**. [Pricing](https://supabase.com/pricing). The project entitlement spans organizations where the member is Owner/Admin; paused projects do not count. [Billing](https://supabase.com/docs/guides/platform/billing-on-supabase). |
| Inactivity | Projects pause after **1 week of inactivity**; paid plans do not. Plan a pre-demo resume/check, not an always-on claim. [Pricing](https://supabase.com/pricing). Exact restore delay is unverified. |
| Connections | Nano Free defaults: **60 direct DB connections**, **200 pooler clients**. These are not 200 simultaneously executing DB queries; backend pool size and reserved service connections matter. [Connection defaults](https://supabase.com/kb/troubleshooting/how-to-change-max-database-connections-_BQ8P5). |
| Pooler networking | Shared Supavisor is included and IPv4-only; direct connections normally require IPv6 unless buying an add-on. Dedicated PgBouncer requires Pro or above. [Pooling and limits](https://supabase.com/docs/guides/database/connecting-to-postgres/pooling-and-limits). |
| Egress | **5 GB uncached + 5 GB cached egress**, not an interchangeable 10 GB allowance for database traffic. [Pricing](https://supabase.com/pricing). Quotas aggregate at organization level, except DB size is per project. [Billing](https://supabase.com/docs/guides/platform/billing-on-supabase). |
| Card | [Billing setup](https://supabase.com/docs/guides/platform/get-set-up-for-billing) explicitly requires cards for **paid** plans; a categorical no-card statement for Free was not found in retrieved official text: **unverified**. Do not treat a Free plan as authorization to upgrade. |

Risks: pausing interrupts API readiness; small connection/storage budgets and egress constrain a public demo. Automatic backups are not included on Free ([pricing](https://supabase.com/pricing)); maintain independent exports. Disable prepared statements if using transaction pooling and verify driver/migration behaviour; prefer session pooling for the initial persistent API. Never expose the DB password in browser code.

### Grafana Cloud Free

- **10,000 metrics series, 50 GB logs and 50 GB traces**: [official deployment comparison](https://grafana.com/grafana/deployment-options/) lists these Free allowances and **3 users**. [Pricing](https://grafana.com/pricing/) identifies the metrics unit as **active series**, not datapoints. Treat logs/traces as monthly ingestion budgets, not persistent disk allocations; precise current ingestion reset/accounting details are **unverified** in retrieved text.
- **14-day retention** for metrics/logs/traces, and **no credit card required**, verified on [Free tier](https://grafana.com/products/cloud/free-tier/) and [pricing](https://grafana.com/pricing/).
- **OTLP endpoint exists for all three signals**: [official OTLP guide](https://grafana.com/docs/grafana-cloud/send-data/otlp/send-data-otlp/) recommends the managed endpoint and documents direct SDK ingestion for non-production when a collector is impractical. Get the stack-specific endpoint and auth headers from the portal; exact tenant endpoint and successful authentication are **unverified** until provisioning. Use OTLP/HTTP over HTTPS, with signal paths configured correctly.
- No app-server sleep requirement; precise inactive-stack suspension/deletion policy is **unverified**. Risk: cardinality explosion, verbose logs, missing batch flushes when Render sleeps, and data aging out. Remain on **Free**, not a paid usage plan; the Free page promises no charges, but telemetry beyond allowances is not a retention guarantee. Do not enable AI features as a BuildWise dependency.

### GitHub Free Actions

[Current official billing docs](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions) now describe **$12/month included compute usage** for GitHub Free/private repositories, rather than a fixed minutes grant. At their documented **$0.006/min standard Linux** rate this is **2,000 Linux-equivalent minutes/month** (calculated: 12 / 0.006), only if no other eligible usage consumes the shared allowance. Do not present 2,000 as a universal fixed runner-independent quota. **Standard hosted runners in public repos remain free independently of that pool**; larger runners are billed even for public repos. Free includes **500 MB artifact storage** and **10 GB cache storage** (see billing page for storage accounting).

Card-free public Actions/account-specific verification is **unverified** in the retrieved billing page; no paid runner is needed for this design. No app sleep behaviour applies. Risks: accidentally selecting larger runners, artifact accumulation and private-repo shared compute consumption. Explicitly block paid overages before enabling CI; public compute being free does not mean arbitrary artifact storage is free.

## Alternatives if a primary fails

| Provider | Officially verified numbers | Card / commercial or hobby terms | Sleep/pause and risks |
| --- | --- | --- | --- |
| **Neon Free Postgres** | [Pricing](https://neon.com/pricing), updated 2026-11-04: **100 projects**, **100 CU-hours/project/month**, **1 GB/project, 20 GB/account total**, **5 GB egress/project**, up to **2 CU**. | Pricing explicitly says permanent Free plan, **no credit card** (AI Gateway is separate and excluded). A non-commercial-only restriction was not found; commercial eligibility is **unverified**, not a legal conclusion. | Compute scales to zero after **5 idle minutes**, auto-wakes on query, typically a few hundred milliseconds per pricing FAQ, not an SLA. No inactivity project-pause/restore step. Exhausting CU-hours/egress suspends compute until next period; storage excess blocks writes. Excellent DB fallback, not API hosting. |
| **Koyeb Free instance** | [Instances](https://www.koyeb.com/docs/reference/instances): **one/org**, **512 MB RAM**, **0.1 vCPU**, **2 GB SSD**. | [Pricing FAQ](https://www.koyeb.com/docs/faqs/pricing): **card required**, **$29 preauthorization hold**; it also warns the selected plan is charged pro rata at signup (example/default Pro), with Starter downgrade possible. Do not enroll assuming zero initial charge. Instance docs position Free for hobby/testing, **not production**; explicit commercial-use prohibition is **unverified**. | Scales to zero after **1 idle hour**; no volumes or custom scaling; cold-start duration unverified. Possible API fallback only after explicit signup/plan validation; not a verified zero-mandatory-payment substitute. |
| **Fly.io** | [Trial](https://fly.io/docs/about/free-trial/): **$1 credit**, expires after **7 days** or consumption; up to **10 machines**, trial machines stop after **5 minutes running**. | No card for trial; **card required to continue when credit expires**. Commercial/hobby restriction unverified; [pricing](https://fly.io/docs/about/pricing/) is pay-as-you-go, not an ongoing general free tier. | Trial resource deletion possible without payment. The trial page mentions waiver of monthly bills **below $5** after adding a card; this is a conditional waiver, not a hard spend cap. Reject as a predictable zero-cost primary. |
| **Vercel Hobby** | [Hobby docs](https://vercel.com/docs/plans/hobby): **100 GB fast data transfer**, **10 GB origin transfer**, **1 million invocations**, **4 CPU-hours**, **360 GB-hours provisioned memory**, generally monthly. | Free. No-card signup is **unverified** in retrieved official docs. Official search result for [fair-use guidelines](https://vercel.com/docs/limits/fair-use-guidelines.md) explicitly says **non-commercial personal use only**, commercial use requires Pro/Enterprise. However today's fetched full text omitted this paragraph: treat current enforceable commercial eligibility as **unverified/conflicting evidence** and do not approve BuildWise commercial use without confirmation. | Static CDN/request-driven functions; no Render-style inactivity timeout verified. Most exhausted Hobby features require waiting **30 days** per Hobby docs. Next.js-friendly fallback for an eligible personal demo only; paid development/consulting can raise commercial eligibility concerns. |

## Unresolved provider checks

Potential fallback account/card eligibility, regional signup capacity, Python
Workers compatibility with the full stack, and commercial eligibility of some
personal tiers remain unverified. There is no verified unconditional,
card-free, drop-in API fallback. Recheck actual billing/quotas in provider
dashboards before changing hosting; do not make a paid change to restore service.
