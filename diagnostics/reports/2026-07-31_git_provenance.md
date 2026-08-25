# Git gerçeği — §4 cümlesinin doğru hâli

**Rapor tarihi:** 2026-07-31 · **Soran:** `planning/ide_prompt_export_bandi.md` §6
**Ölçüm:** `git log --reverse` + her ön-kayıt artefaktı için `git log --diff-filter=A`

---

## Kısa hüküm

**Sorduğun iki şıktan hiçbiri doğru değil; gerçek üçüncü bir durum.**

Repo 11 Temmuz'dan beri git altında. Ama **14 Temmuz ile 31 Temmuz arasında tek bir commit
yok**, ve bütün ön-kayıtlar tam olarak o boşlukta donduruldu. Yani git *vardı* ama
*uyuyordu*: hiçbir tahmin bir commit zaman damgası taşımıyor.

Sonuç: **git, geçmişe dönük hiçbir kanıt gücü eklemiyor.** Zaman damgası zinciri olduğu gibi
kalıyor — artefakt mtime'ı + koşu dizininin kendi damgası.

---

## 1. Commit geçmişi (11 commit)

```
2026-07-11 22:37:46  51b05bf  Initial commit: POSTER-Var KD pipeline with Phase 0 extensions
2026-07-11 22:41:21  b976572  Split extended ablation into per-machine launchers
2026-07-12 12:47:39  8e5db21  Add verify_machine2_setup.ps1 pre-flight check
2026-07-12 14:39:37  b8a2e23  Fix RAF-DB new-recipe grid: feed teacher its native 224px
2026-07-12 20:43:42  95884b8  Add -SkipBaseline to AffectNet+8 grid launcher; add resume script
2026-07-13 04:38:52  31cab14  Add -StartAt param to AffectNet+8 launcher
2026-07-13 12:29:50  cb27527  Resume checkpoint: g2g_kl done (61.93%)
2026-07-14 09:53:39  e139a59  Resume checkpoint: logit_std done (58.08%)
2026-07-14 17:41:48  902c5b4  Resume checkpoint: adaptive_t done (61.63%)      <-- kampanya öncesi son
                     ·
                     ·   17 GÜN, SIFIR COMMIT  <-- bütün ön-kayıtlar burada donduruldu
                     ·
2026-07-31 17:04:24  9b2d31c  RAF-DB calibration campaign: full diagnostics layer, prereg, docs
2026-07-31 18:05:56  a6a18d0  One-way repo -> Drive export band with a checksummed MANIFEST
```

İlk dokuz commit AffectNet+8 ablasyon dönemine ait ve RAF-DB kalibrasyon kampanyasından
öncedir. Kampanyanın hiçbir parçası 31 Temmuz'a kadar versiyon kontrolüne girmedi.

## 2. Ön-kayıt artefaktları: dondurulma vs. ilk commit

| # | artefakt | donduruldu | git'e ilk girdiği commit |
|---|---|---|---|
| A5 | `diagnostics/bridge_teacher_check.py` | 2026-07-20 13:41 | 9b2d31c · 07-31 17:04 |
| A6 | `rafdb_p1_temperature_doseresponse_queue.ps1` | 2026-07-23 10:34 | 9b2d31c · 07-31 17:04 |
| A1 | `rafdb_p1_vae9182_flatcontrol_queue.ps1` | 2026-07-24 18:05 | 9b2d31c · 07-31 17:04 |
| A2 | `rafdb_p3_then_miscal_chain.ps1` | 2026-07-25 14:35 | 9b2d31c · 07-31 17:04 |
| A3 | `ferplus_dose_response_queue.ps1` | 2026-07-26 13:27 | 9b2d31c · 07-31 17:04 |
| A4 | `ferplus_tjsd_queue.ps1` | 2026-07-27 12:56 | 9b2d31c · 07-31 17:04 |
| A7 | `rafdb_p1_logit_std_seeds_queue.ps1` | 2026-07-29 01:23 | 9b2d31c · 07-31 17:04 |
| A8 | `rafdb_p2_gate_oracle_seeds_queue.ps1` | 2026-07-29 01:26 | 9b2d31c · 07-31 17:04 |
| P4 | `rafdb_p4_noclassweight_controls_queue.ps1` | 2026-07-30 14:43 | 9b2d31c · 07-31 17:04 |
| P5 | `rafdb_p5_oracle_replication_queue.ps1` | 2026-07-31 14:14 | 9b2d31c · 07-31 17:04 |

