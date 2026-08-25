# Kuyruk üretim raporu

Üretici: `diagnostics/build_replicate_queue.py`. Her komut satırı referans koşunun kendi `run_args.json`'undan üretildi; bayrak adları `train_rafdb_kd.py`'nin argparse nesnesinden okundu.

**Gidiş-dönüş kapısı geçildi.** Her komut satırı parser'a geri verildi ve referans namespace'e birebir çözüldüğü doğrulandı (kasıtlı değişenler hariç); tutmasaydı bu dosya hiç yazılmazdı. Yani "tarif birebir aynı" ölçülmüş bir ifade, anlatılan bir iddia değil.

### A12 · RAFDB_stage1_gate_noclassweight_b070_T6_224_400e_swa200_seed1

- referans: `results\unified_students\RAFDB_stage1_gate_noclassweight_b070_T6_224_400e_swa200\2026-07-19-08-10-43\run_args.json`
- değişen: `seed` 42 → 1, `name`
- varsayılana düşen anahtar (3): `teacher_temperature_scale`=1.0, `allow_tempscale_with_mechanism`=False, `student_arch`='plus'
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A12 · RAFDB_stage1_gate_noclassweight_b070_T6_224_400e_swa200_seed43

- referans: `results\unified_students\RAFDB_stage1_gate_noclassweight_b070_T6_224_400e_swa200\2026-07-19-08-10-43\run_args.json`
- değişen: `seed` 42 → 43, `name`
- varsayılana düşen anahtar (3): `teacher_temperature_scale`=1.0, `allow_tempscale_with_mechanism`=False, `student_arch`='plus'
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A12 · RAFDB_stage1_gate_target_logvar_b070_T6_224_400e_swa200_seed1

- referans: `results\unified_students\RAFDB_stage1_gate_target_logvar_b070_T6_224_400e_swa200\2026-07-20-01-22-31\run_args.json`
- değişen: `seed` 42 → 1, `name`
- varsayılana düşen anahtar (3): `teacher_temperature_scale`=1.0, `allow_tempscale_with_mechanism`=False, `student_arch`='plus'
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A12 · RAFDB_stage1_gate_target_logvar_b070_T6_224_400e_swa200_seed43

- referans: `results\unified_students\RAFDB_stage1_gate_target_logvar_b070_T6_224_400e_swa200\2026-07-20-01-22-31\run_args.json`
- değişen: `seed` 42 → 43, `name`
- varsayılana düşen anahtar (3): `teacher_temperature_scale`=1.0, `allow_tempscale_with_mechanism`=False, `student_arch`='plus'
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A12 · RAFDB_primary_gate_noclassweight_b070_T6_224_400e_swa200_seed1

- referans: `results\unified_students\RAFDB_primary_gate_noclassweight_b070_T6_224_400e_swa200\2026-07-19-10-39-49\run_args.json`
- değişen: `seed` 42 → 1, `name`
- varsayılana düşen anahtar (3): `teacher_temperature_scale`=1.0, `allow_tempscale_with_mechanism`=False, `student_arch`='plus'
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A12 · RAFDB_primary_gate_noclassweight_b070_T6_224_400e_swa200_seed43

- referans: `results\unified_students\RAFDB_primary_gate_noclassweight_b070_T6_224_400e_swa200\2026-07-19-10-39-49\run_args.json`
- değişen: `seed` 42 → 43, `name`
- varsayılana düşen anahtar (3): `teacher_temperature_scale`=1.0, `allow_tempscale_with_mechanism`=False, `student_arch`='plus'
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A12 · RAFDB_primary_gate_target_logvar_b070_T6_224_400e_swa200_seed1

- referans: `results\unified_students\RAFDB_primary_gate_target_logvar_b070_T6_224_400e_swa200\2026-07-20-04-53-00\run_args.json`
- değişen: `seed` 42 → 1, `name`
- varsayılana düşen anahtar (3): `teacher_temperature_scale`=1.0, `allow_tempscale_with_mechanism`=False, `student_arch`='plus'
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A12 · RAFDB_primary_gate_target_logvar_b070_T6_224_400e_swa200_seed43

- referans: `results\unified_students\RAFDB_primary_gate_target_logvar_b070_T6_224_400e_swa200\2026-07-20-04-53-00\run_args.json`
- değişen: `seed` 42 → 43, `name`
- varsayılana düşen anahtar (3): `teacher_temperature_scale`=1.0, `allow_tempscale_with_mechanism`=False, `student_arch`='plus'
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A12 · RAFDB_vae9182_gate_noclassweight_b070_T6_224_400e_swa200_seed1

- referans: `results\unified_students\RAFDB_vae9182_gate_noclassweight_b070_T6_224_400e_swa200\2026-07-19-13-01-18\run_args.json`
- değişen: `seed` 42 → 1, `name`
- varsayılana düşen anahtar (3): `teacher_temperature_scale`=1.0, `allow_tempscale_with_mechanism`=False, `student_arch`='plus'
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A12 · RAFDB_vae9182_gate_noclassweight_b070_T6_224_400e_swa200_seed43

- referans: `results\unified_students\RAFDB_vae9182_gate_noclassweight_b070_T6_224_400e_swa200\2026-07-19-13-01-18\run_args.json`
- değişen: `seed` 42 → 43, `name`
- varsayılana düşen anahtar (3): `teacher_temperature_scale`=1.0, `allow_tempscale_with_mechanism`=False, `student_arch`='plus'
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A13 · RAFDB_vae9182_frontier_w100ns_tempscale_T170_b070_T6_224_400e_swa200_seed42

- referans: `results\unified_students\RAFDB_vae9182_frontier_w100ns_b070_T6_224_400e_swa200_seed42\2026-07-28-17-21-01\run_args.json`
- değişen: `teacher_temperature_scale` 1.0 → 1.7, `seed` 42 → 42, `name`
- varsayılana düşen anahtar (0): yok
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A13 · RAFDB_vae9182_frontier_w100ns_tempscale_T170_b070_T6_224_400e_swa200_seed1

- referans: `results\unified_students\RAFDB_vae9182_frontier_w100ns_b070_T6_224_400e_swa200_seed42\2026-07-28-17-21-01\run_args.json`
- değişen: `teacher_temperature_scale` 1.0 → 1.7, `seed` 42 → 1, `name`
- varsayılana düşen anahtar (0): yok
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A13 · RAFDB_vae9182_frontier_w100ns_tempscale_T220_b070_T6_224_400e_swa200_seed42

- referans: `results\unified_students\RAFDB_vae9182_frontier_w100ns_b070_T6_224_400e_swa200_seed42\2026-07-28-17-21-01\run_args.json`
- değişen: `teacher_temperature_scale` 1.0 → 2.2, `seed` 42 → 42, `name`
- varsayılana düşen anahtar (0): yok
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

### A13 · RAFDB_vae9182_frontier_w100ns_tempscale_T220_b070_T6_224_400e_swa200_seed1

- referans: `results\unified_students\RAFDB_vae9182_frontier_w100ns_b070_T6_224_400e_swa200_seed42\2026-07-28-17-21-01\run_args.json`
- değişen: `teacher_temperature_scale` 1.0 → 2.2, `seed` 42 → 1, `name`
- varsayılana düşen anahtar (0): yok
- ifade edilemeyen (None): `teacher_cache`
- parser'da olmayan run_args anahtarı: yok

