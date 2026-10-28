# Rental vs buy: one single-alert shape

The rental texts are the standard. A buy alert uses the same blocks in the same order, with "home" for "place" in the headline only.

1. Headline ("New place that fits" / "New home that fits")
2. Beds, baths and a stated type; area; price; range line ("In your target range", "In your stretch range", "Top of your stretch range", "Above your usual range"). Buying takes the range from `price_tiers`, else the buy budget (`buy.target_max`, `buy.price_max`); with no budget set there is no range line, for rentals too.
3. Details, one per line, ending with "Via <source>". Rentals: available date, pets, garage as asked. Buying: open house, HOA (only when stated), sq ft, lot (only the home's own), built, days on market.
4. Street, then its link right under it. The link is the clean listing page from any copy of the same home (Redfin, Zillow, Realtor.com). Rule when no copy has a clean link: the street stands alone, for rentals and buying alike.
5. "No rush."
6. "I'll keep watching."

Checked by `tests/test_rent_buy_shape.py`.

```
RENTAL (C1)                       | BUY (Y1)
----------------------------------|----------------------------------
New place that fits               | New home that fits
                                  |
1 bed, 1 bath apartment           | 3 bed, 2 bath house
Los Angeles, 90001                | Exampleville, 90001
$1,695/mo                         | $850,000
In your target range              | In your stretch range
                                  |
Available 12/1/26                 | HOA $150/mo
Via Demo PM                       | 1,600 sq ft
                                  | Lot 5,000 sq ft
                                  | Via Zillow
                                  |
100 Example St Unit 4             | 123 Maple Test Dr
https://example.com/listing/1     | https://www.zillow.com/homedetails/11111111_zpid/
                                  |
No rush.                          | No rush.
                                  |
I'll keep watching.               | I'll keep watching.
```