**Onunun da ilk commit'i aynı:** `9b2d31c`, 31 Temmuz 17:04. A1–A8 için bu, sonuçlar çoktan
elde olduktan **sonra**dır. Dolayısıyla commit zaman damgası bu sekiz ön-kayıt için kanıt
değildir — yalnızca "31 Temmuz'da bu dosyalar buydu" der.

## 3. Tek kısmi istisna: P5

| olay | zaman |
|---|---|
| P5 beyanı donduruldu (`rafdb_p5_oracle_replication_queue.ps1` mtime) | 07-31 **14:14:11** |
| P5 koşu 1/6 başladı (dizin damgası) | 07-31 **14:14:40** (+29 sn) |
| P5 koşu 1/6 bitti | 07-31 **16:33:53** |
| commit `9b2d31c` (beyan git'e girdi) | 07-31 **17:04:24** |
| P5 koşu 2–6 sonuçları | henüz yok (ETA 08-01 ~04:35) |

Commit, koşu 1'in bitişinden **30 dakika sonra**, koşu 2–6'nın sonuçlarından ise **önce**.
Yani P5 için git kısmi bir kanıt sunuyor: beyanın 6 koşudan 5'inin sonucundan önce var
olduğu commit'le sabit. Tam değil — "bütün sonuçlardan önce" diyemeyiz.

---

## 4. §4 için önerilen cümle

Şu anki cümle (*"the codebase is not under version control"*) **olgusal olarak yanlış** ve
kalkmalı. Ama önerdiğin yedek cümle de yanlış olur:

> ~~"was not under version control at the time the predictions were frozen; it has since been
> placed under git"~~

Repo o sırada **git altındaydı** — git yalnızca kullanılmıyordu. Bu cümle bir yanlışı başka
bir yanlışla değiştirir. Doğrusu commit'in yokluğunu söylemek, versiyon kontrolünün
yokluğunu değil:

> The codebase is version-controlled with Git. No commit, however, falls within the window in
> which the predictions were frozen (14–31 July 2026): the pre-registration artifacts entered
> version control only afterwards, in a single commit. The timestamp evidence therefore does
> not rest on commit history. It rests on two independent marks described above — the
> artifact's own modification time, and the timestamp of the training run's output directory,
> which the training script writes at launch and never rewrites.

Kazandığımız şey bir kanıt değil, bir **doğruluk**: yanlış bir cümle kalkıyor ve zaman
damgası argümanı zaten dayandığı yerde duruyor. §4 kendini satmıyordu; yalnızca yanlış bir
gerekçe gösteriyordu.

## 5. `diagnostics/PREREGISTRATIONS.md` de aynı yanlışı taşıyor

11. satır: *"`poster-var` **git deposu değil.** Dolayısıyla hiçbir ön-kaydın commit hash'i
yok."* İlk cümle yanlış, ikinci cümle **doğru**. Bölümün kalan mantığı (mtime + koşu dizini,
"kural: (1) < (2)") olduğu gibi geçerli. Düzeltme: ilk cümleyi yukarıdaki gerekçeyle
değiştir, gerisine dokunma. Ertelenen belge turuna yazıldı.

## 6. Dondurma tag'leri hakkında uyarı (§7.3)

§7.3 tag'leri *"zaman damgası disiplinimizin kriptografik karşılığı; hakeme karşı en güçlü
kanıt biçimi"* diye tanımlıyor. Bu **ileriye dönük** doğru, **geriye dönük yanlış**.

Bugün atılacak bir `audit-frozen-131` tag'i bugünkü bir commit'i işaret eder; denetimin
30 Temmuz'da dondurulduğuna dair hiçbir şey kanıtlamaz. Tag, işaret ettiği commit'ten daha
eski bir gerçeği belgeleyemez. Bu yüzden tag'ler atıldı ama **belgeleyici** olarak, kanıt
olarak değil (`git tag -n` çıktısında bu sınır yazılı).

Gerçek kanıt gücü **bundan sonraki** dondurmalarda: beyan yazılır → commit → tag → koşu
başlar. Bu zincir hakem karşısında sağlamdır. İlk uygulanabileceği an P5 sonrası hükümdür.
