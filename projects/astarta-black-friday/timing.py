import json, sys, re, numpy as np
db = np.array(json.load(open(sys.argv[1]))["db"])  # 20 ms frames
voiced = db > -27
# (start, end, [ (chunk, syllables, keyword or None) ])
SUB = [
 (0.00, 1.25, [("OD DANAS", 3, "DANAS"), ("23.11.", 9, "23.11.")]),
 (1.25, 3.73, [("PA SVE DO", 3, None), ("29.11.", 10, "29.11.")]),
 (3.73, 5.00, [("ASTARTA PARFUMS", 5, "ASTARTA"), ("SU MI PRIPREMILI", 6, None)]),
 (5.00, 6.49, [("NEŠTO POSEBNO", 5, "POSEBNO")]),
 (6.49, 7.80, [("U SVAKI", 3, None)]),
 (7.80, 10.92, [("KUPLJENI PARFEM", 5, "PARFEM"), ("NA NJIHOVOM SAJTU", 6, "SAJTU"), ("DOBIJATE", 4, None), ("BESPLATNO", 3, "BESPLATNO")]),
 (10.92, 13.92, [("MIKROPARFEM", 4, None), ("PREMIUM DEKANT", 5, None), ("GURMANSKI SET", 4, None)]),
 (13.92, 15.85, [("TO FUNKCIONIŠE", 6, None), ("NA SLEDEĆI NAČIN", 6, "NAČIN")]),
 (15.85, 17.40, [("NA PRIMER", 4, None), ("VAŠ OMILJENI PARFEM", 7, "OMILJENI")]),
 (17.40, 19.17, [("JE ASTARTA PARFUMS", 6, "ASTARTA"), ("LIPA", 2, "LIPA")]),
 (19.17, 21.78, [("I AKO PORUČITE", 6, "PORUČITE"), ("OVAJ PARFEM", 4, None), ("NA NJIHOVOM SAJTU", 6, "SAJTU")]),
 (21.78, 23.45, [("U SVAKOJ PORUDŽBINI", 7, "PORUDŽBINI"), ("DOBIJATE", 4, None)]),
 (23.45, 25.11, [("BESPLATAN", 3, "BESPLATAN"), ("GURMANSKI SET", 4, "SET")]),
 (25.11, 27.00, [("ZA SVAKI KUPLJENI", 6, None), ("ASTARTA PARFEM", 5, "ASTARTA")]),
 (27.00, 29.01, [("JEDAN", 2, None), ("BESPLATAN", 3, "BESPLATAN"), ("GURMANSKI SET", 4, "SET")]),
 (29.01, 30.20, [("JA SAM MARKO", 4, "MARKO")]),
 (30.20, 32.43, [("A VI ZAPRATITE", 5, "ZAPRATITE"), ("MOJ PROFIL", 3, None), ("MARKOV MIRISNI SVET", 6, None)]),
 (32.43, 33.00, [("VIDIMO SE!", 4, None)]),
]
out = []
for s, e, ch in SUB:
    fr = [i for i in range(int(s / .02), int(e / .02)) if i < len(voiced) and voiced[i]]
    # voiced timeline; allocate syllables proportionally along voiced frames
    tot = sum(c[1] for c in ch); acc = 0
    for txt, syl, kw in ch:
        k = int(len(fr) * acc / tot)
        t0 = fr[min(k, len(fr) - 1)] * .02
        out.append((round(max(s, t0 - 0.04), 2), txt, kw))
        acc += syl
for o in out: print(o)
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
