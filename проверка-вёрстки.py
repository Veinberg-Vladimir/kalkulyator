#!/usr/bin/env python3
"""Проверка вёрстки калькулятора на трёх ширинах (телефон / планшет / ноутбук).

Правило из памяти feedback_verstka-merit-na-treh-shirinah: перед показом любой правки шапки
рендерить 390 / 768 / 1300 px и мерить границы цифрами, а не на глаз.

Что проверяет:
  1. низ фото = низ шапки (допуск 2 px)
  2. фото не заходит на карточку формы (низ фото <= верх карточки)
  3. текст шапки не уходит под фигуру (правый край текста <= левый край фото + 20 px)
  4. нет горизонтального скролла
  5. все картинки ориентира по жиру грузятся (мужчины и женщины)
Пишет лист проверка-вёрстки.png и маркер .last-check (хэш index.html), по которому Stop-хук
понимает, что проверка после правки была. Код выхода 1 = есть нарушение.
"""
import hashlib, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INDEX = HERE / "index.html"
MARK = HERE / ".last-check"
WIDTHS = [390, 768, 1300]

def main():
    from playwright.sync_api import sync_playwright
    from PIL import Image
    problems, shots = [], []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for w in WIDTHS:
            pg = b.new_page(viewport={"width": w, "height": 900})
            pg.goto("file://" + str(INDEX)); pg.wait_for_timeout(700)
            m = pg.evaluate("""(()=>{const r=s=>document.querySelector(s).getBoundingClientRect();
              const h=r('.hero'),i=r('.hero .ph'),t=r('.hero .txt'),c=r('#form-card');
              return {heroBottom:h.bottom,imgBottom:i.bottom,imgLeft:i.left,txtRight:t.right,cardTop:c.top,
                      scrollW:document.documentElement.scrollWidth,vw:window.innerWidth}})()""")
            if abs(m["imgBottom"] - m["heroBottom"]) > 2: problems.append(f"{w}px: низ фото {m['imgBottom']:.0f} не совпадает с низом шапки {m['heroBottom']:.0f}")
            if m["imgBottom"] > m["cardTop"] + 0.5: problems.append(f"{w}px: фото заходит на карточку (низ фото {m['imgBottom']:.0f} > верх карточки {m['cardTop']:.0f})")
            if m["txtRight"] > m["imgLeft"] + 20: problems.append(f"{w}px: текст уходит под фигуру (текст до {m['txtRight']:.0f}, фото с {m['imgLeft']:.0f})")
            if m["scrollW"] > m["vw"]: problems.append(f"{w}px: горизонтальный скролл ({m['scrollW']} > {m['vw']})")
            for g in ("m", "f"):
                pg.click(f"#gender button[data-v='{g}']");
                if pg.is_hidden("#ref"): pg.click("#ref-btn")
                pg.wait_for_timeout(400)
                ok = pg.evaluate("[...document.querySelectorAll('.band img')].every(i=>i.complete&&i.naturalWidth>0)")
                if not ok: problems.append(f"{w}px: не грузятся картинки ориентира ({'мужчины' if g=='m' else 'женщины'})")
            pg.click("#ref-btn") if not pg.is_hidden("#ref") else None
            name = HERE / f"_тест-{w}.png"; pg.screenshot(path=str(name), clip={"x": 0, "y": 0, "width": w, "height": int(m["cardTop"]) + 110}); shots.append(name)
            print(f"{w}px: шапка {m['heroBottom']:.0f}, фото {m['imgBottom']:.0f}, карточка {m['cardTop']:.0f}, текст→{m['txtRight']:.0f} | фото←{m['imgLeft']:.0f}")
            pg.close()
        b.close()
    ims = [Image.open(s) for s in shots]
    sheet = Image.new("RGB", (max(i.width for i in ims), sum(i.height for i in ims) + 20 * (len(ims) - 1)), "white")
    y = 0
    for i in ims: sheet.paste(i, (0, y)); y += i.height + 20
    sheet.save(HERE / "проверка-вёрстки.png")
    for s in shots: s.unlink(missing_ok=True)
    digest = hashlib.sha256(INDEX.read_bytes()).hexdigest()
    MARK.write_text(json.dumps({"sha256": digest, "ok": not problems, "problems": problems}, ensure_ascii=False))
    if problems:
        print("НАРУШЕНИЯ:"); [print(" -", p) for p in problems]; sys.exit(1)
    print("Вёрстка в порядке на трёх ширинах. Лист: проверка-вёрстки.png")

if __name__ == "__main__":
    main()
