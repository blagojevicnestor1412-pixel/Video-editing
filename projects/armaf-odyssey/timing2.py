import json, sys, re, numpy as np
db = np.array(json.load(open(sys.argv[1]))["db"])  # 20 ms frames
voiced = db > -27
# (start, end, [ (chunk, syllables, keyword or None) ])
SUB = [
 (0.00, 1.30, [("U MOJOJ", 3, None), ("KOLEKCIJI IMAM", 6, "KOLEKCIJI")]),
 (1.30, 2.60, [("ČETIRI ARMAF", 4, "ČETIRI")]),
 (2.60, 4.40, [("ODYSSEY PARFEMA", 6, "ODYSSEY"), ("I HAJDE DA KAŽEM", 6, None)]),
 (4.40, 6.30, [("NEŠTO VIŠE", 4, None), ("O SVAKOM OD NJIH", 5, "SVAKOM")]),
 (6.30, 8.00, [("ARMAF ODYSSEY", 5, None), ("BAHAMAS", 3, "BAHAMAS")]),
 (8.00, 9.60, [("MIRIŠE VRLO SLIČNO", 7, "SLIČNO"), ("KAO ISSEY", 3, None)]),
 (9.60, 11.00, [("MIYAKE", 3, "MIYAKE"), ("L'EAU D'ISSEY", 4, None), ("ŠTO", 1, None)]),
 (11.00, 12.60, [("ZNAČI DA MIRIŠE", 5, None), ("NA MORE", 3, "MORE")]),
 (12.60, 15.07, [("ONDA", 2, None), ("MOJ FAVORIT", 4, "FAVORIT"), ("ZA ZIMU", 3, "ZIMU"), ("ARMAF", 2, None)]),
 (15.07, 15.68, [("ODYSSEY", 3, None)]),
 (15.68, 17.50, [("TOFFEE COFFEE", 4, "COFFEE"), ("POGLEDAJ SAMO TAJ ČEP", 7, "ČEP")]),
 (17.50, 18.55, [("OVOG PARFEMA", 5, None)]),
 (18.55, 20.40, [("KAO ŠTO MU", 4, None), ("SAMO IME KAŽE", 5, None), ("MIRIŠE NA", 4, None)]),
 (20.40, 21.82, [("TOFI", 2, "TOFI"), ("I NA KAFU", 4, "KAFU")]),
 (21.82, 25.51, [("NAJBOLJI", 3, "NAJBOLJI"), ("LETNJI PARFEM", 4, "LETNJI"), ("IZ ODYSSEY LINIJE", 7, None), ("JESTE ARMAF", 4, None)]),
 (25.51, 27.45, [("ODYSSEY", 3, None), ("LIMONI", 3, "LIMONI"), ("KOJI MIRIŠE", 4, None)]),
 (27.45, 29.48, [("KAO SLATKA", 3, None), ("LIMUNADA", 4, "LIMUNADA")]),
 (29.48, 31.50, [("UBEDLJIVO", 4, None), ("NAJDUGOTRAJNIJI", 6, "NAJDUGOTRAJNIJI")]),
 (31.50, 33.58, [("I NAJSLAĐI PARFEM", 5, "NAJSLAĐI"), ("OD OVIH SVIH", 4, None), ("JESTE", 2, None)]),
 (33.58, 35.20, [("ARMAF ODYSSEY", 5, None), ("MANDARIN", 3, "MANDARIN")]),
 (35.20, 36.90, [("SKY", 1, "SKY"), ("KOJI MIRIŠE", 4, None), ("NA KARAMELU", 5, "KARAMELU")]),
 (36.90, 39.04, [("I MENE LIČNO", 5, None), ("GUŠI", 2, "GUŠI"), ("KOLIKO JE JAK", 5, "JAK")]),
 (39.04, 40.60, [("JA SAM MARKO", 4, "MARKO"), ("OVO SU BILI", 5, None)]),
 (40.60, 42.30, [("ARMAF ODYSSEY", 5, "ODYSSEY"), ("PARFEMI", 3, None), ("A VI", 2, None)]),
 (42.30, 44.28, [("ZAPRATITE", 4, "ZAPRATITE"), ("MOJ PROFIL", 3, None), ("MARKOV MIRISNI SVET", 6, None)]),
 (44.28, 45.40, [("VIDIMO SE!", 4, None)]),
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
