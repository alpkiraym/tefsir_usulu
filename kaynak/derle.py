#!/usr/bin/env python3
"""Tefsir Usulü · kaynak dosyalarından index.html üretir.

Kullanım:  python3 kaynak/derle.py
Okur:      kaynak/01.txt … 10.txt (üniteler), kaynak/sorular.txt, kaynak/sinav.txt, kaynak/sablon.html,
           kaynak/bildir.html ve kaynak/altcubuk.html (Giray Akademi ortak parçaları)
Yazar:     index.html (depo kökü)

Ünite dosyası biçimi:
  # Ünite başlığı            > giriş cümlesi
  ## Bölüm başlığı           ### Alt başlık        #### Küçük alt başlık
  - madde                    1. numaralı madde
  : Terim = tanım            (kavram kartı ve teste girer)
  ! not kutusu               !! dikkat kutusu (karıştırılan / eleştiri)
  ~ örnek kutusu             ?? soru | cevap  (soru–cevap kutusu)
  @ Arapça metin | açıklama  (ayet / Arapça blok; açıklama isteğe bağlı)
  >> adım                    (art arda gelenler numaralı adım şeridi olur)
  | a | b | c                (tablo satırı; art arda gelenler tek tablo, ilk satır başlık)
  * hızlı tekrar maddesi     (ünite sonundaki "Hızlı tekrar" kutusunda toplanır)
  **kalın**  «Arapça»
Başlığında "Müellif" ve "Eser" bulunan tablolar eser–müellif eşleştirmesine ve testlere girer.
"""
import json, re, sys
from pathlib import Path

K = Path(__file__).resolve().parent
KOK = K.parent


def hata(msg):
    sys.exit('HATA: ' + msg)


def hucre(s):
    s = s.strip()
    if s.startswith('|'):
        s = s[1:]
    return [c.strip() for c in s.split(' | ')] if ' | ' in s else [c.strip() for c in s.split('|')]


def unite_oku(yol):
    u = {'t': '', 'intro': '', 's': [], 'ht': []}
    sec = None
    for no, satir in enumerate(yol.read_text(encoding='utf-8').splitlines(), 1):
        s = satir.rstrip()
        if not s.strip():
            continue
        if s.startswith('## '):
            sec = {'h': s[3:].strip(), 'b': []}
            u['s'].append(sec)
            continue
        if s.startswith('# '):
            u['t'] = s[2:].strip()
            continue
        if s.startswith('> '):
            u['intro'] = s[2:].strip()
            continue
        if sec is None:
            hata(f'{yol.name}:{no} bölüm başlığından önce içerik')
        b = sec['b']
        son = b[-1] if b else None
        if s.startswith('#### '):
            b.append({'k': 'h5', 'x': s[5:].strip()})
        elif s.startswith('### '):
            b.append({'k': 'h', 'x': s[4:].strip()})
        elif s.startswith('| ') or s == '|' or s.startswith('| |'):
            satir_h = [c.strip() for c in s.split('|')[1:]]
            if son and son['k'] == 'tbl':
                son['r'].append(satir_h)
            else:
                b.append({'k': 'tbl', 'r': [satir_h]})
        elif s.startswith('>> '):
            if son and son['k'] == 'steps':
                son['x'].append(s[3:].strip())
            else:
                b.append({'k': 'steps', 'x': [s[3:].strip()]})
        elif s.startswith('* '):
            u['ht'].append({'s': len(u['s']) - 1, 'x': s[2:].strip()})
        elif s.startswith('!! '):
            b.append({'k': 'dikkat', 'x': s[3:].strip()})
        elif s.startswith('! '):
            b.append({'k': 'not', 'x': s[2:].strip()})
        elif s.startswith('~ '):
            b.append({'k': 'ornek', 'x': s[2:].strip()})
        elif s.startswith('?? '):
            if ' | ' not in s:
                hata(f'{yol.name}:{no} soru–cevap satırında " | " yok')
            q, a = s[3:].split(' | ', 1)
            b.append({'k': 'sc', 'q': q.strip(), 'x': a.strip()})
        elif s.startswith('@ '):
            a, m = (s[2:].split(' | ', 1) + [''])[:2]
            b.append({'k': 'ar', 'a': a.strip(), 'x': m.strip()})
        elif s.startswith('- '):
            b.append({'k': 'li', 'x': s[2:].strip()})
        elif s.startswith(': '):
            if ' = ' not in s:
                hata(f'{yol.name}:{no} tanım satırında " = " yok')
            t, d = s[2:].split(' = ', 1)
            b.append({'k': 'd', 't': t.strip(), 'x': d.strip()})
        elif re.match(r'^\d+\.\s', s):
            n, x = s.split('.', 1)
            b.append({'k': 'n', 'n': int(n), 'x': x.strip()})
        else:
            hata(f'{yol.name}:{no} tanınmayan satır: {s[:40]}')
    if not u['t'] or not u['s']:
        hata(f'{yol.name} başlık veya bölüm eksik')
    for sec in u['s']:
        for b in sec['b']:
            if b['k'] == 'tbl':
                n = len(b['r'][0])
                for r in b['r']:
                    if len(r) != n:
                        hata(f'{yol.name}: "{sec["h"]}" tablosunda sütun sayısı tutmuyor: {r[:2]}')
    return u


