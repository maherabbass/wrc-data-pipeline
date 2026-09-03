# Body name -> WRC's internal numeric ID for the "body" filter on workplacerelations.ie/en/search.
# There's no public listing of these IDs, so they were found by manually submitting the site's
# search form with exactly one body checked at a time and reading the resulting "body=" value
# back off the results page URL.

BODY_IDS = {
    "equality_tribunal": 1,
    "employment_appeals_tribunal": 2,
    "labour_court": 3,
    "workplace_relations_commission": 15376,
}