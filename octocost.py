import datetime
import requests
import json

MPAN=!secret elec_mpan
SERIAL=!secret elec_serial


consumptionurl = 'https://api.octopus.energy/v1/electricity-meter-points/' + MPAN + '/meters/' + SERIAL + '/consumption/'
costurl= 'https://api.octopus.energy/v1/products/AGILE-18-02-21/electricity-tariffs/E-1R-AGILE-18-02-21-H/standard-unit-rates/'

auth=!secret octopus_api

today = datetime.date.today()
yesterday = datetime.date(today.year, today.month, today.day-1)
#startyear = datetime.date(today.year, 1, 1)
startyear = datetime.date(today.year, 2, 19)
#startyear = datetime.date(today.year, 3, 1)
numberdays = yesterday-startyear
numberdays = numberdays.days

expectedcount= ((numberdays+1)*48)-1
expectedcount


rconsumption = requests.get(url=consumptionurl + '?order_by=period&period_from=' + startyear.isoformat() + 'T00:00:00Z&period_to=' + yesterday.isoformat() + 'T23:59:59Z&page_size=' + str(expectedcount), auth=(auth,''))

rcost = requests.get(url=costurl + '?period_from=' + startyear.isoformat() + 'T00:00:00Z&period_to=' + yesterday.isoformat() + 'T23:59:59Z')

jconsumption = json.loads(rconsumption.text)
jcost = json.loads(rcost.text)

jconsumption[u'count']

expectedcount= ((numberdays+1)*48)-1
expectedcount

usage = 0
price = 0
cost = []

results = jconsumption[u'results']

while jcost[u'next']:
    cost.extend(jcost[u'results'])
    rcost = requests.get(url=jcost[u'next'])
    jcost = json.loads(rcost.text)

cost.extend(jcost[u'results'])
cost.reverse()

for period in results:
    curridx = results.index(period)
    usage = usage + (results[curridx][u'consumption'])
    if (results[curridx][u'interval_start']) != (cost[curridx][u'valid_from']):
        print('Unmatched consumption {} / cost {}'.format(results[curridx][u'interval_start'],cost[curridx][u'valid_from']))
    price = price + ((cost[curridx][u'value_inc_vat'])*(results[curridx][u'consumption']))

print('Total usage: {} kWh'.format(usage))
print('Total cost: {} p'.format(price))
