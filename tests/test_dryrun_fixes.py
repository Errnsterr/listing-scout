"""Found in the v1.2.0 live dry run: AppFolio apply links, and street names with ' - unit'."""
import os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src")); os.environ.setdefault("SCOUT_CRITERIA", os.path.join(HERE, "tests/fixtures/CRITERIA.test.yaml"))
import scout, notify
CARD = '''<div class="js-listing-item"><a href="/listings/detail/abc-1">x</a><span class="js-listing-address">100 Example Street - Unit C, Exampleville, CA 90001</span>
<dt class="detail-box__label">Rent</dt><dd class="detail-box__value">$3,950</dd>
<a href="/listings/rental_applications/new?listable_uid=abc-1&amp;source=Website">Apply Now</a></div>
<div class="js-listing-item"><a href="/listings/detail/abc-2">y</a></div>'''
scout.get = lambda u: CARD
L = scout.parse_appfolio({"url": "https://pm.appfolio.com/listings", "name": "PM"})
assert L[0]["apply_url"] == "https://pm.appfolio.com/listings/rental_applications/new?listable_uid=abc-1&source=Website", L[0]["apply_url"]
assert L[1]["apply_url"] is None
assert notify.short_where({"address": "100 Example Street - Unit C, Exampleville"}) == "Example"
assert notify.short_where({"address": "200 Sample Ave - C, Exampleville"}) == "Sample"
assert notify.short_where({"address": "5 Avon-Ridge Rd, X"}) == "Avon-Ridge"
print("ok test_dryrun_fixes")
