# Decision 0004: isolate historical values behind resolved-ID-only lookup

Status: accepted for weak discrepancy evidence; prohibited for mapping and confidence promotion

The uploaded archive contains several plausibly named historical collections. Direct inspection showed that `report_yearly` and `report_quaterly` cover no code in the 27-bank registry, despite containing generic CDKT/KQKD structures. Indexing them as bank history would introduce structurally plausible but wrong-sector evidence. The allowlisted `data_chart` collection instead contains exactly one annual and one quarterly document for every registered bank and exposes numeric source keys that intersect 79 supplied ReportNormIDs.

Only `data_chart` documents with `stock_industry=bank` and a code from the hashed bank registry are indexed. Numeric keys must already exist in the supplied schema; unknown numeric and named/formula keys are excluded and audited. `YTD_<ReportNormID>` is retained as a separate upstream-derived series. Unit and scope stay UNKNOWN. Lookup requires an independently resolved ID and accepts no label or PDF value. DuckDB constraints make `can_map_pdf` and `can_promote_pdf` permanently false.

The index may flag a discrepancy for targeted rereading or review. It cannot choose an ID, overwrite a value, resolve a blank, supply a PDF derivation operand, satisfy the no-history-conflict gate by agreement alone, or establish production truth. A missing/corrupt index or code/policy hash drift disables Mongo-assisted mode without disabling PDF-only processing.

The local DuckDB is reconstructable and excluded from Git. Its registry, policy, builder, evaluator, and E-0008 results are versioned. Routine bootstrap revalidates the current database hash, row and bank counts, duplicate identity, ID 1944 absence, and safety flags.
