import sys, re, xml.etree.ElementTree as ET

def attrs(e, skip=()):
    return " ".join(f"{k}={v}" for k, v in e.attrib.items() if k not in skip)

def compact_events(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    def dedup(m):
        seen = {}
        def r(a):
            k = a.group(1); seen[k] = seen.get(k, 0) + 1
            return f" {k}{seen[k] if seen[k] > 1 else ''}="
        return re.sub(r" ([a-zA-Z_0-9]+)=", r, m.group(0))
    raw = re.sub(r"<[a-z_]+ [^>]*>", dedup, raw)
    root = ET.fromstring(raw)
    out = []
    for v in root.iter("variable"):
        t = v.get("text") or ""
        out.append(f"VAR {v.get('name')}={v.get('value')}" + (f" vis '{t}'" if v.get("visible") == "1" else ""))
    for ev in root.iter("event"):
        head = f"E{ev.get('id')}"
        if ev.get("name"): head += f" [{ev.get('name')}]"
        rep = {k: ev.get(k) for k in ("repeat_days_min", "repeat_days_max", "max_number_of_repeats") if ev.get(k)}
        if rep:
            head += f" rep{rep.get('repeat_days_min')}-{rep.get('repeat_days_max')}d x{rep.get('max_number_of_repeats', 'inf')}"
        conds = []
        c = ev.find("conditions")
        if c is not None:
            for x in c:
                if x.tag == "group" or len(x):
                    conds.append("OR(" + " | ".join(f"{y.tag} {attrs(y)}" for y in x) + ")")
                else:
                    conds.append(f"{x.tag} {attrs(x)}")
        acts = []
        a = ev.find("actions")
        if a is not None:
            for x in a:
                acts.append(f"{x.tag} {attrs(x)}")
        out.append(f"{head} IF {' & '.join(conds) or 'always'} => {' ; '.join(acts)}")
    return out

def compact_messages(path):
    root = ET.parse(path).getroot()
    out = []
    for m in root.iter("message"):
        def t(tag):
            e = m.find(tag)
            return re.sub(r"\s+", " ", (e.text or "").strip()) if e is not None and e.text else ""
        text = t("text")
        text = re.sub(r"@G\[[^\]]*\]|@[GLPHI*]|@\d+|@", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        out.append(f"MSG {m.get('uid')} | {t('title')} | {t('subtitle')} | {text}")
    return out

d = sys.argv[1]
print("\n".join(compact_events(d + "/events.xml")))
print("\n".join(compact_messages(d + "/messages.xml")))
