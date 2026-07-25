# Quality check results

Root: `/workspace/ai-lead-os`
Invocation mode: uv run <tool>

### Ruff check — PASS (exit code 0)
`uv run ruff check .`

```
All checks passed!
```


### Ruff format check — PASS (exit code 0)
`uv run ruff format --check .`

```
314 files already formatted
```


### mypy (strict) — PASS (exit code 0)
`uv run mypy src`

```
Success: no issues found in 195 source files
```


### Alembic upgrade head — PASS (exit code 0)
`uv run alembic upgrade head`

```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
```


### Alembic check (no model drift) — PASS (exit code 0)
`uv run alembic check`

```
No new upgrade operations detected.
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.schemas
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.tables
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.types
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.constraints
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.defaults
INFO  [alembic.runtime.plugins] setting up autogenerate plugin alembic.autogenerate.comments
```


### pytest with coverage — PASS (exit code 0)
`uv run pytest --cov=ai_lead_os --cov-report=term-missing`

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /workspace/ai-lead-os
configfile: pyproject.toml
testpaths: tests
plugins: cov-6.3.0
collected 1006 items

tests/integration/test_a48_reliability.py ................               [  1%]
tests/integration/test_a50_job_lifecycle.py ..........                   [  2%]
tests/integration/test_budget_gateway.py ...                             [  2%]
tests/integration/test_budget_production_gaps.py .........               [  3%]
tests/integration/test_campaign_queue.py .....................           [  5%]
tests/integration/test_campaign_version.py ............................. [  8%]
........                                                                 [  9%]
tests/integration/test_campaign_version_cli.py ...........               [ 10%]
tests/integration/test_campaigns.py ..                                   [ 10%]
tests/integration/test_cli.py ..........                                 [ 11%]
tests/integration/test_cli_smoke.py ......................               [ 14%]
tests/integration/test_collect_places.py ....                            [ 14%]
tests/integration/test_company_import_service.py ..........              [ 15%]
tests/integration/test_contact_enrichment.py ..                          [ 15%]
tests/integration/test_contact_routes.py .                               [ 15%]
tests/integration/test_data_quality.py ..........                        [ 16%]
tests/integration/test_delivery_events_reconciliation.py ............... [ 18%]
.                                                                        [ 18%]
tests/integration/test_detect_duplicates.py .................            [ 19%]
tests/integration/test_email_discovery.py ..                             [ 20%]
tests/integration/test_entity_duplicate_candidate.py ......              [ 20%]
tests/integration/test_entity_duplicates_exporters.py ........           [ 21%]
tests/integration/test_entity_merge_foundation.py ................       [ 23%]
tests/integration/test_instantly_doctor_cli.py .........                 [ 24%]
tests/integration/test_instantly_validate_personalization_cli.py ......  [ 24%]
tests/integration/test_migrations.py ........................            [ 27%]
tests/integration/test_outbound_delivery.py ............................ [ 29%]
..............................                                           [ 32%]
tests/integration/test_pipeline.py ..                                    [ 33%]
tests/integration/test_plan_merge.py ........................            [ 35%]
tests/integration/test_production_metrics.py .....                       [ 35%]
tests/integration/test_provider_event_backfill.py ......                 [ 36%]
tests/integration/test_provider_event_intake.py .............            [ 37%]
tests/integration/test_provider_event_intelligence_cli.py ..........     [ 38%]
tests/integration/test_qualification.py ....                             [ 39%]
tests/integration/test_recover_failed_activation.py .................... [ 41%]
.....                                                                    [ 41%]
tests/integration/test_reports_cli.py .....                              [ 42%]
tests/integration/test_repositories.py ...                               [ 42%]
tests/integration/test_review_drafts.py ..............                   [ 43%]
tests/integration/test_review_duplicates.py .............                [ 45%]
tests/integration/test_review_enrollments.py ..............              [ 46%]
tests/integration/test_send_delivery.py ................................ [ 49%]
...........................                                              [ 52%]
tests/integration/test_send_delivery_campaign_version_v2.py ........     [ 53%]
tests/integration/test_services.py .....                                 [ 53%]
tests/integration/test_simulate_merge.py ............                    [ 54%]
tests/integration/test_validate_provider_contract.py ................... [ 56%]
...........                                                              [ 57%]
tests/integration/test_visual_website_intelligence_service.py ...        [ 58%]
tests/integration/test_webhook_receiver.py ...............               [ 59%]
tests/integration/test_website_enrichment.py ...                         [ 59%]
tests/integration/test_website_intelligence_service.py .....             [ 60%]
tests/unit/test_business_observations.py ..........                      [ 61%]
tests/unit/test_campaign_templates.py ....                               [ 61%]
tests/unit/test_campaign_version_fingerprint.py ..........               [ 62%]
tests/unit/test_cold_email.py .........                                  [ 63%]
tests/unit/test_company_import_adapter.py ........                       [ 64%]
tests/unit/test_company_import_report.py ...                             [ 64%]
tests/unit/test_company_import_schema.py .........                       [ 65%]
tests/unit/test_compliance.py ........                                   [ 66%]
tests/unit/test_contact_candidates.py .....                              [ 66%]
tests/unit/test_contact_route_rules.py ...                               [ 67%]
tests/unit/test_email_discovery_rules.py ................                [ 68%]
tests/unit/test_instantly_adapter.py ...                                 [ 69%]
tests/unit/test_instantly_delivery_adapter.py .......................... [ 71%]
......................................................................   [ 78%]
tests/unit/test_instantly_personalization_adapter.py ..........          [ 79%]
tests/unit/test_instantly_provider_doctor.py ........................... [ 82%]
...............                                                          [ 83%]
tests/unit/test_instantly_webhook_verifier.py .......                    [ 84%]
tests/unit/test_normalization.py .............                           [ 85%]
tests/unit/test_offer_engine.py ...............                          [ 87%]
tests/unit/test_outcomes.py ......                                       [ 87%]
tests/unit/test_personalization_tokens.py ........                       [ 88%]
tests/unit/test_personalized_drafts.py ..............                    [ 90%]
tests/unit/test_places_adapter.py .........                              [ 91%]
tests/unit/test_provider_event_fingerprint.py ................           [ 92%]
tests/unit/test_provider_personalization_validation.py .........         [ 93%]
tests/unit/test_provider_sync.py ..............                          [ 94%]
tests/unit/test_pytest_isolation.py ......                               [ 95%]
tests/unit/test_qualification_scoring.py ....                            [ 95%]
tests/unit/test_schemas_enums_export.py ....                             [ 96%]
tests/unit/test_settings.py ..                                           [ 96%]
tests/unit/test_status_memo.py ........                                  [ 97%]
tests/unit/test_visual_website_intelligence.py ...........               [ 98%]
tests/unit/test_website_adapter.py ............                          [ 99%]
tests/unit/test_website_intelligence.py ....                             [100%]

