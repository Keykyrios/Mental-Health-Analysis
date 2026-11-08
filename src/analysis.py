"""Analysis for the seed deck: exam-aspirant mental healthcare, India.

Run from the repo root:  python src/analysis.py
Writes figures to figures/ and key numbers to results.json.

Everything marked MODEL is an assumption set by the founders, not a measurement.
Everything marked DATA comes from data/*.csv (sources in SOURCES.md).
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3d projection)
from scipy import stats

RNG = np.random.default_rng(20261104)
BG, TXT, MUT, AMB, HAIR = "#0B0B0A", "#F2F0EA", "#A9A69E", "#E9A23B", "#2A2A27"
CMAP = LinearSegmentedColormap.from_list("lamp", ["#1D1D1B", "#6E4A17", AMB, "#F6D9A0"])
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "text.color": TXT, "axes.labelcolor": MUT, "axes.edgecolor": HAIR,
    "xtick.color": MUT, "ytick.color": MUT, "grid.color": HAIR,
    "font.family": "DejaVu Sans", "font.size": 11, "axes.titlesize": 14,
    "axes.titlecolor": TXT, "axes.spines.top": False, "axes.spines.right": False,
})
OUT = {}


def save(fig, name):
    fig.savefig(f"figures/{name}.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def style3d(ax):
    for a in (ax.xaxis, ax.yaxis, ax.zaxis):
        a.set_pane_color((0.04, 0.04, 0.04, 1.0))
        a._axinfo["grid"]["color"] = HAIR
    ax.tick_params(colors=MUT)


# ------------------------------------------------------------------ DATA
neet = pd.read_csv("data/neet_state_2022_2024.csv")
pop = pd.read_csv("data/population_census2011.csv")
nat = pd.read_csv("data/ncrb_student_suicides_national.csv")

# Data-quality check: 2022 column of the source does not tie to its printed total.
OUT["neet_2022_row_sum"] = int(neet.reg_2022.sum())
OUT["neet_2022_printed_total_excl_OTHER"] = 1597435 - 1659
OUT["neet_2023_row_sum"] = int(neet.reg_2023.sum())
OUT["neet_2024_row_sum"] = int(neet.reg_2024.sum())

# Merge states so names match Census 2011 geography.
m = neet.copy()
m["unit"] = m.state
m.loc[m.state.isin(["Andhra Pradesh", "Telangana"]), "unit"] = "Andhra Pradesh + Telangana"
m.loc[m.state.isin(["Jammu and Kashmir", "Ladakh"]), "unit"] = "Jammu and Kashmir + Ladakh"
cols = [c for c in m.columns if c not in ("state", "unit")]
g = m.groupby("unit")[cols].sum().reset_index().rename(columns={"unit": "state"})
g = g.merge(pop, on="state", how="inner")  # drops tiny UTs with no Census row
g = g[g.population_2011 > 1_000_000].copy()  # avoid per-capita noise in micro UTs
g["reg24_per_lakh"] = g.reg_2024 / (g.population_2011 / 1e5)
g["growth_23_24"] = g.reg_2024 / g.reg_2023 - 1
g["qual_rate_24"] = g.qual_2024 / g.app_2024
g["appear_rate_24"] = g.app_2024 / g.reg_2024
g["share_24"] = g.reg_2024 / g.reg_2024.sum()
g = g.sort_values("reg_2024", ascending=False).reset_index(drop=True)
g.to_csv("figures/state_table.csv", index=False)
OUT["states_analysed"] = int(len(g))

# ------------------------------------------------ FIG 01 national trend
x = nat.year.values
y = nat.student_suicides.values
res = stats.linregress(x, y)
n = len(x)
xf = np.arange(2014, 2028)
yhat = res.intercept + res.slope * xf
se = np.sqrt(np.sum((y - (res.intercept + res.slope * x)) ** 2) / (n - 2))
t = stats.t.ppf(0.975, n - 2)
pi = t * se * np.sqrt(1 + 1 / n + (xf - x.mean()) ** 2 / np.sum((x - x.mean()) ** 2))
OUT["trend_slope_per_year"] = round(res.slope, 1)
OUT["trend_r2"] = round(res.rvalue ** 2, 3)
OUT["growth_2014_2024_pct"] = round((y[-1] / y[0] - 1) * 100, 1)
OUT["cagr_2014_2024_pct"] = round(((y[-1] / y[0]) ** (1 / 10) - 1) * 100, 2)
OUT["extrapolated_2027"] = [round(yhat[-1]), round(yhat[-1] - pi[-1]), round(yhat[-1] + pi[-1])]
fig, ax = plt.subplots(figsize=(11, 5.6))
ax.bar(x, y, color=HAIR, width=0.62, zorder=2)
ax.bar(x[-1], y[-1], color=AMB, width=0.62, zorder=3)
ax.plot(xf, yhat, color=AMB, lw=1.8, zorder=4)
fut = xf > 2024
ax.fill_between(xf[fut], (yhat - pi)[fut], (yhat + pi)[fut], color=AMB, alpha=0.18, zorder=1)
for xi, yi in zip(x, y):
    ax.text(xi, yi + 180, f"{yi:,}", ha="center", color=MUT, fontsize=9)
ax.set_title("Student suicides in India, NCRB 2014-2024, with straight-line extrapolation to 2027", loc="left")
ax.set_ylabel("Student suicides a year")
ax.set_xticks(xf)
ax.set_ylim(0, 19000)
ax.grid(axis="y", zorder=0)
ax.text(2014.1, 17600, f"+{OUT['growth_2014_2024_pct']}% in ten years  |  {OUT['cagr_2014_2024_pct']}% a year compounded  |  "
        f"trend adds about {res.slope:,.0f} a year (R2 {res.rvalue**2:.2f})", color=TXT, fontsize=11)
ax.text(2024.6, 8200, "shaded: 95% prediction band\nextrapolation, not a forecast", color=MUT, fontsize=9)
save(fig, "fig01_student_suicide_trend")

# ------------------------------------------ FIG 02 state intensity bubble
fig, ax = plt.subplots(figsize=(11, 6.2))
med_i, med_g = g.reg24_per_lakh.median(), g.growth_23_24.median()
ax.axvline(med_i, color=HAIR, lw=1)
ax.axhline(med_g * 100, color=HAIR, lw=1)
sz = g.reg_2024 / g.reg_2024.max() * 1800 + 25
hot = (g.reg24_per_lakh > med_i) & (g.growth_23_24 > med_g)
ax.scatter(g.reg24_per_lakh[~hot], g.growth_23_24[~hot] * 100, s=sz[~hot], color="#6E6C66", alpha=0.75, edgecolor=BG, zorder=3)
ax.scatter(g.reg24_per_lakh[hot], g.growth_23_24[hot] * 100, s=sz[hot], color=AMB, alpha=0.9, edgecolor=BG, zorder=4)
for _, r in g.iterrows():
    if r.reg_2024 > 90000 or r.growth_23_24 > 0.3 or r.reg24_per_lakh > 280:
        ax.annotate(r.state.replace(" + ", "+").replace("Andhra Pradesh+Telangana", "AP+Telangana").replace("Jammu and Kashmir+Ladakh", "J&K+Ladakh"),
                    (r.reg24_per_lakh, r.growth_23_24 * 100), xytext=(6, 6), textcoords="offset points", color=TXT, fontsize=9)
ax.set_xlabel("NEET UG 2024 registrations per lakh people (Census 2011 base)")
ax.set_ylabel("Growth in registrations, 2023 to 2024 (%)")
ax.set_title("Where aspirants are dense and growing fastest (bubble = registrations)", loc="left")
ax.grid(alpha=0.5)
save(fig, "fig02_state_intensity_growth")
OUT["hot_states"] = g[hot].state.tolist()
OUT["top5_share_2024_pct"] = round(g.share_24.head(5).sum() * 100, 1)
OUT["top5_states_2024"] = g.state.head(5).tolist()

# ------------------------------------------- FIG 03 3D scatter state space
fig = plt.figure(figsize=(10.5, 7.2))
ax = fig.add_subplot(111, projection="3d")
style3d(ax)
zmin = g.qual_rate_24.min() * 100 - 3
for _, r in g.iterrows():
    ax.plot([r.reg24_per_lakh] * 2, [r.growth_23_24 * 100] * 2, [zmin, r.qual_rate_24 * 100], color=HAIR, lw=0.8)
ax.set_zlim(zmin, g.qual_rate_24.max() * 100 + 4)
sc = ax.scatter(g.reg24_per_lakh, g.growth_23_24 * 100, g.qual_rate_24 * 100,
                s=sz * 0.5, c=g.reg_2024, cmap=CMAP, edgecolor=BG, depthshade=False, alpha=0.95)
for _, r in g.head(8).iterrows():
    ax.text(r.reg24_per_lakh, r.growth_23_24 * 100, r.qual_rate_24 * 100 + 1.4,
            r.state.replace("Andhra Pradesh + Telangana", "AP+TG").replace("Jammu and Kashmir + Ladakh", "J&K"), color=TXT, fontsize=8)
ax.set_xlabel("Registrations per lakh people", labelpad=10)
ax.set_ylabel("Growth 2023-24 (%)", labelpad=10)
ax.set_zlabel("Qualified of appeared (%)", labelpad=8)
ax.view_init(elev=22, azim=-58)
ax.set_title("States in three dimensions: density, growth, and pass rate (colour = registrations)", loc="left")
cb = fig.colorbar(sc, ax=ax, shrink=0.55, pad=0.08)
cb.outline.set_edgecolor(HAIR)
cb.ax.tick_params(colors=MUT)
save(fig, "fig03_state_space_3d")

# 3D bars: top 12 states by registrations, 2023 vs 2024
top = g.head(10)
fig = plt.figure(figsize=(13, 7.4))
ax = fig.add_subplot(111, projection="3d")
style3d(ax)
for yi, col, c in [(0, "reg_2023", "#6E6C66"), (1, "reg_2024", AMB)]:
    ax.bar3d(np.arange(len(top)), np.full(len(top), yi * 1.1), np.zeros(len(top)), 0.7, 0.8, top[col].values / 1000,
             color=c, shade=True, edgecolor=BG, linewidth=0.3)
ax.set_xticks(np.arange(len(top)) + 0.35)
ax.set_xticklabels([n.replace("Andhra Pradesh + Telangana", "AP+TG").replace("Uttar Pradesh", "UP").replace("Madhya Pradesh", "MP").replace("Tamil Nadu", "TN").replace("West Bengal", "WB") for n in top.state],
                   rotation=-55, ha="left", fontsize=10)
ax.set_yticks([0.4, 1.5]); ax.set_yticklabels(["2023", "2024"])
ax.set_zlabel("NEET UG registrations (thousand)", labelpad=8)
ax.view_init(elev=24, azim=-70)
ax.set_title("The ten biggest aspirant states, 2023 against 2024 (grey = 2023, amber = 2024)", loc="left")
save(fig, "fig03b_top_states_3d_bars")

# ------------------------------------------------ FIG 04 Lorenz curve
v = np.sort(g.reg_2024.values)
cum = np.insert(np.cumsum(v) / v.sum(), 0, 0)
p = np.linspace(0, 1, len(cum))
gini = 1 - 2 * np.trapezoid(cum, p)
OUT["gini_state_registrations"] = round(float(gini), 3)
fig, ax = plt.subplots(figsize=(7.4, 6.2))
ax.plot([0, 1], [0, 1], color=HAIR, lw=1.2)
ax.plot(p, cum, color=AMB, lw=2.2)
ax.fill_between(p, cum, p, color=AMB, alpha=0.12)
ax.set_xlabel("Share of states (poorest to richest in aspirants)")
ax.set_ylabel("Share of NEET UG registrations")
ax.set_title(f"Aspirants are concentrated: Gini {gini:.2f}", loc="left")
ax.text(0.04, 0.84, f"Top 5 states hold {OUT['top5_share_2024_pct']}% of 2024 registrations", color=TXT, fontsize=11)
ax.grid(alpha=0.5)
save(fig, "fig04_concentration_lorenz")

# ------------------------------------------- Spearman correlations (heat)
feat = g[["reg24_per_lakh", "growth_23_24", "qual_rate_24", "appear_rate_24", "population_2011"]].copy()
feat.columns = ["Density", "Growth", "Pass rate", "Appear rate", "Population"]
cor = feat.corr(method="spearman")
OUT["spearman"] = cor.round(2).to_dict()
OUT["spearman_rho_crit_p05"] = round(float(2.048 / np.sqrt(len(g) - 2 + 2.048 ** 2)), 2)
fig, ax = plt.subplots(figsize=(6.4, 5.4))
im = ax.imshow(cor.values, cmap=LinearSegmentedColormap.from_list("div", ["#3A3936", BG, AMB]), vmin=-1, vmax=1)
ax.set_xticks(range(len(cor))); ax.set_xticklabels(cor.columns, rotation=30, ha="right")
ax.set_yticks(range(len(cor))); ax.set_yticklabels(cor.columns)
for i in range(len(cor)):
    for j in range(len(cor)):
        ax.text(j, i, f"{cor.values[i, j]:.2f}", ha="center", va="center", color=TXT, fontsize=10)
rcrit = 2.048 / np.sqrt(len(g) - 2 + 2.048 ** 2)  # approx. |rho| needed for p<0.05
ax.set_title(f"Rank correlations, {len(g)} states", loc="left")
ax.text(0.0, -0.32, f"|rho| above about {rcrit:.2f} is needed for p<0.05 at this sample size.\nGrowth is unrelated to density: new demand is not only in the old hubs.",
        transform=ax.transAxes, color=MUT, fontsize=9, va="top")
for s_ in ax.spines.values():
    s_.set_visible(False)
save(fig, "fig05_state_correlations")

# ---------------------------------------------------- UNIT ECONOMICS
PRICE, COST, CAC0, Q0, H = 999.0, 483.0, 750.0, 0.76, 12


def exp_months(q, h=H):
    return (1 - q ** h) / (1 - q)


def ltv_cac(price=PRICE, cost=COST, cac=CAC0, q=Q0):
    return (price - cost) * exp_months(q) / cac


base = ltv_cac()
OUT["base_exp_months"] = round(exp_months(Q0), 2)
OUT["base_ltv_cac"] = round(base, 2)
OUT["base_gross_profit_month"] = PRICE - COST
OUT["base_payback_months"] = round(CAC0 / (PRICE - COST), 2)

# FIG 06 tornado (+/-20% one at a time)
params = {"Price": "price", "Cost to serve": "cost", "CAC": "cac", "Monthly retention": "q"}
rows = []
for lab, k in params.items():
    kw_lo, kw_hi = {k: {"price": PRICE, "cost": COST, "cac": CAC0, "q": Q0}[k] * 0.8}, {k: {"price": PRICE, "cost": COST, "cac": CAC0, "q": Q0}[k] * 1.2}
    if k == "q":
        kw_hi = {"q": min(Q0 * 1.2, 0.97)}
    rows.append((lab, ltv_cac(**kw_lo), ltv_cac(**kw_hi)))
rows.sort(key=lambda r: abs(r[2] - r[1]))
OUT["tornado"] = {r[0]: [round(r[1], 2), round(r[2], 2)] for r in rows}
fig, ax = plt.subplots(figsize=(10, 4.8))
for i, (lab, lo, hi) in enumerate(rows):
    for val in (lo, hi):
        ax.barh(i, val - base, left=base, color=AMB if val > base else "#6E6C66", height=0.5, zorder=3)
    ax.text(min(lo, hi) - 0.06, i, f"{min(lo, hi):.2f}x", ha="right", va="center", color=MUT, fontsize=10)
    ax.text(max(lo, hi) + 0.06, i, f"{max(lo, hi):.2f}x", ha="left", va="center", color=TXT, fontsize=10)
ax.axvline(base, color=TXT, lw=1)
ax.axvline(3, color=AMB, lw=1, ls="--")
ax.text(3.04, len(rows) - 0.6, "3x bar", color=AMB, fontsize=9)
ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows])
ax.set_xlim(0.8, 5.9)
ax.set_xlabel("LTV to CAC")
ax.set_title(f"What moves LTV to CAC most (base {base:.2f}x; each input changed by 20%; amber = better than base)", loc="left")
ax.grid(axis="x", alpha=0.5, zorder=0)
save(fig, "fig06_tornado_ltv_cac")

# FIG 07 3D surface LTV:CAC over CAC and retention
cac_g = np.linspace(400, 1200, 60)
q_g = np.linspace(0.55, 0.90, 60)
CG, QG = np.meshgrid(cac_g, q_g)
Z = ltv_cac(cac=CG, q=QG)
fig = plt.figure(figsize=(10.5, 7.2))
ax = fig.add_subplot(111, projection="3d")
style3d(ax)
ax.computed_zorder = False
ax.plot_surface(CG, QG * 100, Z, cmap=CMAP, edgecolor="none", alpha=0.97, antialiased=True, zorder=1)
ax.plot_surface(CG, QG * 100, np.full_like(Z, 3.0), color=TXT, alpha=0.18, zorder=2)
ax.plot([CAC0, CAC0], [Q0 * 100, Q0 * 100], [base, base + 2.2], color=TXT, lw=1.8, zorder=10)
ax.scatter([CAC0], [Q0 * 100], [base + 2.2], color=TXT, s=80, depthshade=False, zorder=11)
ax.text(CAC0, Q0 * 100, base + 2.9, f"base {base:.2f}x (CAC 750, retention 76%)", color=TXT, fontsize=11, zorder=12)
ax.set_xlabel("CAC (Rs)", labelpad=10)
ax.set_ylabel("Monthly retention (%)", labelpad=10)
ax.set_zlabel("LTV to CAC (12-month horizon)", labelpad=8)
ax.view_init(elev=24, azim=-128)
ax.set_title("LTV to CAC surface: the grey plane is the 3x bar", loc="left")
save(fig, "fig07_ltvcac_surface_3d")
OUT["share_surface_above_3x_pct"] = round(float((Z >= 3).mean() * 100), 1)

# FIG 08 Monte Carlo of LTV:CAC
N = 50000
def beta_ms(mean, sd, size):
    k = mean * (1 - mean) / sd ** 2 - 1
    return RNG.beta(mean * k, (1 - mean) * k, size)
q_s = beta_ms(Q0, 0.06, N)
cac_s = RNG.triangular(500, 750, 1100, N)
real_s = RNG.uniform(0.85, 1.0, N)          # price realisation after discounts and refunds
cost_s = RNG.triangular(0.9, 1.0, 1.25, N)  # cost-to-serve multiplier (utilisation risk)
ltv_s = (PRICE * real_s - COST * cost_s) * exp_months(q_s) / cac_s
pb_s = cac_s / np.maximum(PRICE * real_s - COST * cost_s, 1)
OUT["mc_ltvcac_p5_p50_p95"] = [round(float(np.percentile(ltv_s, k)), 2) for k in (5, 50, 95)]
OUT["mc_prob_ltvcac_ge_3_pct"] = round(float((ltv_s >= 3).mean() * 100), 1)
OUT["mc_prob_ltvcac_lt_1_pct"] = round(float((ltv_s < 1).mean() * 100), 1)
OUT["mc_prob_payback_le_3m_pct"] = round(float((pb_s <= 3).mean() * 100), 1)
fig, ax = plt.subplots(figsize=(10, 5.4))
ax.hist(ltv_s, bins=90, range=(0, 8), color="#6E6C66", zorder=3)
ax.hist(ltv_s[ltv_s >= 3], bins=int(90 * 5 / 8), range=(3, 8), color=AMB, zorder=4)
ax.axvline(3, color=TXT, lw=1, ls="--")
ax.set_xlabel("LTV to CAC")
ax.set_ylabel(f"Simulated outcomes (of {N:,})")
ax.set_title(f"Monte Carlo, {N:,} draws: LTV to CAC clears 3x in {OUT['mc_prob_ltvcac_ge_3_pct']}% of them", loc="left")
ax.text(5.0, ax.get_ylim()[1] * 0.8,
        f"5th / 50th / 95th percentile\n{OUT['mc_ltvcac_p5_p50_p95'][0]}x / {OUT['mc_ltvcac_p5_p50_p95'][1]}x / {OUT['mc_ltvcac_p5_p50_p95'][2]}x\n"
        f"below 1x: {OUT['mc_prob_ltvcac_lt_1_pct']}%\npayback within 3 months: {OUT['mc_prob_payback_le_3m_pct']}%", color=TXT, fontsize=11)
ax.grid(axis="y", alpha=0.5, zorder=0)
save(fig, "fig08_montecarlo_ltv_cac")

# --------------------------------------------------------- CASH MODEL
CR, LAKH = 1e7, 1e5


def cash_path(q, cac, addmult, costmult=1.0, fixmult=1.0, price=PRICE, deliv=COST, raise_=8 * CR):
    """Vectorised 24-month cash model; q, cac, addmult, costmult may be arrays."""
    q, cac, addmult, costmult, fixmult = [np.atleast_1d(np.asarray(a, float)) for a in (q, cac, addmult, costmult, fixmult)]
    months = np.arange(1, 25)
    adds = np.where(months <= 12, 80 * months, 960 + 107.5 * (months - 12))[None, :] * addmult[:, None]
    active = np.zeros((len(q), 24))
    for m in range(24):
        for j in range(m + 1):
            active[:, m] += adds[:, j] * q ** (m - j)
    fixed = np.where(months <= 6, 16, np.where(months <= 12, 22, 30)) * LAKH
    oneoff = np.where((months >= 4) & (months <= 11), 15 * LAKH, 0)
    burn = fixed[None, :] * fixmult[:, None] + oneoff[None, :] + active * deliv * costmult[:, None] + adds * cac[:, None] - active * price
    cash = raise_ - np.cumsum(burn, axis=1)
    return cash / CR, active, burn / LAKH


b_cash, b_act, b_burn = cash_path(Q0, 750, 1.0)
OUT["cash_base_m24_cr"] = round(float(b_cash[0, -1]), 2)
OUT["active_base_m24"] = round(float(b_act[0, -1]))
OUT["burn_base_m24_lakh"] = round(float(b_burn[0, -1]), 1)
bad_cash, _, bad_burn = cash_path(0.65, 1000, 0.7)
OUT["cash_bad_m24_cr"] = round(float(bad_cash[0, -1]), 2)
OUT["burn_bad_m24_lakh"] = round(float(bad_burn[0, -1]), 1)

# FIG 09 3D surface: month-24 cash over fixed-cost creep and sign-up volume
OUT["zero_revenue_floor_cr"] = round(float(cash_path(Q0, 750, 0.0)[0][0, -1]), 2)
fx = np.linspace(0.8, 2.2, 40)
am = np.linspace(0.1, 1.3, 40)
FX, AM = np.meshgrid(fx, am)
Zc = cash_path(np.full(FX.size, Q0), np.full(FX.size, 750.0), AM.ravel(), 1.0, FX.ravel())[0][:, -1].reshape(FX.shape)
fig = plt.figure(figsize=(10.5, 7.2))
ax = fig.add_subplot(111, projection="3d")
style3d(ax)
ax.computed_zorder = False
ax.plot_surface(FX, AM, Zc, cmap=CMAP, edgecolor="none", alpha=0.96, zorder=1)
ax.plot_surface(FX, AM, np.zeros_like(Zc), color=TXT, alpha=0.18, zorder=2)
zb = float(b_cash[0, -1])
ax.plot([1, 1], [1, 1], [zb, zb + 2.0], color=TXT, lw=1.8, zorder=10)
ax.scatter([1], [1], [zb + 2.0], color=TXT, s=80, depthshade=False, zorder=11)
ax.text(1, 1, zb + 2.8, f"base Rs {zb:.2f} Cr", color=TXT, fontsize=11, zorder=12)
ax.set_xlabel("Fixed-cost multiple (1.0 = plan)", labelpad=10)
ax.set_ylabel("Sign-up volume (1.0 = plan)", labelpad=10)
ax.set_zlabel("Cash left at month 24 (Rs Cr)", labelpad=8)
ax.view_init(elev=24, azim=-48)
ax.set_title("Where the Rs 8 Cr breaks: fixed-cost creep matters far more than sign-ups (grey plane = zero)", loc="left", fontsize=12)
save(fig, "fig09_cash_surface_3d")
OUT["share_surface_cash_negative_pct"] = round(float((Zc < 0).mean() * 100), 1)
# fixed-cost multiple at which plan-volume cash hits zero
fgrid = np.linspace(1.0, 3.0, 401)
zz = cash_path(np.full(fgrid.size, Q0), np.full(fgrid.size, 750.0), np.ones(fgrid.size), 1.0, fgrid)[0][:, -1]
OUT["breakeven_fixed_multiple_at_plan_volume"] = round(float(fgrid[np.argmax(zz < 0)]), 2)

# FIG 10 Monte Carlo fan chart of cash
Nc = 20000
q_c = beta_ms(Q0, 0.06, Nc)
cac_c = RNG.triangular(600, 750, 1100, Nc)
add_c = RNG.triangular(0.5, 1.0, 1.2, Nc)
cost_c = RNG.triangular(0.95, 1.0, 1.2, Nc)
fix_c = RNG.triangular(1.0, 1.2, 1.8, Nc)  # hiring creep, ASSUMPTION
paths, _, _ = cash_path(q_c, cac_c, add_c, cost_c, fix_c)
mn = paths.min(axis=1)
OUT["mc_cash_m24_p5_p50_p95_cr"] = [round(float(np.percentile(paths[:, -1], k)), 2) for k in (5, 50, 95)]
OUT["mc_prob_cash_negative_any_month_pct"] = round(float((mn < 0).mean() * 100), 1)
OUT["mc_prob_cash_below_1cr_m24_pct"] = round(float((paths[:, -1] < 1).mean() * 100), 1)
mo = np.arange(1, 25)
fig, ax = plt.subplots(figsize=(11, 5.8))
ax.fill_between(mo, *np.percentile(paths, [5, 95], axis=0), color=AMB, alpha=0.14, label="5th to 95th percentile")
ax.fill_between(mo, *np.percentile(paths, [25, 75], axis=0), color=AMB, alpha=0.30, label="25th to 75th percentile")
ax.plot(mo, np.percentile(paths, 50, axis=0), color=AMB, lw=2.2, label="median")
ax.plot(mo, b_cash[0], color=TXT, lw=1.4, ls="--", label="deck base case")
ax.axhline(0, color=TXT, lw=1)
ax.set_xlabel("Month"); ax.set_ylabel("Cash on hand (Rs Cr)")
ax.set_xticks(range(0, 25, 3))
ax.set_title(f"Cash after the raise, {Nc:,} simulated futures (incl. fixed-cost creep): hits zero in {OUT['mc_prob_cash_negative_any_month_pct']}%", loc="left")
ax.legend(frameon=False, loc="upper right", labelcolor=MUT)
ax.grid(alpha=0.5)
save(fig, "fig10_cash_fan_montecarlo")

# FIG 11 cohort curves + revenue vs cost stack (base)
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
k = np.arange(0, 13)
for q_, c_, lab in [(0.85, TXT, "85%"), (0.76, AMB, "76% (base)"), (0.65, "#6E6C66", "65%")]:
    axs[0].plot(k, q_ ** k * 100, color=c_, lw=2.2 if q_ == 0.76 else 1.4, label=lab)
axs[0].set_xlabel("Months since sign-up"); axs[0].set_ylabel("Students still paying (%)")
axs[0].set_title("Cohort survival by monthly retention", loc="left"); axs[0].legend(frameon=False, labelcolor=MUT); axs[0].grid(alpha=0.5)
act = b_act[0]
rev = act * PRICE / LAKH
deliv = act * COST / LAKH
axs[1].plot(mo, rev, color=AMB, lw=2.2, label="revenue")
axs[1].plot(mo, deliv, color="#6E6C66", lw=1.6, label="delivery cost")
axs[1].set_xlabel("Month"); axs[1].set_ylabel("Rs lakh a month")
axs[1].set_title("Revenue against delivery cost (base case)", loc="left"); axs[1].legend(frameon=False, labelcolor=MUT); axs[1].grid(alpha=0.5)
save(fig, "fig11_cohorts_and_revenue")

OUT["cash_surface_note"] = "grid retention 55-90%, CAC 400-1300"
with open("results.json", "w") as f:
    json.dump(OUT, f, indent=2, default=str)
print(json.dumps({k: v for k, v in OUT.items() if k not in ("spearman",)}, indent=1, default=str))
