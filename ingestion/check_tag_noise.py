import csv
from collections import Counter
rows = list(csv.DictReader(open("data/pairs_tags.csv")))
print(Counter(r["ingredient_class"] for r in rows if r["tag_class"] == "tag_change"))