import argparse
import json
import sqlite3
import requests
import numpy

with open('config.json', 'r') as json_file:
    config = json.load(json_file)

# Init database
db = sqlite3.connect('skinner.db')
c = db.cursor()
c.execute('''DROP TABLE IF EXISTS unlocked''')
c.execute('''CREATE TABLE unlocked 
             (skinid INTEGER PRIMARY KEY)''')
c.execute('''DROP TABLE IF EXISTS minis''')
c.execute('''CREATE TABLE minis
             (miniid INTEGER PRIMARY KEY)''')
c.execute('''DROP TABLE IF EXISTS buys''')
c.execute('''CREATE TABLE buys
             (itemid INTEGER PRIMARY KEY)''')
db.commit()

baseurl = "https://api.guildwars2.com/v2/account/skins"
miniurl = "https://api.guildwars2.com/v2/account/minis"
buysurl = "https://api.guildwars2.com/v2/commerce/transactions/current/buys"

# Get list of item ids
response = requests.get(baseurl, headers={'Authorization': 'Bearer {}'.format(config['apikey'])})
assert(response.status_code == 200)
ids = response.json()

# Get data for each chunk
c = db.cursor()
ids = [(x,) for x in ids]
c.executemany("INSERT INTO unlocked VALUES (?)", ids)
db.commit()

# Get list of mini ids
response = requests.get(miniurl, headers={'Authorization': 'Bearer {}'.format(config['apikey'])})
assert(response.status_code == 200)
ids = response.json()

# Get data for each chunk
c = db.cursor()
ids = [(x,) for x in ids]
c.executemany("INSERT INTO minis VALUES (?)", ids)
db.commit()

# Now get list of unique item ids you have current buy orders for
response = requests.get(buysurl, headers={'Authorization': 'Bearer {}'.format(config['apikey'])})
response.raise_for_status()
# assert(response.status_code == 200)
recs = response.json()
ids = set()
for rec in recs:
    ids.add(rec["item_id"])
c = db.cursor()
ids = [(x,) for x in ids]
c.executemany("INSERT INTO buys VALUES (?)", ids)
db.commit()

db.close()
