# Hong Kong City-Change Magazine — Source Directory

> **Purpose**  
> This source directory supports a Hong Kong digital magazine covering property, city transformation, infrastructure, transport, economy, investment context, business, technology, smart construction, maritime/logistics, and Greater Bay Area developments.
>
> **Editorial rule:** use official primary sources for factual claims; use professional research and journalism for context, interpretation, reactions, and story angles. Preserve original URLs, retrieval dates, source tiers, and evidence excerpts in the research engine.
>
> **Important:** Paid publishers and sources with access restrictions must be configured as `metadata_only` unless you have explicit permission to collect more. Do not bypass paywalls, logins, CAPTCHAs, robots restrictions, or terms of service.

---

## 1. Source Tiers

| Tier | Source type | How the newsroom uses it |
|---|---|---|
| **Tier 1** | Official government datasets, legislation, gazette notices, statutory documents, filings, direct project documentation | Primary factual basis |
| **Tier 2** | Official organisations, listed companies, developers, MTR, public bodies, official vendor announcements | Project updates, commitments, schedules, product details |
| **Tier 3** | Established journalism and wire services | Context, reporting, interviews, reaction |
| **Tier 4** | Consultancy, agency, institutional, and market research | Attributed market interpretation and forecasts |
| **Tier 5** | Social platforms, forums, creator content, agent commentary | Sentiment, leads, public reaction only; never sole evidence |

---

## 2. Collection Policies

Use one of these collection policies for each source in the research engine.

| Policy | Meaning |
|---|---|
| `rss_only` | Collect only public RSS/Atom feed entries |
| `sitemap_only` | Discover source URLs from public XML sitemap(s); fetch only where permitted |
| `metadata_only` | Store title, URL, source, date, approved snippet, and editorial note only |
| `public_page_extract_allowed` | Fetch and extract readable text from public pages, with rate limits and robots/TOS checks |
| `manual_only` | Editor adds links or notes manually |
| `official_api` | Use the official published API or official downloadable data only |
| `disabled` | Keep in registry but do not collect |

Recommended defaults:

- Official public-government pages and open data: `official_api`, `rss_only`, `sitemap_only`, or `public_page_extract_allowed` after verification.
- Professional research/consultancy reports: `metadata_only` or `public_page_extract_allowed` only where permitted.
- Established media and paid publishers: `metadata_only`.
- Social/community sources: `manual_only`.

---

# 3. Free Official Sources

## 3.1 Government news, policy, open data and maps

