#!/usr/bin/env python3
"""Compare fullchip benchmark output folders or ZIPs; stdlib only."""
import argparse
import csv
import html
import io
import json
import math
from pathlib import Path
import statistics
import zipfile

STAGES = ["cpu_single", "cpu_multi", "gpu_3d", "cpu_gpu", "cpu_gpu_ram"]
LABELS = {"cpu_single":"CPU — 1 núcleo", "cpu_multi":"CPU — 4 núcleos",
          "gpu_3d":"GPU 3D", "cpu_gpu":"CPU + GPU", "cpu_gpu_ram":"CPU + GPU + memória"}
COLORS = ["#2878da", "#d27837", "#3a9f83", "#ad5bd2", "#ce5374", "#687898"]


def read_case(path):
    path = Path(path)
    if path.is_dir():
        meta = json.loads((path/"resumo.json").read_text())
        def data_for(name):
            with (path/name).open(newline="") as f:
                return list(csv.DictReader(f))
    elif path.suffix.lower() == ".zip":
        z = zipfile.ZipFile(path)
        roots = [s for s in z.namelist() if s.endswith("resumo.json")]
        if len(roots) != 1:
            raise ValueError(f"{path}: ZIP deve conter apenas um resumo.json")
        member = roots[0]
        prefix = member[:-len("resumo.json")]
        meta = json.loads(z.read(member).decode())
        def data_for(name):
            return list(csv.DictReader(io.StringIO(z.read(prefix+name).decode())))
    else:
        raise ValueError("Esperado pasta do benchmark ou ZIP contendo resumo.json")
    rows = []
    for stage in meta.get("stages",[]):
        if stage.get("csv"):
            rows.extend(data_for(stage["csv"]))
    return meta, rows


def series_points(rows, stage, freq):
    sub = [r for r in rows if r["stage"] == stage and int(r["freq_target_mhz"]) == freq and r["temperature_c"]]
    order = {"repouso":0,"stress":1,"resfriamento":2}
    durations = [max((float(r["elapsed_s"]) for r in sub if r["phase"] == phase),default=0) for phase in order]
    offsets = [0, durations[0]+1, durations[0]+durations[1]+2]
    pts = [(offsets[order[r["phase"]]] + float(r["elapsed_s"]), float(r["temperature_c"]),r["phase"]) for r in sub]
    return pts, [offsets[1], offsets[2]]