================================ tests coverage ================================
_______________ coverage: platform linux, python 3.12.3-final-0 ________________

Name                                                                   Stmts   Miss Branch BrPart  Cover   Missing
------------------------------------------------------------------------------------------------------------------
src/ai_lead_os/__init__.py                                                 1      0      0      0   100%
src/ai_lead_os/__main__.py                                                 3      3      2      0     0%   1-4
src/ai_lead_os/adapters/__init__.py                                        0      0      0      0   100%
src/ai_lead_os/adapters/company_import/__init__.py                         3      0      0      0   100%
src/ai_lead_os/adapters/company_import/base.py                            36      0     16      0   100%
src/ai_lead_os/adapters/company_import/generic_csv.py                     16      0      2      0   100%
src/ai_lead_os/adapters/delivery/__init__.py                               6      0      0      0   100%
src/ai_lead_os/adapters/delivery/base.py                                  50      3      2      1    92%   112, 124, 142
src/ai_lead_os/adapters/delivery/fake.py                                  28      5      4      1    81%   43, 46, 51, 60, 72
src/ai_lead_os/adapters/delivery/instantly.py                            514     34    160     16    92%   251, 297-298, 415->414, 454, 472, 516-517, 528-529, 536, 627-639, 904->exit, 1120, 1235, 1291, 1309, 1343-1351, 1378, 1382, 1385, 1442->1444, 1589, 1636-1637, 1735-1740, 1744-1745
src/ai_lead_os/adapters/delivery/provider_doctor.py                       67      0      0      0   100%
src/ai_lead_os/adapters/delivery/provider_events.py                       27      0      0      0   100%
src/ai_lead_os/adapters/places/__init__.py                                 4      0      0      0   100%
src/ai_lead_os/adapters/places/client.py                                  93     17     20      5    79%   83, 88-89, 127-133, 143, 147, 159, 164-170, 177
src/ai_lead_os/adapters/places/dto.py                                     25      0      0      0   100%
src/ai_lead_os/adapters/places/exceptions.py                               6      0      0      0   100%
src/ai_lead_os/adapters/places/mapper.py                                  24      0      6      1    97%   14->13
src/ai_lead_os/adapters/places/persistence.py                              6      0      0      0   100%
src/ai_lead_os/adapters/places/quota.py                                   34      0      8      0   100%
src/ai_lead_os/adapters/sending/__init__.py                                3      0      0      0   100%
src/ai_lead_os/adapters/sending/base.py                                   44      0      0      0   100%
src/ai_lead_os/adapters/sending/instantly.py                              73      6     14      5    85%   74->76, 104, 106-107, 108->93, 110-112, 134->136
src/ai_lead_os/adapters/website_intelligence/__init__.py                   5      0      0      0   100%
src/ai_lead_os/adapters/website_intelligence/evidence.py                  91      1     32      1    98%   75
src/ai_lead_os/adapters/website_intelligence/model.py                     41      0      0      0   100%
src/ai_lead_os/adapters/website_intelligence/openai_vision.py            117     12     24     11    84%   67, 86-90, 151, 216, 219, 222, 223->217, 224->223, 226->223, 228, 249
src/ai_lead_os/adapters/website_intelligence/visual.py                   113     19     18      6    79%   101-111, 135, 139, 142, 144, 151, 165-170, 180
src/ai_lead_os/adapters/websites/__init__.py                               0      0      0      0   100%
src/ai_lead_os/adapters/websites/client.py                               122     23     34      9    76%   27, 74, 84, 88-90, 98->100, 104, 107, 118, 121, 134, 152, 157-159, 161-162, 164-172
src/ai_lead_os/adapters/websites/contact_candidates.py                   119     18     46      5    86%   67, 71, 75, 151-153, 174-176, 177->169, 191-193, 194->188, 209-211, 230-232
src/ai_lead_os/adapters/websites/contact_routes.py                       166     27     70     22    78%   85, 89-90, 110, 221, 223, 225, 227, 229, 231, 233, 237, 239, 249, 253, 278, 280, 282, 284, 287, 314, 316, 318-320, 413-414
src/ai_lead_os/adapters/websites/email_discovery.py                       87      8     34      5    89%   79, 82, 87, 142, 166-168, 170
src/ai_lead_os/adapters/websites/exceptions.py                             6      0      0      0   100%
src/ai_lead_os/adapters/websites/html_parser.py                          126      6     54     10    91%   56->58, 63->exit, 66-67, 78-79, 86->88, 107->104, 110-111, 141->146, 144->146, 146->148, 148->150, 150->152, 154->159
src/ai_lead_os/adapters/websites/normalization.py                         15      1      2      1    88%   13
src/ai_lead_os/adapters/websites/security.py                              27      4     12      2    85%   21, 27-28, 30
src/ai_lead_os/application/__init__.py                                     0      0      0      0   100%
src/ai_lead_os/application/analyze_visual_websites.py                    166     18     32      8    87%   138, 152, 154, 194, 224-226, 233, 235, 249, 272-274, 281-283, 305-306
src/ai_lead_os/application/analyze_websites.py                           120      4     20      4    94%   138, 143, 163, 280
src/ai_lead_os/application/business_observations.py                      254     23     96     11    89%   103, 114-115, 158-165, 269, 271, 273, 292, 410-416, 502-503, 557, 566, 570
src/ai_lead_os/application/campaign_queue.py                             161      1     36      2    98%   72->exit, 208
src/ai_lead_os/application/campaign_version.py                           121      2     30      3    97%   77->exit, 175, 243
src/ai_lead_os/application/campaigns.py                                  340     28     84     19    88%   234, 237, 283, 336-339, 355, 363, 370-371, 382->391, 392-395, 431, 445, 467, 470, 528, 529->543, 600, 621, 676, 689, 698, 743-745
src/ai_lead_os/application/cleanup_places.py                              47      0     12      1    98%   82->91
src/ai_lead_os/application/cold_email.py                                  30      0      2      0   100%
src/ai_lead_os/application/collect_places.py                             140      2     22      3    97%   215->219, 242, 261
src/ai_lead_os/application/company_import.py                             209      8     72      4    96%   105-112, 179->181, 237, 260-261, 380
src/ai_lead_os/application/compliance.py                                  47      6     26      2    84%   61, 88-92
src/ai_lead_os/application/contact_routes.py                             161     18     36      3    88%   78, 101, 117-124, 182-189
src/ai_lead_os/application/data_quality.py                               117      9     34      5    91%   121-122, 131-132, 157, 173-174, 176-177, 216->exit
src/ai_lead_os/application/delivery_events.py                            106      2     42      3    97%   204, 321, 371->385
src/ai_lead_os/application/detect_duplicates.py                          251     17     82     10    91%   161-163, 169-172, 301-303, 317, 332, 364, 397-398, 413->416, 447, 487
src/ai_lead_os/application/discover_emails.py                            168     12     42      5    92%   98, 133-135, 137-139, 179->177, 198, 201-202, 259, 294
src/ai_lead_os/application/enrich_contacts.py                            159     18     46      5    87%   79, 115-117, 119-121, 182-189, 245-246, 247->exit, 270
src/ai_lead_os/application/enrich_websites.py                            202      9     38      5    94%   108, 170-172, 177-178, 182, 199-200, 294->exit
src/ai_lead_os/application/job_maintenance.py                             25      0      4      0   100%
src/ai_lead_os/application/offer_engine.py                                54      2     18      2    94%   141, 163
src/ai_lead_os/application/outbound_delivery.py                          239     13     78     13    92%   156, 378, 422, 502, 507, 528, 537, 546, 553, 603, 665, 737, 744
src/ai_lead_os/application/outcomes.py                                   313     36     74     17    84%   127-129, 176-179, 227, 241->239, 257-274, 282, 293, 298, 308, 310, 323, 419, 426, 449-453, 563, 611-612, 655-656, 658-661
src/ai_lead_os/application/personalized_drafts.py                        340     20     88     13    92%   89, 213, 217, 232, 235, 317-322, 356, 435, 504, 506-508, 744, 787, 815, 840, 846
src/ai_lead_os/application/pipeline.py                                    30      0      0      0   100%
src/ai_lead_os/application/plan_merge.py                                 192     16     70     14    89%   184, 193, 254, 256, 262, 279-280, 282, 284, 286, 291, 309, 362, 364, 378, 388
src/ai_lead_os/application/production_metrics.py                          83      0     18      2    98%   86->92, 144->143
src/ai_lead_os/application/provider_event_backfill.py                     99      5     30      4    93%   48, 56->58, 136-141, 150, 183->186
src/ai_lead_os/application/provider_event_intake.py                       81      3     26      4    93%   76, 160, 175, 185->198
src/ai_lead_os/application/provider_personalization_validation.py         46      0      6      0   100%
src/ai_lead_os/application/provider_sync.py                              239      9     80      8    95%   232, 268, 270, 289->291, 291->275, 340, 389, 502, 507, 510, 600
src/ai_lead_os/application/qualify_leads.py                              305     16    110     16    92%   146, 173, 254->256, 256->258, 258->261, 282, 299->301, 314, 317, 366, 368, 374, 376, 388, 534, 539, 606-609
src/ai_lead_os/application/recover_failed_activation.py                  150     11     48     10    89%   86->exit, 148, 159, 163, 168, 230, 264, 275, 296, 306, 323-324
src/ai_lead_os/application/review_drafts.py                               56      1     18      1    97%   57
src/ai_lead_os/application/review_duplicates.py                           37      0     12      0   100%
src/ai_lead_os/application/review_enrollments.py                          50      0     18      0   100%
src/ai_lead_os/application/send_delivery.py                              366     19     88     11    93%   250-251, 253, 258, 269, 273-274, 291, 436-437, 447, 461, 473-476, 494, 813, 865, 965
src/ai_lead_os/application/simulate_merge.py                             244     12     76     12    92%   153, 398, 444, 493, 526, 571, 610, 718, 731, 771, 790, 800
src/ai_lead_os/application/status_memo.py                                 39      0      8      0   100%
src/ai_lead_os/application/validate_provider_contract.py                 141     10     50      6    92%   147, 151, 156, 164, 169, 187, 209-210, 319-326
src/ai_lead_os/budget/__init__.py                                          4      0      0      0   100%
src/ai_lead_os/budget/gateway.py                                         310     30     84     21    87%   108-109, 186-192, 211, 216-217, 220-221, 247-248, 250-251, 262-263, 287, 327, 336-337, 385-386, 397->exit, 428, 454, 470->exit, 521->541, 594->662, 614, 624, 669, 673
src/ai_lead_os/budget/notifications.py                                    74      8     12      4    86%   64, 85-91, 107, 121->123, 123->125, 127-133
src/ai_lead_os/budget/reconciliation.py                                   80      9     28     11    81%   38, 40-41, 50, 54->56, 86->100, 89, 91->93, 98-99, 100->56, 114, 139
src/ai_lead_os/cli/__init__.py                                             3      0      0      0   100%
src/ai_lead_os/cli/apps.py                                                48      0      0      0   100%
src/ai_lead_os/cli/budget.py                                             103      4     14      3    94%   77-93, 114, 130
src/ai_lead_os/cli/campaign_queue.py                                      39     28      4      0    26%   23-32, 72-98, 107-116
src/ai_lead_os/cli/campaign_version.py                                    51      0     10      0   100%
src/ai_lead_os/cli/campaigns.py                                           95     22      8      3    76%   60-61, 63, 89-91, 120-122, 165-167, 191, 198-200, 226-228, 255-257
src/ai_lead_os/cli/common.py                                              41      8     10      3    75%   54-60, 70, 95-96
src/ai_lead_os/cli/database.py                                            82      0      8      0   100%
src/ai_lead_os/cli/deliveries.py                                         199     36     44      9    80%   101-105, 112, 169-170, 182->193, 188, 207->193, 249-251, 263-264, 299-328, 362->exit, 499->506, 507, 540-542, 560-563, 570-573
src/ai_lead_os/cli/enrich.py                                              77     19     10      4    71%   37-38, 40, 67-77, 102, 121-127, 156-158, 198-200, 240-242
src/ai_lead_os/cli/enrollments.py                                         42      1      6      1    96%   74
src/ai_lead_os/cli/entities.py                                           114     12     22      4    88%   187-189, 198->203, 200-202, 221-223, 229, 245-246
src/ai_lead_os/cli/exports.py                                             37     14      0      0    62%   46-48, 76-78, 94-103
src/ai_lead_os/cli/jobs.py                                                17      1      2      1    89%   38
src/ai_lead_os/cli/leads.py                                               46     34     14      0    20%   38-64, 68-85
src/ai_lead_os/cli/outcomes.py                                            34     10      0      0    71%   66-68, 84-87, 118-120
src/ai_lead_os/cli/personalized_drafts.py                                 43      3      6      2    90%   76-77, 79
src/ai_lead_os/cli/pipeline.py                                            27     11      0      0    59%   38-59
src/ai_lead_os/cli/places.py                                              46      9      8      2    80%   68-70, 137, 145, 156-159
src/ai_lead_os/cli/pricing.py                                             42      6     12      2    78%   21, 39-41, 63-64
src/ai_lead_os/cli/providers.py                                          166     28     38      2    84%   57-59, 115-117, 136-145, 178-180, 255-257, 281-283, 385-396
src/ai_lead_os/cli/reports.py                                             50      2     10      1    92%   61-62
src/ai_lead_os/cli/scoring.py                                             25      4      4      1    83%   43-45, 75
src/ai_lead_os/cli/website.py                                             77     18     10      1    78%   71-73, 86, 126-128, 152-166, 192-194
src/ai_lead_os/config/__init__.py                                          3      0      0      0   100%
src/ai_lead_os/config/scoring.py                                          21      0      0      0   100%
src/ai_lead_os/config/settings.py                                        100      1      6      1    98%   126
src/ai_lead_os/constants/__init__.py                                       2      0      0      0   100%
src/ai_lead_os/constants/enums.py                                        590      0      0      0   100%
src/ai_lead_os/database/__init__.py                                        4      0      0      0   100%
src/ai_lead_os/database/base.py                                           10      0      0      0   100%
src/ai_lead_os/database/engine.py                                         13      0      2      1    93%   10->19
src/ai_lead_os/database/models/__init__.py                                21      0      0      0   100%
src/ai_lead_os/database/models/budget.py                                 100      1      0      0    99%   47
src/ai_lead_os/database/models/business_observation.py                    32      0      0      0   100%
src/ai_lead_os/database/models/campaign.py                               105      0      0      0   100%
src/ai_lead_os/database/models/campaign_queue.py                          26      0      0      0   100%
src/ai_lead_os/database/models/campaign_version.py                        25      0      0      0   100%
src/ai_lead_os/database/models/contact.py                                 27      0      0      0   100%
src/ai_lead_os/database/models/contact_route.py                           36      0      0      0   100%
src/ai_lead_os/database/models/entity.py                                  45      0      0      0   100%
src/ai_lead_os/database/models/entity_duplicate_candidate.py              26      0      0      0   100%
src/ai_lead_os/database/models/entity_merge.py                            25      0      0      0   100%
src/ai_lead_os/database/models/entity_merge_plan.py                       36      0      0      0   100%
src/ai_lead_os/database/models/outbound_delivery.py                       64      0      0      0   100%
src/ai_lead_os/database/models/outcome.py                                 83      0      0      0   100%
src/ai_lead_os/database/models/personalized_draft.py                      51      0      0      0   100%
src/ai_lead_os/database/models/processing_job.py                          26      0      0      0   100%
src/ai_lead_os/database/models/provider_mapping.py                        68      0      0      0   100%
src/ai_lead_os/database/models/qualification_result.py                    29      0      0      0   100%
src/ai_lead_os/database/models/source.py                                  27      0      0      0   100%
src/ai_lead_os/database/models/unresolved_provider_event.py               27      0      0      0   100%
src/ai_lead_os/database/models/website_intelligence_result.py             51      0      0      0   100%
src/ai_lead_os/database/session.py                                         8      2      0      0    75%   14-15
src/ai_lead_os/exporters/__init__.py                                       2      0      0      0   100%
src/ai_lead_os/exporters/business_observations.py                         16      0      2      0   100%
src/ai_lead_os/exporters/company_import.py                                19      0      2      0   100%
src/ai_lead_os/exporters/csv_exporter.py                                  11      0      0      0   100%
src/ai_lead_os/exporters/enrollments.py                                   30      0      2      0   100%
src/ai_lead_os/exporters/entity_duplicates.py                             54      0     10      0   100%
src/ai_lead_os/exporters/entity_merge_plans.py                            20      0      0      0   100%
src/ai_lead_os/exporters/outbound_deliveries.py                           45      6      4      1    86%   99, 157-161
src/ai_lead_os/exporters/outreach.py                                      16      0      2      0   100%
src/ai_lead_os/exporters/personalized_drafts.py                           36      9      4      1    75%   61-63, 71, 100-104
src/ai_lead_os/exporters/website_intelligence.py                          24      2      0      0    92%   123-124
src/ai_lead_os/repositories/__init__.py                                   19      0      0      0   100%
src/ai_lead_os/repositories/business_observation_repository.py            21      0      2      0   100%
src/ai_lead_os/repositories/campaign_queue_repository.py                  34      1      4      0    97%   26
src/ai_lead_os/repositories/campaign_repository.py                        59      1      6      1    97%   140
src/ai_lead_os/repositories/campaign_version_repository.py                24      0      0      0   100%
src/ai_lead_os/repositories/contact_repository.py                         19      0      0      0   100%
src/ai_lead_os/repositories/contact_route_repository.py                   19      0      0      0   100%
src/ai_lead_os/repositories/entity_duplicate_candidate_repository.py      26      0      2      0   100%
src/ai_lead_os/repositories/entity_merge_plan_repository.py               29      5      2      0    77%   49-52, 55
src/ai_lead_os/repositories/entity_repository.py                          73      1     24      1    98%   151
src/ai_lead_os/repositories/outbound_delivery_repository.py               47      2      2      1    94%   44, 116->118, 149
src/ai_lead_os/repositories/outcome_repository.py                         38      4      4      0    90%   72-75
src/ai_lead_os/repositories/personalized_draft_repository.py              26      1      2      1    93%   52->54, 57
src/ai_lead_os/repositories/processing_job_repository.py                  48      0      0      0   100%
src/ai_lead_os/repositories/provider_mapping_repository.py                46      1      4      0    98%   123
src/ai_lead_os/repositories/qualification_repository.py                   27      1      4      1    94%   42
src/ai_lead_os/repositories/source_repository.py                          19      0      0      0   100%
src/ai_lead_os/repositories/unresolved_provider_event_repository.py       15      0      0      0   100%
src/ai_lead_os/repositories/website_intelligence_repository.py            26      0      0      0   100%
src/ai_lead_os/schemas/__init__.py                                        13      0      0      0   100%
src/ai_lead_os/schemas/campaign.py                                        58      2      2      1    95%   32, 38
src/ai_lead_os/schemas/campaign_version.py                                17      0      0      0   100%
src/ai_lead_os/schemas/cold_email.py                                       7      0      0      0   100%
src/ai_lead_os/schemas/common.py                                           8      0      0      0   100%
src/ai_lead_os/schemas/company_import.py                                  55      0      2      0   100%
src/ai_lead_os/schemas/contact.py                                         32      0      0      0   100%
src/ai_lead_os/schemas/entity.py                                          59      1      2      0    98%   62
src/ai_lead_os/schemas/personalized_draft.py                              45      1     16      1    97%   61
src/ai_lead_os/schemas/processing_job.py                                  36      0      0      0   100%
src/ai_lead_os/schemas/qualification_result.py                            24      0      0      0   100%
src/ai_lead_os/schemas/source.py                                          25      0      0      0   100%
src/ai_lead_os/schemas/status_memo.py                                     21      0      0      0   100%
src/ai_lead_os/schemas/website_intelligence.py                           148      3     26      3    97%   133, 135, 171
src/ai_lead_os/services/__init__.py                                        7      0      0      0   100%
src/ai_lead_os/services/business_observation_export_service.py            50      3     10      1    93%   45, 103-104
src/ai_lead_os/services/entity_service.py                                 63     16     22      6    72%   38, 42-47, 64, 66, 74, 80, 83, 95-98, 107
src/ai_lead_os/services/export_service.py                                 31      0      6      0   100%
src/ai_lead_os/services/outreach_export_service.py                        82      2     16      2    96%   53, 161
src/ai_lead_os/services/sample_data_service.py                            52      0      8      0   100%
src/ai_lead_os/services/website_intelligence_export_service.py            67      3     20      3    93%   43, 161, 167
src/ai_lead_os/utils/__init__.py                                           0      0      0      0   100%
src/ai_lead_os/utils/campaign_version_fingerprint.py                      11      0      0      0   100%
src/ai_lead_os/utils/datetime.py                                           3      0      0      0   100%
src/ai_lead_os/utils/identifiers.py                                        3      0      0      0   100%
src/ai_lead_os/utils/logging.py                                           30      0      2      0   100%
src/ai_lead_os/utils/normalization.py                                     68      5     30      3    92%   36, 56, 78, 81-82
src/ai_lead_os/utils/personalization_tokens.py                             8      0      2      0   100%
src/ai_lead_os/utils/provider_event_fingerprint.py                        14      0      0      0   100%
src/ai_lead_os/webhook/__init__.py                                         2      0      0      0   100%
src/ai_lead_os/webhook/receiver.py                                        85     30     14      0    68%   90-92, 118, 121-141, 144-149, 178-187
------------------------------------------------------------------------------------------------------------------
TOTAL                                                                  13691    958   2864    431    91%
Required test coverage of 90.0% reached. Total coverage: 91.08%
======================= 1006 passed in 190.99s (0:03:10) =======================
```

