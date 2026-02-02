import asyncio
from typing import Any, Iterable, Tuple

import discord
import requests
from discord import app_commands, Interaction
from discord.ext import commands

from cogs import is_member_or_above_appcmd
from utils.overwatch_normalize import (
    build_referer,
    normalize_map,
    normalize_role,
    normalize_rq,
    normalize_tier,
)


API_URL = "https://overwatch.blizzard.com/ko-kr/rates/data/"
BASE_PARAMS = {
    "input": "PC",
    "region": "Asia",
}
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://overwatch.blizzard.com",
    "X-Requested-With": "XMLHttpRequest",
}


def _extract_items(data: Any) -> Iterable[dict]:
    if isinstance(data, dict):
        if isinstance(data.get("rates"), list):
            return data["rates"]
        if isinstance(data.get("data"), list):
            return data["data"]
        if isinstance(data.get("heroes"), list):
            return data["heroes"]
    if isinstance(data, list):
        return data
    return []


def _parse_win_rate(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip().replace("%", "")
        try:
            num = float(v)
        except ValueError:
            return None
    elif isinstance(value, (int, float)):
        num = float(value)
    else:
        return None

    if 0 <= num <= 1:
        return num * 100
    return num


def _extract_stats(data: Any) -> list[Tuple[str, float]]:
    results: list[Tuple[str, float]] = []
    for item in _extract_items(data):
        if not isinstance(item, dict):
            continue
        hero_val = item.get("hero") or item.get("heroName") or item.get("name") or item.get("hero_name")
        if isinstance(hero_val, dict):
            name = hero_val.get("name") or hero_val.get("key") or hero_val.get("value")
        else:
            name = hero_val
        win_rate = (
            item.get("winRate")
            or item.get("win_rate")
            or item.get("winrate")
            or item.get("winRatePct")
        )
        if win_rate is None and isinstance(item.get("cells"), dict):
            win_rate = item["cells"].get("winrate") or item["cells"].get("winRate")
        if isinstance(win_rate, dict):
            win_rate = win_rate.get("value") or win_rate.get("percent") or win_rate.get("pct")
        win_rate = _parse_win_rate(win_rate)
        if name and win_rate is not None:
            results.append((str(name), float(win_rate)))
    return results


def _format_top5(stats: list[Tuple[str, float]]) -> list[str]:
    stats_sorted = sorted(stats, key=lambda x: x[1], reverse=True)[:5]
    return [f"{idx}. **{name}** — {rate:.2f}%" for idx, (name, rate) in enumerate(stats_sorted, start=1)]


def _normalize_map_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("slug") or value.get("key") or value.get("name") or value.get("value")
    if not isinstance(value, str):
        return None
    mapped = normalize_map(value)
    if isinstance(mapped, str):
        value = mapped
    return value.strip().lower().replace(" ", "-").replace("_", "-")


def _filter_by_map(items: Iterable[dict], map_value: str) -> list[dict]:
    if not map_value:
        return list(items)
    map_norm = _normalize_map_value(map_value)
    if not map_norm or map_norm == "all-maps":
        return list(items)
    filtered = []
    for item in items:
        if not isinstance(item, dict):
            continue
        candidate = (
            item.get("map")
            or item.get("mapName")
            or item.get("map_name")
            or item.get("mapId")
            or item.get("mapSlug")
            or item.get("mapKey")
        )
        candidate_norm = _normalize_map_value(candidate)
        if candidate_norm and candidate_norm == map_norm:
            filtered.append(item)
    return filtered or list(items)


def _filter_by_role(items: Iterable[dict], role: str) -> list[dict]:
    role_norm = normalize_role(role)
    if role_norm == "All":
        return list(items)
    role_key = role_norm.upper()
    filtered = []
    for item in items:
        if not isinstance(item, dict):
            continue
        hero = item.get("hero")
        if not isinstance(hero, dict):
            hero = {}
        hero_role = hero.get("role") or item.get("role") or item.get("heroRole")
        if isinstance(hero_role, str) and hero_role.upper() == role_key:
            filtered.append(item)
    return filtered


def _filter_by_tier(items: Iterable[dict], tier: str | None) -> list[dict]:
    if not tier:
        return list(items)
    tier_norm = normalize_tier(tier)
    if not isinstance(tier_norm, str) or tier_norm.lower() == "all":
        return list(items)
    tier_key = tier_norm.lower()
    filtered = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_tier = item.get("tier") or item.get("rank") or item.get("tierName")
        if isinstance(item_tier, dict):
            item_tier = item_tier.get("name") or item_tier.get("value") or item_tier.get("key")
        if isinstance(item_tier, str) and item_tier.lower() == tier_key:
            filtered.append(item)
    return filtered or list(items)


def _filter_by_rq(items: Iterable[dict], rq_value: str | int | None) -> list[dict]:
    if rq_value is None:
        return list(items)
    rq_key = str(rq_value)
    filtered = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_rq = item.get("rq") or item.get("mode") or item.get("queue") or item.get("queueId")
        if isinstance(item_rq, int):
            item_rq = str(item_rq)
        if isinstance(item_rq, str) and item_rq == rq_key:
            filtered.append(item)
    return filtered or list(items)
async def fetch_rates(params: dict, log_id: str):
    def _sanitize_params(p: dict) -> dict:
        key_map = {
            "맵": "map",
            "역할": "role",
            "모드": "rq",
            "모드(빠대, 경쟁)": "rq",
            "티어": "tier",
        }
        fixed = {}
        for k, v in p.items():
            fixed[key_map.get(k, k)] = v
        return fixed

    def _request():
        safe_params = _sanitize_params(params)
        headers = {**HEADERS, "Referer": build_referer(safe_params)}
        r = requests.get(API_URL, headers=headers, params=safe_params, timeout=20)
        r.raise_for_status()
        return r.json()

    return await asyncio.to_thread(_request)


class OverwatchRates(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="승률-보기", description="오버워치 영웅 승률 Top 5를 확인합니다.")
    @app_commands.rename(map="맵", role="역할", rq="모드", tier="티어")
    @app_commands.describe(
        map="맵 이름 (예: 왕의 길/지브롤터/전체)",
        role="역할 (탱커/딜러/힐러/전체)",
        rq="모드 (빠른 대전/경쟁전)",
        tier="티어 (브론즈/실버/골드/플레/다이아/마스터/그마/전체)",
    )
    @is_member_or_above_appcmd()
    async def show_rates(
        self,
        interaction: Interaction,
        map: str,
        role: str,
        rq: str,
        tier: str | None = None,
    ):
        await interaction.response.defer(thinking=True)

        rq_parsed = normalize_rq(rq)
        if rq_parsed is None:
            await interaction.followup.send("❌ 빠대/경쟁전 입력만 가능합니다.", ephemeral=True)
            return
        if rq_parsed != 0 and not tier:
            tier = "전체"

        params = {
            **BASE_PARAMS,
            "map": normalize_map(map),
            "role": normalize_role(role),
            "rq": str(rq_parsed),
            "tier": normalize_tier(tier) if rq_parsed != 0 else "All",
        }
        try:
            data = await fetch_rates(params, log_id="")
        except Exception as e:
            await interaction.followup.send("❌ 데이터를 가져오는 중 오류가 발생했습니다.", ephemeral=True)
            return

        items = list(_extract_items(data))

        try:
            map_filtered = _filter_by_map(items, params["map"])
            rq_filtered = _filter_by_rq(map_filtered, params["rq"])
            tier_filtered = _filter_by_tier(rq_filtered, params["tier"])
            role_filtered = _filter_by_role(tier_filtered, params["role"])
            stats = _extract_stats({"rates": role_filtered})
        except Exception as e:
            await interaction.followup.send("❌ 처리 중 오류가 발생했습니다.", ephemeral=True)
            return
        if not stats:
            try:
                await interaction.followup.send("❌ 승률 데이터를 찾을 수 없습니다.", ephemeral=True)
            except Exception:
                pass
            return

        top5_lines = _format_top5(stats)
        map_label = "전체" if (not map or str(map).lower() == "all") else map
        tier_label = "전체" if (not tier or str(tier).lower() == "all") else tier
        role_label = "전체" if (not role or str(role).lower() == "all") else role
        title = f"🎯 `맵: {map_label}`, `티어: {tier_label}`, `포지션: {role_label}` 승률 Top 5 영웅"
        embed = discord.Embed(title=title, color=discord.Color.blue())

        embed.add_field(name="TOP 5", value="\n".join(top5_lines), inline=False)
        embed.set_footer(text="데이터 출처: Blizzard Overwatch Rates")
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(OverwatchRates(bot))
