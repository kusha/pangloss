# Issues: Pangloss MVP

This file tracks problems, gotchas, and edge cases encountered during implementation.

---


## Task 3: Speaker Count Data Extraction

### Low ASJP Coverage (4.6%)

**Issue**: Only 4.6% of ASJP language entries (527/11,540) have speaker count mappings.

**Root Cause**: 
- CLDR territoryInfo contains languages at the ISO 639-3 code level
- ASJP database has ~11,540 entries but only ~6,135 unique ISO codes
- Multiple ASJP variants/dialects per single ISO code cannot all be individually annotated

**Mitigation**:
- Strategy aggregates all ASJP variants under their ISO code's speaker count
- Creates a 1-to-1 mapping: 1 ISO code → 1 first-encountered ASJP ID
- Preserves all speaker data, but users should understand many variants share counts

**Future Enhancement**:
- Ethnologue or Glottolog could provide dialect-level population estimates
- Would require different data source (not free/no licensing conflict)
- For MVP, current approach is acceptable as it doesn't lose data

---

## Resolution

**Status**: RESOLVED

The low ASJP coverage (4.6% with CLDR alone) was addressed by integrating ASJP raw/lists.txt data.

**Solution Applied**:
- Added fallback to ASJP raw/lists.txt for unmapped languages
- Coverage improved from 4.6% to 91.2% (10,526/11,540)
- CLDR data preferred when available (higher quality)
- ASJP raw data used as fallback for rare/regional languages

---
