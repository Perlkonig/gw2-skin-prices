import os
import argparse
from datetime import date, timedelta, datetime
from time import sleep
import json
import sqlite3
from jinja2 import Environment, FileSystemLoader, select_autoescape

parser = argparse.ArgumentParser()
parser.add_argument("--type", type=str, default="Armor,Back,Weapon,MiniPet",\
    help="The main item type you're looking for. If you're not going to search also by subtype, then this can be a comma-delimited string listing multiple types. Supported types are 'Armor', 'Back', 'Weapon', and 'MiniPet'.")
# parser.add_argument("--subtype", type=str, default=None,\
#     help="The subtype of items you are looking for. Only works if a single main type was given. See the API documentation for the list of valid subtypes.")
parser.add_argument("--pricestyle", type=str, default="rounded",\
    help="Determines how you want prices to be displayed in the final report. 'raw' gives all prices in copper. 'decimal' gives the prices in gold with silver and copper as decimals. 'rounded' rounds everything to the nearest gold.")
parser.add_argument("--rarity", type=str, default=None,\
    help="The rarity of items you are looking for. An empty string searches for all rarities. You can provide a comma-delimited string of multiple rarities if you like. See the API documentation for the list of valid rarities.")
group = parser.add_mutually_exclusive_group()
group.add_argument("--maxbuy", type=int, default=None,\
    help="The maximum buy price you're willing to pay, in copper. Cannot be used in conjunction with --maxsell.")
group.add_argument("--maxsell", type=int, default=None,\
    help="The maximum sell price you're willing to pay, in copper. Cannot be used in conjunction with --maxbuy.")
args = parser.parse_args()

# Check argument sanity
# if (',' in args.type):
#     # if (args.subtype is not None):
#     #     raise TypeError("You cannot search a subtype if you selected multiple main types")
#     args.type = args.type.split(',')
# else:
#     args.type = [args.type]
args.type = args.type.split(',')

if (args.rarity is not None):
    if (',' in args.rarity):
        args.rarity = args.rarity.split(',')
    else:
        args.rarity = [args.rarity]

instr_type = "({})".format(','.join(["'{}'".format(x) for x in args.type]))
instr_rarity = None
if (args.rarity is not None):
    instr_rarity = "({})".format(','.join(["'{}'".format(x) for x in args.rarity]))

querystr = '''CREATE TEMPORARY TABLE joined AS SELECT prices.id, prices.buy, prices.sell, items.name, items.type, items.subtype, items.rarity, items.skin, items.chat FROM prices JOIN items ON prices.id = items.id WHERE (buy IS NOT NULL OR sell IS NOT NULL)'''
querystr += " AND (type in {})".format(instr_type)
if (args.rarity is not None):
    querystr += " AND (rarity IN {})".format(instr_rarity)

if (args.maxbuy is not None):
    querystr += " AND (buy <= {}) ORDER BY buy DESC".format(args.maxbuy)
elif (args.maxsell is not None):
    querystr += " AND (sell <= {}) ORDER BY sell DESC".format(args.maxsell)

# querystr += ", type, subtype, name"

db = sqlite3.connect('skinner.db')
c = db.cursor()
c.execute(querystr)
subquery = None
if (args.maxbuy is not None):
    subquery = '''SELECT joined.id, buy, sell, name, type, subtype, rarity, skin, chat FROM joined JOIN (
        SELECT id, MIN(buy) AS minbuy
        FROM joined  
        WHERE type != "MiniPet"
        GROUP BY skin 
    ) t on t.id = joined.id and joined.buy = t.minbuy'''
# elif (args.maxsell is not None):
else:
    subquery = '''SELECT joined.id, buy, sell, name, type, subtype, rarity, skin, chat FROM joined JOIN (
        SELECT id, MIN(sell) AS minsell
        FROM joined  
        WHERE type != "MiniPet"
        GROUP BY skin 
    ) t on t.id = joined.id and joined.sell = t.minsell'''
c.execute(subquery)
recs = c.fetchall()

# Add minis
miniquery = 'SELECT joined.id, buy, sell, name, type, subtype, rarity, skin, chat FROM joined WHERE type = "MiniPet"'
c.execute(miniquery)
minis = c.fetchall()

db.commit()
db.close()
recs = recs + minis
print("{} records found matching criteria".format(len(recs)))

def tuple2dict(tup):
    if (len(tup) != 9):
        print(tup)
        assert len(tup) == 9
    # See initial `querystr` variable for order
    node = dict()
    node["id"] = tup[0]
    node["name"] = tup[3]
    node["type"] = tup[4]
    node["subtype"] = tup[5]
    node["rarity"] = tup[6]
    node["skin"] = tup[7]
    node["chat"] = tup[8]

    if (args.pricestyle == 'decimal'):
        node["buy"] = tup[1] / 10000
        node["sell"] = tup[2] / 10000
    elif (args.pricestyle == 'rounded'):
        node["buy"] = round(tup[1] / 10000)
        node["sell"] = round(tup[2] / 10000)
    else:
        node["buy"] = tup[1]
        node["sell"] = tup[2]

    return node

recs = [tuple2dict(x) for x in recs]
if (args.maxbuy is not None):
    recs = sorted(recs, key=lambda x: x["buy"])
# elif (args.maxsell is not None):
else:
    recs = sorted(recs, key=lambda x: x["sell"])

env = Environment(
    loader=FileSystemLoader('./templates'),
    autoescape=select_autoescape(['html', 'xml'])
)
template = env.get_template('report.html')
html = template.render(recs=recs)
with open("report.html", "w") as f: 
    f.write(html) 
