# Observed Cronfig M4 → M5 data compatibility fixes

Local rehearsal only. Reaudit the final source dump before applying these to a production migration copy. Never run them against the live source.

- Four of nine email definitions had `headers=''`. M5 converts this column to JSON NOT NULL; an empty string is invalid JSON. Replace only empty strings with `[]`, preserving nonempty header definitions.
- The legacy `mautic_intelligent_campaigns_outcomes` table had zero rows, but its `properties` column still advertised Doctrine's removed `json_array` type. M5's built-in converter does not include that table. Update only its type comment to `json`, preserving LONGTEXT storage, NOT NULL and the table itself.

Do not use schema-update/drop commands to remove unfamiliar legacy tables. Preserve the original snapshot and compare meaningful record counts after migrations.

Additional M5 rehearsal findings:

- Old plugin records have null versions. ReloadHelper passed null into the string-only PluginUpdateEvent constructor. The local `m5-null-plugin-version.patch` represents unknown versions as an empty string, preserving the helper's existing empty-version logic. This patch belongs only to the intermediate M5 runtime unless a later version independently needs it.
- M5 expects GrapesJS tables although the M4 source did not have that plugin. `mautic:plugins:reload` initializes the plugin. Its generated email_id was UNSIGNED while the legacy emails.id is signed. After verifying the newly created plugin table is empty, align the foreign-key column with the parent and add the intended CASCADE constraint. Do not change signedness on the live emails table or use a global schema update.
- Migration 20201026101117 changed column encoding, then its postUp failed because the M5 ORM referenced columns supplied by later migrations. A retry skips the encoding step, but that would omit the text conversion. After the full schema exists, `complete-m5-emoji.php` performs the official postUp transformations, accepting Doctrine's entity iterator rows and preserving null text. It checked 9 emails, 61 email copies and 0 dynamic-content records. Do not blindly mark migrations complete merely to suppress warnings.
- M5's configuration migration moves app/config/local.php to config/local.php. Carry the migrated file forward.
- On this Mac, Symfony's recursive directory scan failed through the bind mount despite the directories being present. DDEV `performance_mode: mutagen` resolved it; use that for subsequent stages and flush synchronization before making host-side snapshots.

M5 initial acceptance: migrations and update finish returned successfully; login and form IDs 1/9 returned HTTP 200; the original contact/submission/email-stat counts were preserved. This is not yet final M7 functional acceptance.

M6 rehearsal findings:

- Charset migration 20211020114811 assumes `mautic_integration_reference` exists before dropping/recreating it. The source lacked it. Recreate exactly the migration's intended non-unique index before retrying; other already-applied DDL remains intact.
- The legacy Citrix event index used full 255-character prefixes across enough columns to exceed InnoDB's 3072-byte limit under utf8mb4. Shorten only those non-unique index prefixes to 191; stored field values and unique constraints are unchanged.
- M6.0.9 migration and finish completed after these repairs. Login and form IDs 1/9 returned HTTP 200. Contacts (69,463), form submissions (99,156), and email-stat records (69,302) remained unchanged. Database has 123 tables. A separate application/database checkpoint was saved before M7.

M7 rehearsal findings:

- New user-invite, campaign redirect, SMS/push translation and point-insight foreign keys assumed unsigned IDs, while the existing parent IDs are signed. The SQL repairs match only the new referencing columns to their parents and explicitly install the missing constraints. All six repaired constraints (including M5 GrapesJS) were checked in information_schema. No parent IDs or existing record IDs were rewritten.
- One user's preferences contained serialized null (`N;`), which cannot hydrate M7's typed array property. Replace only null preferences with the serialized empty array (`a:0:{}`). This was discovered by an actual form submission; existing populated preferences remain intact.
- The original Cronfig 1.0 plugin's legacy controller returned HTTP 500 on M7. The local replacement is based on `cronfig/mautic-cronfig` branch 5.x, immutable commit `a6e49442835444d51044221aac317911b5f4204b`, with `cronfig-plugin-m7.patch` applied. That local patch declares the tested M7.2 dependency, removes secret values from mismatch logs, and returns HTTP 500 when a console command exits nonzero (the upstream wrapper incorrectly returned SUCCESS/200). No upstream plugin branch or release was changed.
- Endpoint tests used a temporary local-only secret namespace and a harmless `--version` command: valid key → HTTP 200/SUCCESS; wrong key → 403; nonexistent command → 500/ERROR. The temporary namespace was removed afterward. Production Cronfig API/secret keys are blanked only in the running local preview so browser scripts cannot use the live account. The original keys remain in the untouched private source capture.
- Login, form generation and plugin download checks passed. A real local contact-form submission created the test contact/submission and its notification appeared in Mailpit, with SMTP configured to 127.0.0.1:1025. Outbound network traffic remained blocked. The clean database was then restored and the user-preference fix reapplied to remove test records before the final checkpoint.

The original database migration-history entries remain. Some upstream migrations report themselves skipped because their schema already exists; warnings alone must not be treated as a migration failure, nor should history entries be deleted just to hide them. Review migration results and verify repaired constraints and application behavior explicitly.
