# G4.7 — dağıtılan T\* hangi fit'ten geldi

> **Panel G4.7.** Tablo B.2 başlığı ile §3.3 çelişiyor. Cevap koşuların kendi argümanlarından okundu, metinden değil.

**CEVAP: Dağıtılan T*=1.3406 **yarı fold (yarı-A'da fit)** fitinden geldi (1.340569 → 1.3406). Tam fold 1.349393 verirdi ve hiçbir koşu onu kullanmadı.**

## Diskteki her T değeri, kendi koşu argümanından

| veri kümesi | T | koşu | ne | kaynak | eşleşme |
|---|---|---|---|---|---|
| RAFDB | 0.7311 | 4 | miskalibrasyon enjeksiyonu | A2 / B-010 kill-switch (build_runs_ledger.MISCAL_T) | 0.00e+00 |
| RAFDB | 0.85 | 12 | yuvarlak grid noktası | — | — |
| RAFDB | 0.95 | 3 | yuvarlak grid noktası | — | — |
| RAFDB | 1.1 | 3 | yuvarlak grid noktası | — | — |
| RAFDB | 1.3406 | 24 | FİT EDİLMİŞ T* | yarı fold (yarı-A'da fit) | 3.10e-05 |
| RAFDB | 1.7 | 16 | yuvarlak grid noktası | — | — |
| RAFDB | 2.2 | 10 | yuvarlak grid noktası | — | — |

Hiçbir satır koşu ADINDAN çıkarılmadı; her koşunun kendi `run_args.json`'undaki `teacher_temperature_scale` okundu. `--teacher-temperature-scale` bayrağı eklenmeden önce koşulmuş koşularda anahtar yoktur ve belgelenmiş varsayılan T=1.0 kabul edilir (o koşular bu tabloya girmez).

## İki fit yan yana

| öğretmen | tam fold T\* | yarı-A T\* | fark |
|---|---|---|---|
| primary | 1.261341 | — (fit edilmedi) | — |
| stage1 | 1.349393 | 1.340569 | 0.008824 |
| vae9182 | 0.982938 | — (fit edilmedi) | — |

Yarı-bölme: n_total=3068, yarı-A=1534, yarı-B=1534, bölme tohumu=1234. Artefakt yarı-B indekslerini de saklıyor, yani bölme yeniden üretilebilir.

## Ne değişir, ne değişmez

- **Hiçbir sayı değişmez.** Koşular 1.3406'yı kullandı ve bu dosya onu doğruluyor; hiçbir koşu 1.3494'ü kullanmadı. Sonuçlar olduğu gibi kalır.
- **Metin değişir.** §3.3 ile Tablo B.2'den *tam fold* diyen taraf yanlıştır ve **yarı fold (yarı-A'da fit)** olarak düzeltilmelidir.
- **Yöntem olarak doğru olan da buydu.** T*'ı değerlendirileceği veriye fit etmek iyimserlik taşırdı; yarı-A'da fit edip yarı-B'de ölçmek bunun tam olarak kaçınılması gereken hâlidir. Yani çelişki bir yöntem hatası değil, bir **başlık hatası** — ve düzeltme yöntemi zayıflatmaz, doğru anlatır.
- İki fit arasındaki fark 0.0088 (0.65%), yani dağıtılan değer tam-fold optimumunun çok yakınında; çelişki maddi bir sapma değil, yalnız yanlış etiketlenmiş bir prosedür.

---

Üretici: `diagnostics/tstar_provenance.py` · kaynaklar: her koşunun `run_args.json`'u + `diagnostics/teacher_temperature_scaling/{temperature_fit,b3_tstar_halfsplit}.json` · `MISCAL_T` `build_runs_ledger`'dan ithal