| Source | Tier | Suggested policy | Link | Key uses |
|---|---:|---|---|---|
| GovHK News | 1 | `public_page_extract_allowed` | [news.gov.hk](https://www.news.gov.hk/eng/index.html) | Government policy, public works, economy, city developments |
| Government Information Services press releases | 1 | `sitemap_only` / `public_page_extract_allowed` | [info.gov.hk press releases](https://www.info.gov.hk/gia/general/today.htm) | Primary government announcements |
| 2026 Policy Address | 1 | `manual_only` / document archive | [Policy Address 2026](https://www.policyaddress.gov.hk/2026/en/index.html) | Long-term policy, city development, housing, infrastructure |
| Policy Address highlights | 1 | `public_page_extract_allowed` | [Policy Address highlights](https://www.policyaddress.gov.hk/2026/en/highlight.html) | Quick policy tracking |
| 2026–27 Hong Kong Budget | 1 | `manual_only` / document archive | [Hong Kong Budget 2026–27](https://www.budget.gov.hk/2026/eng/index.html) | Fiscal policy, growth forecast, public works, spending |
| Legislative Council | 1 | `sitemap_only` / `manual_only` | [LegCo](https://www.legco.gov.hk/english/index.htm) | Panel papers, policy scrutiny, project documents |
| LegCo Policy Pulse | 1 | `public_page_extract_allowed` | [Policy Pulse](https://www.legco.gov.hk/general/english/publications/policy_pulse.htm) | Readable public-policy summaries |
| DATA.GOV.HK | 1 | `official_api` | [DATA.GOV.HK](https://data.gov.hk/en/) | Open datasets, reusable public data |
| Common Spatial Data Infrastructure | 1 | `official_api` / `manual_only` | [CSDI Geoportal](https://portal.csdi.gov.hk/geoportal/?lang=en) | Maps, land, spatial datasets |
| Hong Kong GeoInfo Map | 1 | `manual_only` | [GeoInfo Map](https://www.map.gov.hk/) | Location/context checks, map research |

## 3.2 Property, housing, prices and transactions

| Source | Tier | Suggested policy | Link | Key uses |
|---|---:|---|---|---|
| Rating and Valuation Department | 1 | `official_api` / `public_page_extract_allowed` | [RVD](https://www.rvd.gov.hk/en/) | Official property statistics and property information |
| RVD property-market statistics | 1 | `official_api` | [Property market statistics](https://www.rvd.gov.hk/en/publications/property_market_statistics.html) | Price, rent, yield, vacancy, stock, supply data |
| RVD Hong Kong Property Review | 1 | `manual_only` / document archive | [Hong Kong Property Review](https://www.rvd.gov.hk/en/publications/hong-kong-property-review.html) | Annual market context |
| RVD monthly supplement PDF | 1 | `manual_only` / document archive | [Property Review monthly supplement](https://www.rvd.gov.hk/doc/en/statistics/full.pdf) | Monthly property-market figures |
| DATA.GOV.HK RVD property dataset | 1 | `official_api` | [Property Market Statistics dataset](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics) | Central machine-readable property data catalogue |
| Average domestic prices by class, monthly | 1 | `official_api` | [Monthly average prices CSV](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics/resource/79db448f-46a0-4bea-8163-e9bff613e5cb) | Property-price series |
| Average domestic rents by class, monthly | 1 | `official_api` | [Monthly average rents CSV](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics/resource/8d5513e5-22cd-4809-878c-4afc35264c03) | Rental-market series |
| Domestic price index by class, monthly | 1 | `official_api` | [Monthly price indices CSV](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics/resource/f0f063ea-fb27-4846-bcb6-e611269e3b63) | Price-index trend analysis |
| Private domestic yield, monthly | 1 | `official_api` | [Monthly yields CSV](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics/resource/7abe6fdf-8738-4d01-b1b1-f8a4de4cfb08) | Rental yield / investment context |
| Domestic sales statistics | 1 | `official_api` | [Domestic sales dataset](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics/resource/74cb2277-c96f-4262-8016-cf8ed8f1083a) | Sales-volume and value trends |
| Domestic completions, stock, vacancy and take-up | 1 | `official_api` | [Supply and vacancy dataset](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics/resource/b8c6ad0b-7360-4128-87d0-65ddf12b02c5) | Supply / absorption analysis |
| Private domestic stock by district | 1 | `official_api` | [District stock dataset](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics/resource/c3e67022-b8bc-4c57-86ad-55ca2fcdbebd) | District stories and comparisons |
| Private retail rents and prices | 1 | `official_api` | [Retail rents and prices dataset](https://data.gov.hk/en-data/dataset/hk-rvd-tsinfo_rvd-property-market-statistics/resource/83afc881-bfeb-448f-b37c-3a6fb4b0aed5) | Retail/property/economy analysis |
| Land Registry latest monthly statistics | 1 | `public_page_extract_allowed` | [Latest monthly statistics](https://www.landreg.gov.hk/en/monthly/monthly.htm) | Monthly registrations, sale-and-purchase agreements |
| Land Registry statistics | 1 | `public_page_extract_allowed` | [Land Registry statistics](https://www.landreg.gov.hk/en/statistics/statistics.htm) | Property registration context |
| Housing Authority | 1 | `public_page_extract_allowed` | [Hong Kong Housing Authority](https://www.housingauthority.gov.hk/en/index.html) | Public housing policy and supply |
| Housing Authority publications and statistics | 1 | `public_page_extract_allowed` | [Publications and statistics](https://www.housingauthority.gov.hk/en/about-us/publications-and-statistics/index.html) | Housing data and reports |

## 3.3 Land, planning, development and urban renewal

| Source | Tier | Suggested policy | Link | Key uses |
|---|---:|---|---|---|
| Development Bureau | 1 | `public_page_extract_allowed` | [Development Bureau](https://www.devb.gov.hk/en/index.html) | Development policy, public works, land and planning |
| Development Bureau press releases | 1 | `sitemap_only` / `public_page_extract_allowed` | [DevB press releases](https://www.devb.gov.hk/en/publications_and_press_releases/press_releases/index.html) | Policy and project announcements |
| Development Bureau public works | 1 | `manual_only` / document archive | [Public Works Programme](https://www.devb.gov.hk/en/publications_and_press_releases/publications/works/index.html) | Public-works budgets, project lists |
| Planning Department | 1 | `public_page_extract_allowed` | [Planning Department](https://www.pland.gov.hk/pland_en/index.html) | Land-use planning and district plans |
| Statutory planning portal | 1 | `manual_only` | [OZP portal](https://www.ozp.tpb.gov.hk/) | Outline zoning plans, planning records |
| Town Planning Board | 1 | `public_page_extract_allowed` | [Town Planning Board](https://www.tpb.gov.hk/en/) | Planning decisions, applications |
| Town Planning Board applications | 1 | `manual_only` | [Plan applications](https://www.tpb.gov.hk/en/plan_application.html) | Individual planning cases |
| Lands Department | 1 | `public_page_extract_allowed` | [Lands Department](https://www.landsd.gov.hk/en/index.html) | Land administration and sales |
| Lands Department land sales | 1 | `public_page_extract_allowed` | [Land sale information](https://www.landsd.gov.hk/en/landsale/land-sale-information.html) | Tender, premium, land-sale stories |
| Civil Engineering and Development Department | 1 | `public_page_extract_allowed` | [CEDD](https://www.cedd.gov.hk/eng/index.html) | New development areas, land formation, infrastructure |
| CEDD major projects | 1 | `public_page_extract_allowed` | [CEDD projects](https://www.cedd.gov.hk/eng/our-projects/index.html) | Project descriptions and programme context |
| Urban Renewal Authority | 2 | `public_page_extract_allowed` | [URA](https://www.ura.org.hk/en) | Urban regeneration, ageing districts, redevelopment |
| URA redevelopment projects | 2 | `public_page_extract_allowed` | [URA redevelopment](https://www.ura.org.hk/en/project/redevelopment) | Project-specific redevelopment stories |
| Northern Metropolis official website | 1 | `public_page_extract_allowed` | [Northern Metropolis](https://www.nm.gov.hk/en/) | Northern Metropolis policy, districts, delivery |
| Northern Metropolis latest news | 1 | `public_page_extract_allowed` | [NM latest news](https://www.nm.gov.hk/en/trending-in-nm/latest-news) | Time-sensitive NM updates |
| Northern Metropolis overview | 1 | `public_page_extract_allowed` | [NM overview](https://www.nm.gov.hk/en/about-nm/overview) | Core strategy and district context |

## 3.4 Transport, mobility, public works, port and airport

| Source | Tier | Suggested policy | Link | Key uses |
|---|---:|---|---|---|
| Transport Department | 1 | `public_page_extract_allowed` | [Transport Department](https://www.td.gov.hk/en/home/index.html) | Traffic policy, transport figures |
| Transport statistics | 1 | `official_api` / `public_page_extract_allowed` | [Transport figures](https://www.td.gov.hk/en/transport_in_hong_kong/transport_figures/index.html) | Traffic and public-transport data |
| Highways Department | 1 | `public_page_extract_allowed` | [Highways Department](https://www.hyd.gov.hk/en/index.html) | Roads, bridges, highways |
| Highways Department press releases | 1 | `public_page_extract_allowed` | [HyD press releases](https://www.hyd.gov.hk/en/information_corner/press_releases/index.html) | Tenders, construction and road-project updates |
| Highways Department road projects | 1 | `public_page_extract_allowed` | [Road projects](https://www.hyd.gov.hk/en/road_and_railway/road_projects/index.html) | Project details |
| MTR Corporation | 2 | `public_page_extract_allowed` | [MTR](https://www.mtr.com.hk/en/customer/main/index.html) | Public transport and operations |
| MTR projects | 2 | `public_page_extract_allowed` | [MTR projects](https://www.mtr.com.hk/en/corporate/projects/projects.html) | Railway-project timelines and scope |
| MTR investor relations | 2 | `metadata_only` / `manual_only` | [MTR investor relations](https://www.mtr.com.hk/en/corporate/investor/investor_relations.html) | Financial disclosures, corporate context |
| Airport Authority Hong Kong | 2 | `public_page_extract_allowed` | [Hong Kong Airport](https://www.hongkongairport.com/en/) | Airport development, passenger/cargo stories |
| Airport Authority media centre | 2 | `public_page_extract_allowed` | [AAHK media centre](https://www.hongkongairport.com/en/media-centre/index.page) | Primary airport announcements |
| Transport and Logistics Bureau | 1 | `public_page_extract_allowed` | [TLB](https://www.tlb.gov.hk/eng/index.html) | Transport/logistics policy |
| TLB transport press releases | 1 | `public_page_extract_allowed` | [TLB press releases](https://www.tlb.gov.hk/eng/pressreleases/transport/index.html) | Primary policy updates |
| TLB Gazette notices | 1 | `manual_only` / `sitemap_only` | [Gazette notices](https://www.tlb.gov.hk/eng/publications/transport/gazette/gazette_2026.html) | Early statutory transport/road/rail signals |
| Marine Department | 1 | `public_page_extract_allowed` | [Marine Department](https://www.mardep.gov.hk/en/home/index.html) | Maritime operations, notices, regulation |
| Hong Kong Maritime and Port Development Board | 1 | `public_page_extract_allowed` | [HKMPB](https://www.hkmpb.gov.hk/en/index.html) | Maritime policy, port development |
| Hong Kong Port | 2 | `public_page_extract_allowed` | [Hong Kong Port](https://www.hkport.gov.hk/en/home.html) | Port statistics and port operations |
| Logistics Hong Kong | 1 | `public_page_extract_allowed` | [Logistics Hong Kong](https://www.logisticshk.gov.hk/en/index.html) | Smart logistics and logistics policy |
| Port Community System news | 1 | `public_page_extract_allowed` | [PCS news](https://www.logisticshk.gov.hk/en/information/news/index.html) | Digital-port and logistics updates |

## 3.5 Economy, money, business and corporate disclosures

| Source | Tier | Suggested policy | Link | Key uses |
|---|---:|---|---|---|
| Census and Statistics Department | 1 | `official_api` / `public_page_extract_allowed` | [C&SD](https://www.censtatd.gov.hk/en/) | Official economic, labour, trade and population data |
| Hong Kong Monthly Digest of Statistics | 1 | `manual_only` / document archive | [Monthly Digest](https://www.censtatd.gov.hk/en/EIndexbySubject.html?pcode=B1010002) | Recurring economic indicators |
| Hong Kong Economic Report | 1 | `manual_only` / document archive | [Economic Report](https://www.censtatd.gov.hk/en/page_800.html) | Macro-economic narrative and data |
| Labour-force statistics | 1 | `official_api` / `public_page_extract_allowed` | [Labour statistics](https://www.censtatd.gov.hk/en/scode200.html) | Employment and unemployment stories |
| Retail sales statistics | 1 | `official_api` / `public_page_extract_allowed` | [Retail sales](https://www.censtatd.gov.hk/en/scode540.html) | Consumer and retail trends |
| GDP statistics | 1 | `official_api` / `public_page_extract_allowed` | [GDP statistics](https://www.censtatd.gov.hk/en/scode310.html) | Growth and economic-cycle stories |
| Hong Kong Monetary Authority | 1 | `public_page_extract_allowed` | [HKMA](https://www.hkma.gov.hk/) | Monetary, financial stability and market context |
| HKMA publications and research | 1 | `manual_only` / document archive | [HKMA research](https://www.hkma.gov.hk/eng/publications-and-research/) | Rates, finance, property/macroeconomic analysis |
| HKMA monetary statistics | 1 | `official_api` / `public_page_extract_allowed` | [Monetary statistics](https://www.hkma.gov.hk/eng/data-publications-and-research/data-and-statistics/monetary-statistics/) | Deposits, loans, financial conditions |
| Financial Services and Treasury Bureau | 1 | `public_page_extract_allowed` | [FSTB](https://www.fstb.gov.hk/en/) | Fiscal and financial-services policy |
| Invest Hong Kong | 2 | `public_page_extract_allowed` | [InvestHK](https://www.investhk.gov.hk/en/) | Business, investment and sector developments |
| InvestHK news | 2 | `public_page_extract_allowed` | [InvestHK news](https://www.investhk.gov.hk/en/news.html) | Investment and company announcements |
| Hong Kong Trade Development Council | 2 | `public_page_extract_allowed` | [HKTDC](https://www.hktdc.com/) | Trade, events and business context |
| HKTDC Research | 4 | `public_page_extract_allowed` | [HKTDC Research](https://research.hktdc.com/en/) | Industry and trade analysis |
| Hong Kong Exchanges and Clearing | 1 | `metadata_only` / `manual_only` | [HKEX](https://www.hkex.com.hk/) | Listed-market context |
| HKEXnews announcements | 1 | `metadata_only` / `manual_only` | [HKEXnews](https://www1.hkexnews.hk/listedco/listconews/index.htm) | Company filings and developer disclosures |

## 3.6 Technology, construction innovation and smart-city ecosystem

| Source | Tier | Suggested policy | Link | Key uses |
|---|---:|---|---|---|
| Construction Industry Council | 2 | `public_page_extract_allowed` | [CIC](https://www.cic.hk/en/) | Construction policy, training, innovation |
| CIC industry news | 2 | `public_page_extract_allowed` | [CIC industry news](https://www2.cic.hk/eng/main/aboutcic/media_centre/industry_news/) | Industry updates |
| CIC news centre | 2 | `public_page_extract_allowed` | [CIC news centre](https://www.cic.hk/en/news-centre) | Official CIC news |
| Construction Industry Innovation and Technology Fund | 2 | `public_page_extract_allowed` | [CITF](https://www.cic.hk/eng/our-services/funding-schemes/citf/) | Funding, tools and smart-construction stories |
| Hong Kong Productivity Council | 2 | `public_page_extract_allowed` | [HKPC](https://www.hkpc.org/en) | SME and productivity technology |
| HKPC media centre | 2 | `public_page_extract_allowed` | [HKPC media centre](https://www.hkpc.org/en/about-us/media-centre) | Digitalisation and business news |
| Cyberport | 2 | `public_page_extract_allowed` | [Cyberport](https://www.cyberport.hk/en) | AI, fintech, startup ecosystem |
| Cyberport news | 2 | `public_page_extract_allowed` | [Cyberport news](https://www.cyberport.hk/en/news) | Startup, AI and digital-economy news |
| Hong Kong Science and Technology Parks | 2 | `public_page_extract_allowed` | [HKSTP](https://www.hkstp.org/) | Technology companies and innovation ecosystem |
| HKSTP news | 2 | `public_page_extract_allowed` | [HKSTP news](https://www.hkstp.org/en/news) | Startup / innovation announcements |
| Digital Policy Office | 1 | `public_page_extract_allowed` | [Digital Policy Office](https://www.digitalpolicy.gov.hk/) | Government digital, AI, cybersecurity and smart-city policy |
| LSCM R&D Centre | 2 | `public_page_extract_allowed` | [LSCM](https://www.lscm.hk/) | Logistics and supply-chain technology |
| Hong Kong Green Building Council | 2 | `public_page_extract_allowed` | [HKGBC](https://www.hkgbc.org.hk/) | Green building and sustainability |
| Hong Kong Institute of Planners | 4 | `manual_only` / `metadata_only` | [HKIP](https://www.hkip.org.hk/) | Planning-community context |
| Hong Kong Institution of Engineers | 4 | `manual_only` / `metadata_only` | [HKIE](https://www.hkie.org.hk/) | Engineering commentary and events |
| RICS Hong Kong | 4 | `manual_only` / `metadata_only` | [RICS Hong Kong](https://www.rics.org/hong-kong/) | Property/professional context |
| Building.hk | 4 | `public_page_extract_allowed` | [Building.hk](https://www.building.hk/) | Construction/property industry leads — not the original. Pair with URA / MTR / LandsD / ITIB / GIS |
| Building.hk eBulletin | 4 | `public_page_extract_allowed` | [Building.hk eBulletin](https://www.building.hk/eBulletin.asp) | Industry story discovery; fetch `view.asp` body |

## 3.7 Primaries behind Building.hk and Unwire

Building.hk and Unwire rewrite these desks. Collect them so a hook can cite the original, not only the trade rewrite.

| Source | Tier | Suggested policy | Link | What Building.hk / Unwire usually rewrite |
|---|---:|---|---|---|
| Urban Renewal Authority press | 2 | `public_page_extract_allowed` | [URA press releases](https://www.ura.org.hk/tc/news-centre/press-releases) | 紅磡等招標、中標價、市建項目 |
| URA redevelopment projects | 2 | `public_page_extract_allowed` | [URA redevelopment](https://www.ura.org.hk/tc/project/redevelopment) | 項目範圍、伙數、公共空間 |
| MTR press releases | 2 | `public_page_extract_allowed` | [MTR press](https://www.mtr.com.hk/ch/corporate/consultancy/press_release.html) | 上蓋批出、南島線西段、鐵路加物業 |
| MTR projects | 2 | `public_page_extract_allowed` | [MTR projects](https://www.mtr.com.hk/ch/corporate/projects/projects.html) | 走線、期數、時間表 |
| Development Bureau press | 1 | `public_page_extract_allowed` | [DevB press](https://www.devb.gov.hk/tc/publications_and_press_releases/press/index.html) | 賣地、北都、用地 |
| Civil Engineering and Development Department | 1 | `public_page_extract_allowed` | [CEDD](https://www.cedd.gov.hk/tc/our-projects/index.html) | 洪水橋物流地、新發展區工程 |
| Highways Department press | 1 | `public_page_extract_allowed` | [HyD press](https://www.hyd.gov.hk/tc/information_corner/press_releases/index.html) | 軌道、公路、意向書 |
| Innovation, Technology and Industry Bureau | 1 | `public_page_extract_allowed` | [ITIB](https://www.itib.gov.hk/en/index.html) | 沙嶺數據園、算力、創科用地。公報亦見 GIS |
| GIS press releases | 1 | `public_page_extract_allowed` | [GIS today](https://www.info.gov.hk/gia/general/today.htm) | 施政報告、口岸、各局新聞稿正本 |
| 2026 Policy Address | 1 | `manual_only` | [Policy Address 2026](https://www.policyaddress.gov.hk/2026/en/index.html) | AI 專員、大學城、五年規劃原文 |
| HKEXnews | 1 | `metadata_only` | [HKEXnews](https://www1.hkexnews.hk/listedco/listconews/index.htm) | 復星、中海、港鐵、上市公司動土／中標 |
| Unwire.hk | 3 | `public_page_extract_allowed` | [Unwire.hk](https://unwire.hk/) + [RSS](https://feeds.feedburner.com/unwirelife/) | HK tech/life rewrite of GIS / 公司稿 |
| Unwire Pro | 3 | `public_page_extract_allowed` | [Unwire Pro](https://unwire.pro/) + [RSS](https://www.unwire.pro/feed/) | 半島＋東創等 B2B；拉 `.entry-content` |

---

# 4. Free Professional Property Research

> **Use:** attributed interpretation, outlooks, commercial-market detail, office/retail/logistics trends, investor sentiment, and story ideas. Do not treat forecasts as government facts. Cross-check material market claims with RVD, Land Registry, C&SD, HKMA, company filings, and other independent sources.

| Source | Tier | Suggested policy | Link | Key uses |
|---|---:|---|---|---|
| CBRE Hong Kong Insights | 4 | `metadata_only` / `public_page_extract_allowed` where permitted | [CBRE Insights](https://www.cbre.com.hk/insights) | Residential, office, retail, capital markets |
| CBRE Hong Kong market outlook | 4 | `manual_only` / report archive | [CBRE Outlook 2026](https://www.cbre.com.hk/insights/reports/hong-kong-major-report-hong-kong-market-outlook-2026) | Annual outlook and forecasts |
| CBRE residential market insight | 4 | `metadata_only` | [CBRE residential insight](https://www.cbre.com.hk/insights/articles/hong-kong-residential-market-2026-recovery-amid-headwinds) | Residential analysis |
| JLL Hong Kong Insights | 4 | `metadata_only` | [JLL Insights](https://www.jll.com/en-hk/insights) | Commercial/residential market context |
| JLL Hong Kong monthly market dynamics | 4 | `metadata_only` | [JLL Monthly](https://www.jll.com/en-hk/insights/market-dynamics/hong-kong-monthly) | Monthly trends |
| JLL Hong Kong residential dynamics | 4 | `metadata_only` | [JLL Residential](https://www.jll.com/en-hk/insights/market-dynamics/hong-kong-residential) | Residential trends |
| Knight Frank Hong Kong Research | 4 | `metadata_only` | [Knight Frank Research](https://www.knightfrank.com.hk/research) | Market reports |
| Knight Frank Hong Kong Blog | 4 | `metadata_only` | [Knight Frank Blog](https://www.knightfrank.com.hk/blog) | Monthly updates and commentary |
| Knight Frank Q2 2026 report PDF | 4 | `manual_only` / document archive | [Knight Frank Q2 2026 PDF](https://content.knightfrank.com/research/3026/documents/en/hong-kong-market-report-2026-q2-12969.pdf) | Office, residential, retail data |
| Cushman & Wakefield Hong Kong Research | 4 | `metadata_only` | [Cushman & Wakefield report](https://www.cushmanwakefield.com/en/greater-china/insights/hong-kong-office-retail-residential-investment-market-report) | Office, retail, residential, investment |
| Savills Hong Kong Research | 4 | `metadata_only` | [Savills Research](https://www.savills.com.hk/research.aspx) | Sector research and market reports |
| Colliers Hong Kong Research | 4 | `metadata_only` | [Colliers Research](https://www.colliers.com/en-hk/research) | Commercial and investment-property analysis |
| Centaline Property Research Centre | 4 | `metadata_only` | [Centaline Research](https://hk.centanet.com/info/property-research/) | Fast local market sentiment and agency data |
| Midland Realty Research | 4 | `metadata_only` | [Midland Research](https://www.midland.com.hk/en/research/) | Market commentary and local property data |
| Hong Kong Property Services | 4 | `metadata_only` | [Hong Kong Property](https://www.hkp.com.hk/en) | Listing/deal context and sentiment leads |

---

# 5. News and Context Sources

> **Use:** story leads, interviews, reactions, public context, and cross-checking. For every major factual claim, trace back to a Tier 1 or Tier 2 original source whenever possible.

## 5.1 Hong Kong and regional news

| Source | Tier | Suggested policy | Link |
|---|---:|---|---|
| RTHK News | 3 | `metadata_only` | [RTHK News](https://news.rthk.hk/rthk/en/) |
| The Standard | 3 | `metadata_only` | [The Standard](https://www.thestandard.com.hk/) |
| Hong Kong Free Press | 3 | `metadata_only` | [HKFP](https://hongkongfp.com/) |
| South China Morning Post | 3 | `metadata_only` | [SCMP](https://www.scmp.com/) |
| Hong Kong Economic Times | 3 | `metadata_only` | [HKET](https://www.hket.com/) |
| Ming Pao | 3 | `metadata_only` | [Ming Pao](https://news.mingpao.com/) |
| Unwire.hk | 3 | `public_page_extract_allowed` | [Unwire.hk](https://unwire.hk/) |
| Unwire Pro | 3 | `public_page_extract_allowed` | [Unwire Pro](https://unwire.pro/) |
| Sing Tao | 3 | `metadata_only` | [Sing Tao](https://www.singtao.ca/) |
| Now News | 3 | `metadata_only` | [Now News](https://news.now.com/) |
| TVB News | 3 | `metadata_only` | [TVB News](https://news.tvb.com/) |
| Yahoo Finance Hong Kong | 3 | `metadata_only` | [Yahoo Finance HK](https://hk.finance.yahoo.com/) |
| Reuters Asia-Pacific | 3 | `metadata_only` | [Reuters Asia-Pacific](https://www.reuters.com/world/asia-pacific/) |
| Reuters Hong Kong search | 3 | `manual_only` | [Reuters search: Hong Kong](https://www.reuters.com/site-search/?query=Hong%20Kong) |
| Nikkei Asia | 3 | `metadata_only` | [Nikkei Asia](https://asia.nikkei.com/) |
| Bloomberg Asia | 3 | `metadata_only` | [Bloomberg Asia](https://www.bloomberg.com/asia) |
| Financial Times Asia-Pacific | 3 | `metadata_only` | [Financial Times Asia-Pacific](https://www.ft.com/asia-pacific) |

## 5.2 Global technology and AI official sources

| Source | Tier | Suggested policy | Link | Key uses |
|---|---:|---|---|---|
| OpenAI News | 2 | `public_page_extract_allowed` | [OpenAI News](https://openai.com/news/) | Model/product/company news |
| OpenAI release notes | 2 | `public_page_extract_allowed` | [OpenAI Release Notes](https://help.openai.com/en/articles/9624314-model-release-notes) | Capability and product changes |
| Anthropic Newsroom | 2 | `public_page_extract_allowed` | [Anthropic News](https://www.anthropic.com/news) | Claude/product research updates |
| Google AI Blog | 2 | `public_page_extract_allowed` | [Google AI Blog](https://blog.google/technology/ai/) | AI product and research updates |
| Google DeepMind Blog | 2 | `public_page_extract_allowed` | [DeepMind Blog](https://deepmind.google/discover/blog/) | Research and model updates |
| Microsoft AI Blog | 2 | `public_page_extract_allowed` | [Microsoft AI](https://blogs.microsoft.com/on-the-issues/ai/) | Microsoft AI policy/products |
| Microsoft Azure AI Blog | 2 | `public_page_extract_allowed` | [Azure AI Blog](https://azure.microsoft.com/en-us/blog/tag/ai-machine-learning/) | Enterprise AI and cloud tools |
| Meta AI Blog | 2 | `public_page_extract_allowed` | [Meta AI](https://ai.meta.com/blog/) | Models and research |
| NVIDIA Blog | 2 | `public_page_extract_allowed` | [NVIDIA Blog](https://blogs.nvidia.com/) | GPUs, AI infrastructure and software |
| AWS Machine Learning Blog | 2 | `public_page_extract_allowed` | [AWS ML Blog](https://aws.amazon.com/blogs/machine-learning/) | Cloud AI and machine learning |
| Alibaba Cloud News | 2 | `public_page_extract_allowed` | [Alibaba Cloud News](https://www.alibabacloud.com/en/news) | China/Asia cloud and AI updates |
| Tencent Cloud Blog | 2 | `public_page_extract_allowed` | [Tencent Cloud Blog](https://www.tencentcloud.com/blog) | China/Asia cloud and AI updates |
| DeepSeek | 2 | `manual_only` / `public_page_extract_allowed` | [DeepSeek](https://www.deepseek.com/) | Official model/company updates |
| Mistral AI News | 2 | `public_page_extract_allowed` | [Mistral News](https://mistral.ai/news/) | Model and enterprise updates |

## 5.3 Global technology journalism

| Source | Tier | Suggested policy | Link |
|---|---:|---|---|
| The Verge AI | 3 | `metadata_only` | [The Verge AI](https://www.theverge.com/ai-artificial-intelligence) |
| MIT Technology Review AI | 3 | `metadata_only` | [MIT Technology Review AI](https://www.technologyreview.com/topic/artificial-intelligence/) |
| TechCrunch AI | 3 | `metadata_only` | [TechCrunch AI](https://techcrunch.com/category/artificial-intelligence/) |
| Wired AI | 3 | `metadata_only` | [Wired AI](https://www.wired.com/tag/artificial-intelligence/) |
| Ars Technica | 3 | `metadata_only` | [Ars Technica](https://arstechnica.com/) |

---

# 6. Paid / Optional Sources

> **Rule:** do not subscribe to everything. Start with one premium journalism subscription, one search/research API, and one LLM provider. Add specialist market data only after it creates a clear revenue advantage or supports a paid intelligence product.

## 6.1 Premium journalism subscriptions

| Service | Typical editorial value | Link | Suggested stage |
|---|---|---|---|
| SCMP subscription | Local Hong Kong, policy, property, China, GBA | [SCMP Subscribe](https://subscribe.scmp.com/) | Early optional |
| Bloomberg subscription | Global markets, rates, capital flows, listed companies | [Bloomberg Subscriptions](https://www.bloomberg.com/subscriptions) | Later if finance expands |
| Financial Times subscription | Macro, capital markets, business and global policy | [FT Products](https://www.ft.com/products) | Later if macro/investment expands |
| Nikkei Asia subscription | Asia business, China, supply chain, investment | [Nikkei Asia Subscription](https://asia.nikkei.com/Subscription) | Early optional |
| Wall Street Journal subscription | Global business/markets | [WSJ Subscribe](https://subscribe.wsj.com/) | Optional |
| The Economist subscription | Global macro and city/business context | [The Economist Subscribe](https://www.economist.com/subscribe) | Optional |
| Caixin Global subscription | China policy, developers, corporate and financial news | [Caixin Global](https://www.caixinglobal.com/subscribe/) | Useful if mainland coverage grows |
| The Information | Technology/company intelligence | [The Information Subscribe](https://www.theinformation.com/subscribe) | Later, if AI/tech coverage is premium-led |

## 6.2 Premium market, financial and property data

| Service | Use case | Link | Suggested stage |
|---|---|---|---|
| Bloomberg Terminal | Professional financial data/news | [Bloomberg Terminal](https://www.bloomberg.com/professional/solution/bloomberg-terminal/) | Do not buy initially |
| LSEG Workspace | Markets, company and economic data | [LSEG Workspace](https://www.lseg.com/en/data-analytics/products/workspace) | Do not buy initially |
| FactSet | Financial/company analysis | [FactSet](https://www.factset.com/) | Later |
| S&P Capital IQ Pro | Company, deals, financial data | [Capital IQ Pro](https://www.spglobal.com/marketintelligence/en/solutions/sp-capital-iq-pro) | Later |
| MSCI Real Assets | Institutional property/real-assets data | [MSCI Real Assets](https://www.msci.com/our-solutions/real-assets) | Later / B2B intelligence |
| CoStar | Commercial-property research/data | [CoStar](https://www.costar.com/) | Later / commercial-property focus |
| Real Capital Analytics | Property investment transactions | [Real Capital Analytics](https://www.mscirealassets.com/real-capital-analytics/) | Later |
| Argus Enterprise | Commercial real-estate valuation/cash-flow analysis | [Argus Enterprise](https://www.altusgroup.com/argus/argus-enterprise/) | Only if building paid property analytics |
| Statista | General market data and charts | [Statista](https://www.statista.com/) | Optional |
| CEIC Data | Asian macroeconomic data | [CEIC](https://www.ceicdata.com/) | Later if macro data needs deepen |
| Oxford Economics | Forecasts and macro research | [Oxford Economics](https://www.oxfordeconomics.com/) | Later |
| Fitch Solutions | Country/sector risk and forecast research | [Fitch Solutions](https://www.fitchsolutions.com/) | Later |
| BMI | Sector and country research | [BMI](https://www.fitchsolutions.com/bmi) | Later |

## 6.3 Media monitoring and social listening

| Service | Use case | Link | Suggested stage |
|---|---|---|---|
| Meltwater | Enterprise monitoring, media intelligence | [Meltwater](https://www.meltwater.com/) | Later |
| Cision | PR/media monitoring | [Cision](https://www.cision.com/) | Later |
| Muck Rack | Journalist and media-database monitoring | [Muck Rack](https://muckrack.com/) | Later |
| Brandwatch | Social listening | [Brandwatch](https://www.brandwatch.com/) | Later |
| Talkwalker | Social/media intelligence | [Talkwalker](https://www.talkwalker.com/) | Later |
| Sprinklr | Enterprise social/customer intelligence | [Sprinklr](https://www.sprinklr.com/) | Later |
| Google Alerts | Basic keyword alerts | [Google Alerts](https://www.google.com/alerts) | Start immediately — free |
| Feedly | RSS and AI-assisted monitoring | [Feedly](https://feedly.com/) | Useful optional |
| Inoreader | RSS monitoring, rules, folders | [Inoreader](https://www.inoreader.com/) | Useful optional |

---

# 7. Research Engine, Search, Crawling and AI Services

## 7.1 Discovery/search services

| Service | Suggested use | Link | Start? |
|---|---|---|---|
| Perplexity Search API | Structured web discovery, related-source finding, topic research | [Perplexity Search quickstart](https://docs.perplexity.ai/docs/search/quickstart) | Yes |
| Perplexity Search API reference | API implementation | [Search API reference](https://docs.perplexity.ai/api-reference/search-post) | Yes |
| Perplexity Sonar API | Citation-aware research answers / editorial assistance | [Sonar quickstart](https://docs.perplexity.ai/docs/sonar/quickstart) | Optional |
| Perplexity pricing | Budgeting | [Perplexity pricing](https://docs.perplexity.ai/docs/getting-started/pricing) | Yes |
| Google Programmable Search | Curated-domain or supplementary search | [Programmable Search Engine](https://programmablesearchengine.google.com/) | Later / validation |
| Google Custom Search API | JSON API for Google custom engine | [Custom Search overview](https://developers.google.com/custom-search/v1/overview) | Later / validation |
| Google Custom Search API reference | API implementation | [JSON API reference](https://developers.google.com/custom-search/docs/json_api_reference) | Later |
| Tavily | AI-oriented web search/research API | [Tavily Docs](https://docs.tavily.com/) | Optional alternative |
| SerpAPI | Search-result API | [SerpAPI](https://serpapi.com/) | Optional alternative |
| Brave Search API | Search/discovery API | [Brave Search API](https://brave.com/search/api/) | Optional alternative |

## 7.2 Extraction and collection tools

| Service | Suggested use | Link | Start? |
|---|---|---|---|
| Firecrawl | Public webpage fetch/extraction where permitted | [Firecrawl](https://www.firecrawl.dev/) | Later only if normal fetches fail |
| Apify | Managed public-web actors and workflows | [Apify](https://apify.com/) | Later only |
| Browserless | Headless browser execution for permitted sites | [Browserless](https://www.browserless.io/) | Later only |
| Diffbot | Structured article/entity extraction | [Diffbot](https://www.diffbot.com/) | Later / expensive |

## 7.3 LLM, database, automation and hosting tools

| Service | Suggested use | Link | Start? |
|---|---|---|---|
| OpenRouter | Model routing for classification, summaries and drafts | [OpenRouter](https://openrouter.ai/) | Yes |
| Supabase | Managed Postgres, auth, storage, pgvector | [Supabase](https://supabase.com/) | Free tier initially |
| Supabase pricing | Upgrade decision | [Supabase pricing](https://supabase.com/pricing) | Reference |
| n8n | Workflow scheduling and orchestration | [n8n](https://n8n.io/) | Yes, self-hosted |
| n8n self-hosting docs | Deployment reference | [n8n Hosting docs](https://docs.n8n.io/hosting/) | Yes |
| n8n import/export | Version-controlled workflow handling | [Workflow import/export](https://docs.n8n.io/workflows/export-import/) | Yes |
| Cloudflare | DNS, security, CDN, optional edge tooling | [Cloudflare](https://www.cloudflare.com/) | Yes, free tier |
| Cloudflare Workers | Edge functions later | [Cloudflare Workers](https://workers.cloudflare.com/) | Later |
| Cloudflare R2 | Object storage later | [Cloudflare R2](https://www.cloudflare.com/developer-platform/products/r2/) | Later |
| Vultr pricing | Hong Kong VPS reference | [Vultr pricing](https://www.vultr.com/pricing/) | Yes, evaluate VPS |
| LayerStack pricing | Hong Kong VPS reference | [LayerStack pricing](https://www.layerstack.com/zh-hk/pricing) | Evaluate alternative |

---

# 8. Suggested Initial Watchlist

Start with 25–35 sources. Do not ingest hundreds of sources on day one.

## Core primary-source watchlist

1. [GovHK News](https://www.news.gov.hk/eng/index.html)
2. [Government Information Services](https://www.info.gov.hk/gia/general/today.htm)
3. [DATA.GOV.HK](https://data.gov.hk/en/)
4. [RVD Property Market Statistics](https://www.rvd.gov.hk/en/publications/property_market_statistics.html)
5. [Land Registry Monthly Statistics](https://www.landreg.gov.hk/en/monthly/monthly.htm)
6. [C&SD](https://www.censtatd.gov.hk/en/)
7. [HKMA](https://www.hkma.gov.hk/)
8. [Development Bureau](https://www.devb.gov.hk/en/index.html)
9. [Planning Department](https://www.pland.gov.hk/pland_en/index.html)
10. [Town Planning Board](https://www.tpb.gov.hk/en/)
11. [Lands Department Land Sale Information](https://www.landsd.gov.hk/en/landsale/land-sale-information.html)
12. [CEDD Projects](https://www.cedd.gov.hk/eng/our-projects/index.html)
13. [Northern Metropolis](https://www.nm.gov.hk/en/)
14. [Highways Department Press Releases](https://www.hyd.gov.hk/en/information_corner/press_releases/index.html)
15. [MTR Projects](https://www.mtr.com.hk/en/corporate/projects/projects.html)
16. [Transport and Logistics Bureau](https://www.tlb.gov.hk/eng/index.html)
17. [Transport Gazette Notices](https://www.tlb.gov.hk/eng/publications/transport/gazette/gazette_2026.html)
18. [Airport Authority Media Centre](https://www.hongkongairport.com/en/media-centre/index.page)
19. [Construction Industry Council](https://www.cic.hk/en/news-centre)
20. [Cyberport News](https://www.cyberport.hk/en/news)
21. [HKSTP News](https://www.hkstp.org/en/news)
22. [HKPC Media Centre](https://www.hkpc.org/en/about-us/media-centre)
23. [Digital Policy Office](https://www.digitalpolicy.gov.hk/)
24. [Logistics Hong Kong](https://www.logisticshk.gov.hk/en/information/news/index.html)

## Core context/research watchlist

25. [CBRE Hong Kong Insights](https://www.cbre.com.hk/insights)
26. [JLL Hong Kong Insights](https://www.jll.com/en-hk/insights)
27. [Knight Frank Hong Kong Research](https://www.knightfrank.com.hk/research)
28. [Cushman & Wakefield Hong Kong](https://www.cushmanwakefield.com/en/greater-china/insights/hong-kong-office-retail-residential-investment-market-report)
29. [RTHK News](https://news.rthk.hk/rthk/en/)
30. [Reuters Asia-Pacific](https://www.reuters.com/world/asia-pacific/)
31. [SCMP](https://www.scmp.com/)
32. [OpenAI News](https://openai.com/news/)
33. [Anthropic News](https://www.anthropic.com/news)
34. [Google AI Blog](https://blog.google/technology/ai/)
35. [NVIDIA Blog](https://blogs.nvidia.com/)

---

# 9. Recommended Paid Subscription Order

Do not buy all services at once.

1. **VPS + domain + Cloudflare Free** — research-engine infrastructure.
2. **Perplexity Search API** — structured discovery and topic research.
3. **One LLM provider / OpenRouter** — classification, summaries, editorial briefs.
4. **One premium journalism subscription** — choose one:
   - [SCMP](https://subscribe.scmp.com/) for Hong Kong / GBA local depth
   - [Nikkei Asia](https://asia.nikkei.com/Subscription) for Asia business and China context
   - [Financial Times](https://www.ft.com/products) or [Bloomberg](https://www.bloomberg.com/subscriptions) if macro/markets become central
5. **Supabase Pro** only when daily ingestion and production reliability require it.
6. **Feedly Pro or Inoreader Pro** only if source monitoring becomes too inconvenient in your own engine.
7. **Specialist property/financial data** only when you have a premium B2B intelligence product or a clear monetisation case.

---

# 10. Editorial Use Reminder

For every publishable story:

1. Start with a Tier 1 or Tier 2 source where possible.
2. Add Tier 3 reporting for context or response.
3. Add Tier 4 research for attributed market interpretation.
4. Use Tier 5 only for sentiment and leads.
5. Preserve original URL, title, publication date, retrieval timestamp, source tier, evidence excerpt, and source version.
6. Clearly distinguish:
   - Official fact
   - Company/developer statement
   - Consultancy forecast
   - Editorial analysis
   - Opinion
7. Do not present investment, property, mortgage, legal, or financial advice.

Suggested disclaimer for relevant stories:

> 本文只作新聞、教育及一般資訊用途，不構成投資、置業、法律、按揭或財務建議。讀者應按自身情況尋求合資格專業人士意見。