def eserler(uniteler):
    """Başlığında Müellif ve Eser olan tablolardan eser–müellif listesi."""
    out = []
    for ui, u in enumerate(uniteler):
        for si, sec in enumerate(u['s']):
            for b in sec['b']:
                if b['k'] != 'tbl':
                    continue
                bas = [re.sub(r'\*', '', c) for c in b['r'][0]]
                if 'Müellif' not in bas or 'Eser' not in bas:
                    continue
                im, ie = bas.index('Müellif'), bas.index('Eser')
                iv = bas.index('Vefat') if 'Vefat' in bas else None
                for r in b['r'][1:]:
                    e = re.sub(r'\s*\(.*?\)\s*', ' ', r[ie]).strip()
                    out.append({'u': ui, 's': si, 'e': e, 'm': r[im].replace('**', ''), 'not': r[iv] if iv is not None else ''})
    return out


def sorular_oku(yol, adet):
    out, q = [], None
    for no, s in enumerate(yol.read_text(encoding='utf-8').splitlines(), 1):
        if not s.strip() or s.startswith('#'):
            continue
        if s.startswith('? '):
            if q:
                out.append(q)
            u, metin = s[2:].split('|', 1)
            q = {'u': int(u) - 1, 'q': metin.strip(), 'a': [], 'x': ''}
        elif s.startswith('+ '):
            q['a'].insert(0, s[2:].strip())
        elif s.startswith('- '):
            q['a'].append(s[2:].strip())
        elif s.startswith('= '):
            q['x'] = s[2:].strip()
        else:
            hata(f'{yol.name}:{no} tanınmayan satır')
    if q:
        out.append(q)
    for i, q in enumerate(out):
        if len(q['a']) != 4 or len(set(q['a'])) != 4:
            hata(f'soru {i + 1}: 4 farklı şık olmalı ({q["q"][:40]})')
        if not (0 <= q['u'] < adet):
            hata(f'soru {i + 1}: ünite numarası geçersiz')
        if not q['x']:
            hata(f'soru {i + 1}: açıklama yok')
    return out


def sinav_oku(yol, uniteler):
    gruplar, q = [], None
    for no, s in enumerate(yol.read_text(encoding='utf-8').splitlines(), 1):
        if not s.strip() or s.startswith('#'):
            continue
        if s.startswith('[') and s.endswith(']'):
            gruplar.append({'t': s[1:-1].strip(), 'q': []})
            continue
        if not gruplar:
            hata(f'{yol.name}:{no} önce [sınav başlığı] yazılmalı')
        if s.startswith('? '):
            q = {'q': s[2:].strip(), 'r': [], 'x': [], 'n': ''}
            gruplar[-1]['q'].append(q)
        elif s.startswith('> '):
            u, h = s[2:].split(':', 1)
            ui = int(u) - 1
            basliklar = [x['h'] for x in uniteler[ui]['s']]
            if h.strip() not in basliklar:
                hata(f'{yol.name}:{no} "{h.strip()}" bölümü {u}. ünitede yok')
            q['r'].append([ui, basliklar.index(h.strip())])
        elif s.startswith('= '):
            q['x'].append(s[2:].strip())
        elif s.startswith('! '):
            q['n'] = s[2:].strip()
        else:
            hata(f'{yol.name}:{no} tanınmayan satır')
    for g in gruplar:
        for q in g['q']:
            if not q['x']:
                hata(f'sınav sorusu cevapsız: {q["q"][:40]}')
    return gruplar


def main():
    dosyalar = sorted(K.glob('[0-9][0-9].txt'))
    uniteler = [unite_oku(p) for p in dosyalar]
    sorular = sorular_oku(K / 'sorular.txt', len(uniteler))
    sinav = sinav_oku(K / 'sinav.txt', uniteler)
    eser = eserler(uniteler)
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    veri = (f'const UNITELER = {j(uniteler)};\nconst SORULAR = {j(sorular)};\n'
            f'const SINAV = {j(sinav)};\nconst ESER_T = {j(eser)};')
    sablon = (K / 'sablon.html').read_text(encoding='utf-8')
    for etiket in ('/*VERI*/', '<!--BILDIR-->', '<!--ALTCUBUK-->'):
        if etiket not in sablon:
            hata(f'sablon.html içinde {etiket} yok')
    sablon = sablon.replace('<!--BILDIR-->', (K / 'bildir.html').read_text(encoding='utf-8'))
    sablon = sablon.replace('<!--ALTCUBUK-->', (K / 'altcubuk.html').read_text(encoding='utf-8'))  # ortak alt çubuk (Giray Akademi)
    (KOK / 'index.html').write_text(sablon.replace('/*VERI*/', veri), encoding='utf-8')
    tanim = sum(1 for u in uniteler for s in u['s'] for b in s['b'] if b['k'] == 'd')
    tablo = sum(1 for u in uniteler for s in u['s'] for b in s['b'] if b['k'] == 'tbl')
    ht = sum(len(u['ht']) for u in uniteler)
    print(f'{len(uniteler)} ünite, {sum(len(u["s"]) for u in uniteler)} bölüm, {tanim} tanım, {tablo} tablo, '
          f'{ht} hızlı tekrar maddesi, {len(eser)} eser, {len(sorular)} el ile soru, '
          f'{sum(len(g["q"]) for g in sinav)} sınav sorusu → index.html')


if __name__ == '__main__':
    main()