def graph(data, stage):
    W,H = 1050,405
    margin = (68,24,28,55)
    left,top,right,bottom=margin
    inside_w,inside_h=W-left-right,H-top-bottom
    lines=[]; colors=[]; splitpoints=[]
    for idx,(meta,rows) in enumerate(data):
        for freq in meta.get("freqs_mhz",[]):
            pts,splits=series_points(rows,stage,freq)
            if not pts:
                continue
            lines.append((f"{meta['label']} · {freq} MHz",pts,COLORS[(idx*2+list(meta['freqs_mhz']).index(freq)) % len(COLORS)]))
            splitpoints=splits
    if not lines:
        return "<p>Dados térmicos indisponíveis para esta etapa.</p>"
    xmin,xmax=0,max(5,max(max(p[0] for p in pts) for _,pts,_ in lines))
    tvals=[p[1] for _,pts,_ in lines for p in pts]
    ymin=5*math.floor((min(tvals)-2)/5)
    ymax=5*math.ceil((max(tvals)+2)/5)
    if ymax<=ymin:ymax=ymin+5
    x=lambda v:left+inside_w*(v-xmin)/(xmax-xmin)
    y=lambda v:top+inside_h*(ymax-v)/(ymax-ymin)
    chunks=[f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {W} {H}" role="img" aria-label="Temperatura por segundo na etapa {stage}">',
            f'<rect x="0" y="0" width="{W}" height="{H}" rx="12" fill="#ffffff"/>']
    for temp in range(int(ymin),int(ymax)+1,5):
        yy=y(temp)
        chunks.append(f'<path d="M {left} {yy:.1f} H {W-right}" stroke="#e8edf5"/>')
        chunks.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end" fill="#52657c" font-size="12">{temp}°</text>')
    for split in splitpoints:
        xx=x(split)
        chunks.append(f'<path d="M {xx:.1f} {top} V {H-bottom}" stroke="#cbd6e2" stroke-dasharray="5 5"/>')
    for label,pts,color in lines:
        path=" ".join(("M" if i==0 else "L")+f"{x(px):.2f},{y(py):.2f}" for i,(px,py,_) in enumerate(pts))
        chunks.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.5" stroke-linejoin="round"/>')
    for tick in range(0,int(xmax)+1,max(30,int(xmax)//8 or 1)):
        chunks.append(f'<text x="{x(tick):.1f}" y="{H-bottom+20}" fill="#52657c" font-size="12" text-anchor="middle">{tick}s</text>')
    chunks.append(f'<text x="{W/2}" y="{H-7}" text-anchor="middle" font-size="12" fill="#52657c">Tempo dentro da etapa (s)</text>')
    for idx,(label,_,color) in enumerate(lines):
        lx=left+idx*min(250,inside_w/max(len(lines),1))
        chunks.append(f'<circle cx="{lx}" cy="12" r="5" fill="{color}"/>')
        chunks.append(f'<text x="{lx+10}" y="16" font-size="12" fill="#18304c">{html.escape(label)}</text>')
    chunks.append('</svg>')
    return ''.join(chunks)


def main():
    p=argparse.ArgumentParser(description="Comparacao grafica Raspberry Pi 4 full chip")
    p.add_argument("resultados",nargs="+",help="pastas ou arquivos ZIP dos ensaios")
    p.add_argument("--out",default="comparativo_fullchip")
    a=p.parse_args()
    data=[read_case(r) for r in a.resultados]
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    stylesheet="""body{font:15px system-ui, sans-serif;background:#f4f6fa;color:#1b324b;margin:0}
    main{max-width:1120px;margin:auto;padding:36px}h1{margin:0}h2{margin-top:40px}
    .muted{color:#60748d}.card{background:white;border:1px solid #dce5ee;padding:20px;border-radius:16px;margin:20px 0}
    table{border-collapse:collapse;width:100%;font-size:13px;background:white}th,td{border-bottom:1px solid #e5eaf2;text-align:left;padding:10px}
    th{background:#eef3f9} .scroll{overflow-x:auto} .tag{display:inline-block;background:#e7f2fa;padding:6px 10px;border-radius:8px;margin:3px}
    """
    body=["<html><head><meta charset='utf-8'><title>Comparativo FullChip RPi4</title>",
          f"<style>{stylesheet}</style></head><body><main>",
          "<h1>Comparativo FullChip · Raspberry Pi 4</h1>",
          "<p class='muted'>CPU 1 núcleo, CPU 4 núcleos, GPU 3D, CPU+GPU e CPU+GPU+RAM · séries de 1 segundo.</p>"]
    for meta,rows in data:
        body.append(f"<span class='tag'>{html.escape(meta['label'])} · {', '.join(map(str,meta['freqs_mhz']))} MHz · GPU: {html.escape(str(meta.get('gpu_validated')))}</span>")
    body.append("<section class='card'><h2>Resumo por etapa</h2><div class='scroll'><table><tr><th>Dispositivo</th><th>Frequência</th><th>Etapa</th><th>Estado</th><th>Máx. °C</th><th>Média °C (carga)</th><th>CPU MHz</th><th>Throttling ativo</th></tr>")
    for meta,rows in data:
        for item in meta.get("stages",[]):
            x=item.get("stress",{})
            body.append("<tr>"+"".join(f"<td>{html.escape(str(v))}</td>" for v in [meta["label"], item["freq_target_mhz"],LABELS.get(item["stage"],item["stage"]),item["status"],x.get("max_c","—"),x.get("mean_c","—"),x.get("mean_arm_mhz","—"),x.get("throttling_samples","—")])+"</tr>")
    body.append("</table></div></section>")
    for stage in STAGES:
        body.append(f"<section class='card'><h2>{LABELS[stage]}</h2>{graph(data,stage)}</section>")
    body.append("<p class='muted'>GPU disponível é validada pelo renderer V3D, mas clock V3D não comprova uso de 100%. A temperatura, sem calibração de potência, não fornece watts térmicos absolutos. Eventos históricos de throttling são diferenciados dos ativos.</p></main></body></html>")
    report=out/"comparativo.html"
    report.write_text("".join(body),encoding="utf-8")
    with (out/"amostras_unificadas.csv").open("w",newline="") as f:
        writer=None
        for meta, rows in data:
            for row in rows:
                if writer is None:
                    writer=csv.DictWriter(f,fieldnames=list(row.keys()))
                    writer.writeheader()
                writer.writerow(row)
    (out/"resumos_originais.json").write_text(json.dumps([meta for meta,_ in data],ensure_ascii=False,indent=2))
    print("Gerado:",report,"\nCSV:",out/"amostras_unificadas.csv")

if __name__=='__main__':
    main()
