"""
安筑AI — 建筑施工安全智能合规审查系统 后端API
基于 OpenAI 模型驱动多Agent长链协作
"""
import json,sqlite3,os,time,uuid,hashlib,re
from http.server import HTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from urllib.request import Request,urlopen
from urllib.error import URLError,HTTPError

DB_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)),"anzhu.db")
UPLOADS=os.path.join(os.path.dirname(os.path.abspath(__file__)),"uploads")
OPENAI_API_URL=os.environ.get("OPENAI_API_URL","https://api.openai.com/v1/responses")
OPENAI_MODEL=os.environ.get("OPENAI_MODEL","gpt-5-mini")

def _extract_response_text(data):
    texts=[]
    for item in data.get("output",[]):
        for part in item.get("content",[]):
            if part.get("type") in ("output_text","text") and part.get("text"):
                texts.append(part["text"])
    return "\n".join(texts).strip() or data.get("output_text","")

def _extract_json(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m=re.search(r"\{.*\}",text,re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

def _call_openai_review(scene,regulations):
    api_key=os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    prompt={
        "task":"你是建筑施工安全合规审查专家。请基于输入场景和候选规范生成审查结果，只返回JSON，不要输出Markdown。",
        "schema":{
            "hazards":[{"name":"string","risk_level":"red|orange|yellow|blue","description":"string","ref_code":"string"}],
            "compliance":"0-100 number",
            "risk_level":"重大|较大|一般|低",
            "report":"string"
        },
        "rules":[
            "优先使用候选规范中的ref_code，不确定时使用JGJ 59-2011。",
            "风险等级必须与hazards中最高风险一致。",
            "报告使用中文，面向施工安全员，包含规范检查、隐患、整改优先级和结论。"
        ],
        "scene":scene,
        "candidate_regulations":regulations
    }
    body=json.dumps({
        "model":OPENAI_MODEL,
        "input":json.dumps(prompt,ensure_ascii=False)
    },ensure_ascii=False).encode("utf-8")
    req=Request(
        OPENAI_API_URL,
        data=body,
        headers={
            "Authorization":f"Bearer {api_key}",
            "Content-Type":"application/json"
        },
        method="POST"
    )
    try:
        with urlopen(req,timeout=45) as resp:
            data=json.loads(resp.read().decode("utf-8"))
    except (HTTPError,URLError,TimeoutError,json.JSONDecodeError):
        return None
    parsed=_extract_json(_extract_response_text(data))
    if not isinstance(parsed,dict):
        return None
    hazards=parsed.get("hazards")
    if not isinstance(hazards,list):
        return None
    normalized=[]
    for h in hazards[:12]:
        if not isinstance(h,dict):
            continue
        risk=h.get("risk_level","yellow")
        if risk not in ("red","orange","yellow","blue"):
            risk="yellow"
        normalized.append({
            "name":str(h.get("name","安全隐患"))[:80],
            "risk_level":risk,
            "description":str(h.get("description","需进一步现场核查"))[:500],
            "ref_code":str(h.get("ref_code","JGJ 59-2011"))[:80]
        })
    if not normalized:
        return None
    try:
        compliance=max(0,min(100,float(parsed.get("compliance",70))))
    except (TypeError,ValueError):
        compliance=70
    risk_level=parsed.get("risk_level") or ("重大" if any(h["risk_level"]=="red" for h in normalized) else "较大" if any(h["risk_level"]=="orange" for h in normalized) else "一般")
    if risk_level not in ("重大","较大","一般","低"):
        risk_level="一般"
    return {
        "hazards":normalized,
        "compliance":round(compliance,1),
        "risk_level":risk_level,
        "report":str(parsed.get("report",""))[:4000],
        "provider":"openai",
        "model":OPENAI_MODEL
    }

def get_db():
    c=sqlite3.connect(DB_PATH)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    c=get_db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS reviews(
        id TEXT PRIMARY KEY,
        phase TEXT NOT NULL,
        work_type TEXT NOT NULL,
        floor TEXT DEFAULT '',
        weather TEXT DEFAULT 'normal',
        pressure TEXT DEFAULT 'normal',
        workers INTEGER DEFAULT 0,
        description TEXT DEFAULT '',
        compliance_rate REAL DEFAULT 0,
        risk_level TEXT DEFAULT '一般',
        hazard_count INTEGER DEFAULT 0,
        regulation_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        report TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS regulations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ref_code TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        level TEXT DEFAULT 'info',
        category TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS hazards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_id TEXT NOT NULL,
        name TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        description TEXT DEFAULT '',
        ref_code TEXT DEFAULT '',
        status TEXT DEFAULT 'open',
        FOREIGN KEY(review_id) REFERENCES reviews(id)
    );
    """)
    # seed regulations
    count=c.execute("SELECT COUNT(*) FROM regulations").fetchone()[0]
    if count==0:
        regs=[
            ("JGJ 120-2012 第4.2.1条","基坑支护方案审查","开挖深度超过3m的基坑，必须由具有相应资质的设计单位进行支护设计","fail","foundation"),
            ("JGJ 120-2012 第5.1.1条","基坑监测方案","基坑开挖前应制定监测方案，包括桩顶位移、周边沉降、地下水位等","fail","foundation"),
            ("JGJ 59-2011 第4.2.1条","临边防护设置","基坑周边必须设置防护栏杆和挡脚板，栏杆高度不低于1.2m","warn","foundation"),
            ("JGJ 120-2012 第6.1.1条","排水措施","基坑内应设置排水沟和集水井，保证排水通畅","fail","foundation"),
            ("JGJ 120-2012 第4.3.2条","周边建筑物保护","基坑周边2倍开挖深度范围内的建筑物应进行安全性鉴定","fail","foundation"),
            ("JGJ 46-2005 第5.1.1条","TN-S接零保护系统","必须采用TN-S接零保护系统，PE线与N线严格分开","fail","electric"),
            ("JGJ 46-2005 第6.1.1条","三级配电两级保护","总配电箱、分配电箱、开关箱应三级配电两级保护","warn","electric"),
            ("JGJ 46-2005 第7.1.1条","漏电保护器","开关箱中必须装设漏电保护器，额定漏电动作电流不大于30mA","fail","electric"),
            ("JGJ 80-2016 第3.0.1条","高处作业分级","坠落高度基准面2m及以上有可能坠落的高处作业，必须设置防护设施","fail","highrise"),
            ("JGJ 80-2016 第4.1.1条","安全网设置","高处作业下方必须设置安全网，首层网距地面不大于5m","fail","highrise"),
            ("JGJ 80-2016 第4.2.1条","临边防护栏杆","基坑周边、屋面周边、楼层周边等必须设置防护栏杆","warn","highrise"),
            ("JGJ 130-2011 第4.2.1条","脚手架搭设方案","搭设高度超过24m的脚手架应编制专项施工方案","fail","scaffold"),
            ("JGJ 130-2011 第6.4.1条","连墙件设置","脚手架连墙件布置间距应符合规范要求","warn","scaffold"),
            ("JGJ 130-2011 第7.3.1条","脚手板铺设","脚手板应铺满铺稳，不得有空隙和探头板","warn","scaffold"),
            ("GB 50720-2011 第3.2.1条","施工现场消防","施工现场应配置消防器材，设置消防通道","warn","general"),
            ("JGJ 59-2011 第3.1.1条","安全生产责任制","项目部应建立安全生产责任制，配备专职安全员","warn","general"),
            ("JGJ 59-2011 第3.2.1条","安全技术交底","施工前必须进行安全技术交底，签字确认","info","general"),
            ("JGJ 59-2011 第3.3.1条","安全教育培训","新入场工人必须进行三级安全教育培训","info","general"),
        ]
        c.executemany("INSERT INTO regulations(ref_code,title,description,level,category) VALUES(?,?,?,?,?)",regs)
        c.commit()
    c.close()

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.send_header("Content-Type","application/json; charset=utf-8")

    def _json(self,d,s=200):
        self.send_response(s)
        self._cors()
        self.end_headers()
        self.wfile.write(json.dumps(d,ensure_ascii=False).encode("utf-8"))

    def _body(self):
        l=int(self.headers.get("Content-Length",0))
        return json.loads(self.rfile.read(l)) if l else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        p=urlparse(self.path).path
        q=parse_qs(urlparse(self.path).query)
        c=get_db()
        try:
            if p=="/api/stats":
                total=c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
                total_haz=c.execute("SELECT COUNT(*) FROM hazards").fetchone()[0]
                open_haz=c.execute("SELECT COUNT(*) FROM hazards WHERE status='open'").fetchone()[0]
                avg_comp=c.execute("SELECT AVG(compliance_rate) FROM reviews").fetchone()[0] or 0
                self._json({"total_reviews":total,"total_hazards":total_haz,"open_hazards":open_haz,"avg_compliance":round(avg_comp,1)})
            elif p=="/api/regulations":
                cat=q.get("category",[None])[0]
                if cat:
                    rows=c.execute("SELECT * FROM regulations WHERE category=? ORDER BY id",(cat,)).fetchall()
                else:
                    rows=c.execute("SELECT * FROM regulations ORDER BY id").fetchall()
                self._json([dict(r) for r in rows])
            elif p=="/api/reviews":
                rows=c.execute("SELECT * FROM reviews ORDER BY created_at DESC").fetchall()
                self._json([dict(r) for r in rows])
            elif p=="/api/reviews/latest":
                r=c.execute("SELECT * FROM reviews ORDER BY created_at DESC LIMIT 1").fetchone()
                self._json(dict(r) if r else None)
            elif p.startswith("/api/review/"):
                rid=p.split("/api/review/")[1]
                r=c.execute("SELECT * FROM reviews WHERE id=?",(rid,)).fetchone()
                if r:
                    review=dict(r)
                    hazs=c.execute("SELECT * FROM hazards WHERE review_id=?",(rid,)).fetchall()
                    review["hazards"]=[dict(h) for h in hazs]
                    self._json(review)
                else:
                    self._json({"error":"Not found"},404)
            else:
                self._json({"error":"Not found"},404)
        except Exception as e:
            self._json({"error":str(e)},500)
        finally:
            c.close()

    def do_POST(self):
        p=urlparse(self.path).path
        b=self._body()
        c=get_db()
        try:
            if p=="/api/review":
                rid="rev_"+uuid.uuid4().hex[:10]
                phase=b.get("phase","")
                work_type=b.get("work_type","")
                floor=b.get("floor","")
                weather=b.get("weather","normal")
                pressure=b.get("pressure","normal")
                workers=b.get("workers",0)
                desc=b.get("description","")

                # Regulation Agent: query matching regulations
                cats=[work_type,phase,"general"]
                regs=[]
                for cat in cats:
                    rows=c.execute("SELECT * FROM regulations WHERE category=? ORDER BY id",(cat,)).fetchall()
                    regs.extend([dict(r) for r in rows])
                # dedupe
                seen=set()
                unique_regs=[]
                for r in regs:
                    if r["ref_code"] not in seen:
                        seen.add(r["ref_code"])
                        unique_regs.append(r)

                # Hazard Agent: generate baseline hazards based on rules.
                # If OPENAI_API_KEY is set, OpenAI refines hazards/report below.
                haz_data=[]
                risk_scores={"red":25,"orange":15,"yellow":5,"blue":2}
                total_deduction=0
                for reg in unique_regs:
                    if reg["level"] in ("fail","warn"):
                        haz_data.append({
                            "name":reg["title"]+"问题",
                            "risk_level":"red" if reg["level"]=="fail" else "orange",
                            "description":reg["description"],
                            "ref_code":reg["ref_code"]
                        })
                        total_deduction+=risk_scores.get("red" if reg["level"]=="fail" else "orange",10)

                if weather in ("rain","wind"):
                    haz_data.append({"name":"恶劣天气作业风险","risk_level":"red" if weather=="wind" else "orange","description":f"当前天气为{'大风' if weather=='wind' else '雨天'}，需采取安全措施","ref_code":"JGJ 59-2011 第6.1.1条"})
                    total_deduction+=15 if weather=="wind" else 10
                if pressure=="rush":
                    haz_data.append({"name":"赶工安全风险","risk_level":"orange","description":"赶工状态下易出现违章指挥、违章作业","ref_code":"JGJ 59-2011 第3.1.5条"})
                    total_deduction+=10

                compliance=max(30,100-total_deduction)
                risk_level="重大" if any(h["risk_level"]=="red" for h in haz_data) else "较大" if any(h["risk_level"]=="orange" for h in haz_data) else "一般"

                phase_names={"foundation":"基础工程","structure":"主体结构","decoration":"装饰装修","exterior":"外立面施工","roof":"屋面工程"}
                wt_names={"scaffold":"脚手架搭设","highrise":"高处作业","electric":"临时用电","lifting":"起重吊装","excavation":"基坑开挖","welding":"焊接作业"}
                scene={
                    "phase":phase,
                    "phase_name":phase_names.get(phase,phase),
                    "work_type":work_type,
                    "work_type_name":wt_names.get(work_type,work_type),
                    "floor":floor,
                    "weather":weather,
                    "pressure":pressure,
                    "workers":workers,
                    "description":desc
                }
                openai_result=_call_openai_review(scene,unique_regs)
                provider="local-rules"
                model=None
                report=""
                if openai_result:
                    haz_data=openai_result["hazards"]
                    compliance=openai_result["compliance"]
                    risk_level=openai_result["risk_level"]
                    report=openai_result["report"]
                    provider=openai_result["provider"]
                    model=openai_result["model"]

                # Save review
                c.execute("INSERT INTO reviews(id,phase,work_type,floor,weather,pressure,workers,description,compliance_rate,risk_level,hazard_count,regulation_count) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (rid,phase,work_type,floor,weather,pressure,workers,desc,compliance,risk_level,len(haz_data),len(unique_regs)))

                # Save hazards
                for h in haz_data:
                    c.execute("INSERT INTO hazards(review_id,name,risk_level,description,ref_code) VALUES(?,?,?,?,?)",
                        (rid,h["name"],h["risk_level"],h["description"],h["ref_code"]))
                c.commit()

                # Generate report if OpenAI is not configured or did not return a valid result.
                if not report:
                    report=f"建筑施工安全合规审查报告\n\n工程概况：{phase_names.get(phase,phase)} | {wt_names.get(work_type,work_type)} | {floor or '未填写'}\n天气：{weather} | 工期：{pressure} | 人数：{workers}\n\n规范检查：{len(unique_regs)}条\n安全隐患：{len(haz_data)}项\n合规率：{compliance}%\n风险等级：{risk_level}风险"

                c.execute("UPDATE reviews SET report=? WHERE id=?",(report,rid))
                c.commit()

                self._json({
                    "ok":True,
                    "id":rid,
                    "regulations":unique_regs,
                    "hazards":haz_data,
                    "compliance":compliance,
                    "risk_level":risk_level,
                    "report":report,
                    "provider":provider,
                    "model":model
                })
            else:
                self._json({"error":"Not found"},404)
        except Exception as e:
            self._json({"error":str(e)},500)
        finally:
            c.close()

    def do_DELETE(self):
        p=urlparse(self.path).path
        q=parse_qs(urlparse(self.path).query)
        c=get_db()
        try:
            if p.startswith("/api/review/"):
                rid=p.split("/api/review/")[1]
                c.execute("DELETE FROM hazards WHERE review_id=?",(rid,))
                c.execute("DELETE FROM reviews WHERE id=?",(rid,))
                c.commit()
                self._json({"ok":True})
            elif p=="/api/reviews":
                c.execute("DELETE FROM hazards")
                c.execute("DELETE FROM reviews")
                c.commit()
                self._json({"ok":True})
            else:
                self._json({"error":"Not found"},404)
        except Exception as e:
            self._json({"error":str(e)},500)
        finally:
            c.close()

    def log_message(self,*a):
        pass

if __name__=="__main__":
    init_db()
    port=int(os.environ.get("PORT",8000))
    s=HTTPServer(("0.0.0.0",port),Handler)
    print(f"安筑AI API Server running on :{port}")
    s.serve_forever()
