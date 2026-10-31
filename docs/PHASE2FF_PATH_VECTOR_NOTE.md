# Phase 2ff — CArmy path-vector / subject RO note

**Live:** pid 9928 · 1936-01-04 11:00 · hours=83 · ETH tag=15
**Path nonempty armies:** 0 / 17

## Path confidence

| path | needs | status |
|------|-------|--------|
| Ordinary CMove | province_arr + path_arr game allocs | live leaf sample STUBBED; subject handle/province READY |
| StrategicRedeploy | army handle + scalar province | subject READY from live ETH CArmy |
| SupportAttack | handle@+0x28 + target_province@+0x30 | subject READY (recipe only) |

Empty movement_dest ⇒ do **not** invent destinations. Candidates (if any) are province-id vectors only.

allow_post **False**. 2fb recipe **not** executed. tool-gate **CLOSED**.
