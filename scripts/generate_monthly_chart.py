

import os
import sys
import calendar
from collections import OrderedDict
from datetime import datetime, timedelta

import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GH_USERNAME = os.environ.get("GH_USERNAME")

if not GITHUB_TOKEN or not GH_USERNAME:
    sys.exit("Missing GITHUB_TOKEN or GH_USERNAME environment variables.")

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_contributions(login: str, from_dt: datetime, to_dt: datetime):
    headers = {"Authorization": f"bearer {GITHUB_TOKEN}"}
    variables = {
        "login": login,
        "from": from_dt.strftime("%Y-%m-%dT00:00:00Z"),
        "to": to_dt.strftime("%Y-%m-%dT23:59:59Z"),
    }
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": variables},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

    monthly = OrderedDict()
    for m in range(1, 13):
        monthly[calendar.month_abbr[m]] = 0

    for week in weeks:
        for day in week["contributionDays"]:
            date = datetime.strptime(day["date"], "%Y-%m-%d")
            month_name = calendar.month_abbr[date.month]
            monthly[month_name] += day["contributionCount"]

    return monthly


def render_chart(monthly: dict, out_path: str):
    months = list(monthly.keys())
    counts = list(monthly.values())

    WHITE = "#ffffff"

    fig, ax = plt.subplots(figsize=(10, 4), dpi=150)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    ax.plot(
        months,
        counts,
        color=WHITE,
        marker="o",
        markersize=5,
        linewidth=2,
    )
    ax.fill_between(months, counts, color=WHITE, alpha=0.08)

    ax.set_title("Monthly Contribution Activity", fontsize=14, weight="bold", color=WHITE)
    ax.set_ylabel("Contributions", color=WHITE)

    for spine in ax.spines.values():
        spine.set_color(WHITE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.tick_params(colors=WHITE)
    ax.xaxis.label.set_color(WHITE)
    ax.yaxis.label.set_color(WHITE)
    ax.grid(axis="y", color=WHITE, alpha=0.15, linewidth=0.5)

    for x, count in zip(months, counts):
        ax.annotate(
            str(count),
            xy=(x, count),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=WHITE,
        )

    fig.tight_layout()
    fig.savefig(out_path, transparent=True)
    print(f"Saved chart to {out_path}")


if __name__ == "__main__":
    to_dt = datetime.utcnow()
    from_dt = to_dt - timedelta(days=365)
    monthly = fetch_contributions(GH_USERNAME, from_dt, to_dt)
    render_chart(monthly, "monthly-activity.png")
