# -*- coding: utf-8 -*-
"""hospitals_raw.json (심평원 병원정보서비스, 병원급 이상 + 소아청소년과/응급의학과 플래그)
-> assets/js/data.js 생성
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

TOOLS = Path(__file__).resolve().parent
BASE = TOOLS.parent
RAW = TOOLS / "hospitals_raw.json"
OUT = BASE / "assets" / "js" / "data.js"

REGION_MAP = {
    "서울": "서울", "부산": "부산", "대구": "대구", "인천": "인천", "광주": "광주",
    "대전": "대전", "울산": "울산", "세종": "세종", "세종시": "세종", "경기": "경기", "강원": "강원",
    "충북": "충북", "충남": "충남", "전북": "전북", "전남": "전남",
    "경북": "경북", "경남": "경남", "제주": "제주",
}

REGION_ORDER = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
                "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

KIND_GROUP = {
    "상급종합": "종합병원",
    "종합병원": "종합병원",
    "병원": "병원",
    "요양병원": "요양병원",
    "정신병원": "정신병원",
    "치과병원": "치과병원",
    "한방병원": "한방병원",
}


def norm_name(name):
    return re.sub(r"\s", "", name or "")


def to_int(v):
    try:
        n = int(float(v))
        return n if n > 0 else 0
    except (TypeError, ValueError):
        return 0


def main():
    raw = json.load(open(RAW, encoding="utf-8"))
    recs = raw["records"]
    print("원본:", len(recs))

    items = {}
    skipped = []
    for r in recs:
        sido = (r.get("sido") or "").strip()
        district = (r.get("sigungu") or "").strip()
        # 데이터 기준 "전남광주통합특별시": 광주 5개 구가 시도코드명="전남"으로 잡혀 있어 분리
        if sido == "전남" and district.startswith("광주") and district != "광주":
            region = "광주"
            district = district[len("광주"):]
        else:
            region = REGION_MAP.get(sido)
        if not region:
            skipped.append((r.get("name"), r.get("sido")))
            continue
        try:
            lat = round(float(r["lat"]), 6)
            lng = round(float(r["lng"]), 6)
        except (TypeError, ValueError):
            skipped.append((r.get("name"), "좌표없음"))
            continue
        if not (33.0 < lat < 38.7 and 124.5 < lng < 131.9):
            skipped.append((r.get("name"), "좌표범위밖"))
            continue

        name = re.sub(r"\s+", " ", r["name"] or "").strip()
        if not name:
            continue
        key = (norm_name(name), region, district)
        if key in items:
            continue

        homepage = (r.get("homepage") or "").strip()
        if homepage and not homepage.startswith("http"):
            homepage = "http://" + homepage

        items[key] = {
            "name": name,
            "kind": KIND_GROUP.get(r.get("kind"), "병원"),
            "region": region,
            "district": district,
            "address": (r.get("address") or "").strip(),
            "lat": lat,
            "lng": lng,
            "phone": (r.get("phone") or "").strip(),
            "homepage": homepage,
            "doctors": to_int(r.get("totalDoctors")),
            "kidsCare": bool(r.get("kidsCare")),
            "erCare": bool(r.get("erCare")),
        }

    out = []
    ordered = sorted(items.values(),
                     key=lambda x: (REGION_ORDER.index(x["region"]), x["district"], x["name"]))
    for i, it in enumerate(ordered, 1):
        it["id"] = i
        out.append(it)

    print("정제 후:", len(out), "| 제외:", len(skipped))
    for s in skipped[:10]:
        print("  제외:", s)

    from collections import Counter
    print("지역별:", dict(Counter(x["region"] for x in out)))
    print("종류별:", dict(Counter(x["kind"] for x in out)))
    print("소아청소년과:", sum(1 for x in out if x["kidsCare"]),
          "| 응급의학과:", sum(1 for x in out if x["erCare"]))

    meta = {
        "surveyDate": date.today().isoformat(),
        "source": "건강보험심사평가원 병원정보서비스(병원급 이상, 2026.6 기준)",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("// 자동 생성 파일 — tools/build_data.py 가 생성. 직접 수정하지 마세요.\n")
        f.write("window.DATA_META = " + json.dumps(meta, ensure_ascii=False) + ";\n")
        f.write("window.HOSPITALS = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print("저장:", OUT, "|", OUT.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
