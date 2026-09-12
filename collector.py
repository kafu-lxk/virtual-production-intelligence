#!/usr/bin/env python3
"""Free RSS collector for the Virtual Production Intelligence MVP.

No paid API is required. It collects public RSS/Atom feeds and Google News RSS
query feeds, filters for relevant keywords, deduplicates by URL, and writes
data/articles.json.

Run:
  python collector.py

Environment:
  MAX_ITEMS (optional, default 500)
"""
import json, re, html, os, time
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import quote
import xml.etree.ElementTree as ET

ROOT=Path(__file__).parent
CFG=ROOT/"sources.json"
DATA=ROOT/"data/articles.json"
UA="VirtualProductionIntelligence/1.0 (+https://github.com/)"

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))

def clean(s):
    s=html.unescape(s or "")
    s=re.sub(r"<[^>]+>"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def fetch(url):
    req=Request(url,headers={"User-Agent":UA,"Accept":"application/rss+xml, application/atom+xml, application/xml;q=0.9,*/*;q=0.8"})
    with urlopen(req,timeout=20) as r:
        return r.read()

def text(el, names):
    for name in names:
        x=el.find(name)
        if x is not None and x.text:
            return clean(x.text)
    return ""

def parse_feed(raw, meta):
    root=ET.fromstring(raw)
    out=[]
    # RSS
    for item in root.findall(".//item"):
        title=text(item,["title"])
        link=text(item,["link"])
        desc=text(item,["description","content:encoded"])
        date=text(item,["pubDate","dc:date"])
        out.append(make(title,link,desc,date,meta))
    # Atom
    ns={"a":"http://www.w3.org/2005/Atom"}
    for item in root.findall(".//a:entry",ns):
        title=text(item,["{http://www.w3.org/2005/Atom}title"])
        link=""
        for l in item.findall("{http://www.w3.org/2005/Atom}link"):
            if l.get("rel","alternate")=="alternate" or not link:
                link=l.get("href","")
        desc=text(item,["{http://www.w3.org/2005/Atom}summary","{http://www.w3.org/2005/Atom}content"])
        date=text(item,["{http://www.w3.org/2005/Atom}published","{http://www.w3.org/2005/Atom}updated"])
        out.append(make(title,link,desc,date,meta))
    return [x for x in out if x]

def make(title,url,desc,date,meta):
    if not title or not url: return None
    return {
      "title":title[:300],
      "date":date[:40],
      "country":meta.get("country","Global"),
      "source":meta.get("name","Unknown"),
      "categories":classify(title+" "+desc),
      "technologies":technologies(title+" "+desc),
      "summary":desc[:600],
      "url":url,
      "collected_at":datetime.now(timezone.utc).isoformat()
    }

def classify(s):
    s=s.lower()
    c=[]
    if any(x in s for x in ["virtual production","virtual set","virtual studio","バーチャルプロダクション","虚拟制片","버추얼 프로덕션","production virtuelle","virtuelle produktion","producción virtual"]): c.append("Virtual Production")
    if any(x in s for x in ["in-camera vfx","icvfx","in camera vfx","インカメラvfx","摄影机内视觉","인카메라"]): c.append("In-Camera VFX")
    if any(x in s for x in ["screen process","rear projection","front projection","スクリーンプロセス"]): c.append("Screen Process")
    if any(x in s for x in ["led volume","led wall","led volume","ledボリューム","ledウォール","led虚拟"]): c.append("LED Volume")
    if any(x in s for x in ["camera tracking","lens tracking","カメラトラッキング","tracking system"]): c.append("Camera Tracking")
    if any(x in s for x in ["real-time rendering","realtime rendering","real-time engine","リアルタイムレンダリング"]): c.append("Real-time Rendering")
    return c or ["Related"]

def technologies(s):
    s=s.lower()
    names=["Unreal Engine","Unity","Disguise","nDisplay","Brompton","ROE Visual","Mo-Sys","stYpe","Vicon","Sony","ARRI","RED","Pixotope","Zero Density","Aximmetry","NVIDIA","Notch","Blackmagic Design"]
    return [x for x in names if x.lower() in s]

def relevant(a, keywords):
    s=(a["title"]+" "+a["summary"]).lower()
    return any(k.lower() in s for k in keywords)

def google_url(query,lang):
    maps={"en":("en-US","US","en"),"ja":("ja","JP","ja"),"zh":("zh-CN","CN","zh-CN"),"ko":("ko","KR","ko"),"fr":("fr","FR","fr"),"de":("de","DE","de"),"es":("es","ES","es")}
    hl,gl,ceid=maps[lang]
    return f"https://news.google.com/rss/search?q={quote(query)}&hl={hl}&gl={gl}&ceid={ceid}"

def main():
    cfg=load(CFG); old=load(DATA) if DATA.exists() else []
    all_items=[]
    for feed in cfg.get("direct_feeds",[]):
        try:
            all_items += parse_feed(fetch(feed["url"]),feed)
            time.sleep(.4)
        except Exception as e:
            print("feed error:",feed["name"],e)
    for lang,queries in cfg["google_news_queries"].items():
        for q in queries:
            try:
                all_items += parse_feed(fetch(google_url(q,lang)),{"name":f"Google News ({lang})","country":"Global"})
                time.sleep(.4)
            except Exception as e:
                print("google feed error:",lang,q,e)

    keywords=cfg["keywords"]
    selected=[a for a in all_items if relevant(a,keywords)]
    # dedupe URL, then title
    merged={}
    for a in old+selected:
        key=a["url"].split("#")[0]
        if key not in merged: merged[key]=a
    items=list(merged.values())
    items.sort(key=lambda x:(x.get("date",""),x.get("collected_at","")),reverse=True)
    max_items=int(os.getenv("MAX_ITEMS","500"))
    DATA.write_text(json.dumps(items[:max_items],ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Collected={len(selected)} Total={len(items[:max_items])}")

if __name__=="__main__":
    main()
