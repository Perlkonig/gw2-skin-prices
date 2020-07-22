import argparse
import json
import sqlite3
import requests
import numpy

# Init database
db = sqlite3.connect('skinner.db')
c = db.cursor()
c.execute('''DROP TABLE IF EXISTS prices''')
c.execute('''CREATE TABLE prices 
             (id INTEGER PRIMARY KEY, buy INTEGER, sell INTEGER)''')
c.execute("CREATE INDEX idx_buy ON prices (buy)")
c.execute("CREATE INDEX idx_sell ON prices (sell)")
db.commit()

parser = argparse.ArgumentParser()
parser.add_argument("--chunksize", type=int, default=100,\
    help="The maximum number of records to fetch in any given request.")
args = parser.parse_args()

# Generate table of Weapon, Armor, and Back items whose skins are still locked
c = db.cursor()
c.execute('INSERT INTO prices(id) SELECT id FROM items WHERE (type IN ("Weapon", "Back", "Armor")) AND (nosell = FALSE) AND (skin IS NOT NULL) AND (skin NOT IN (SELECT skinid FROM unlocked)) AND (skin NOT IN (SELECT DISTINCT items.skin FROM buys JOIN items ON (buys.itemid = items.id) WHERE items.skin IS NOT NULL))')
db.commit()

# Now add minis into the mix
c = db.cursor()
c.execute('INSERT INTO prices(id) SELECT id FROM items WHERE (type = "MiniPet") AND (nosell = FALSE) AND (id NOT IN (SELECT miniid FROM minis)) AND (id NOT IN (SELECT itemid FROM buys))')
db.commit()

# Get list of calculated ids
c = db.cursor()
c.execute("SELECT id FROM prices")
ids = c.fetchall()
c.close()
ids = [x[0] for x in ids]

baseurl = "https://api.guildwars2.com/v2/commerce/prices"

# chunk list so url length does not exceed 2k chars
numchunks = int((len(ids) / args.chunksize) + 1)
# numchunks = len(ids)
chunks = numpy.array_split(ids, numchunks)

# Get data for each chunk
c = db.cursor()
i = 0
data = list()
for chunk in chunks:
# for id in ids:
    i += 1
    param = ','.join([str(x) for x in chunk])
    print("Fetching chunk {} of {} ({} records)".format(i, len(chunks), len(chunk)))
    response = requests.get(baseurl + "?ids=" + param)
    # print("Fetching record {} of {} (id {})".format(i, len(ids), id))
    # response = requests.get(baseurl + str(id))
    # if ( (response.status_code != 200) and (response.status_code != 404)):
    #     response.raise_for_status()
    if ( (response.status_code >= 200) and (response.status_code < 300) ):
        rec = response.json()
        # print("\tFound {} records".format(len(rec)))
        for r in rec:
            # print("\tFound price record for id {}".format(r["id"]))
            buy = r["buys"]["unit_price"]
            sell = r["sells"]["unit_price"]
            data.append((r["id"], buy, sell))
        # c.execute("REPLACE INTO prices (id, buy, sell) VALUES (?, ?, ?)", (r["id"], buy, sell))
c.executemany("REPLACE INTO prices (id, buy, sell) VALUES (?, ?, ?)", data)
db.commit()

db.close()
