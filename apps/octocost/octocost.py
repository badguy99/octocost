import appdaemon.plugins.hass.hassapi as hass
import datetime
import requests
import json


class OctoCost(hass.Hass):
    def initialize(self):
        self.auth = self.args['auth']
        MPAN = self.args['mpan']
        SERIAL = self.args['serial']
        region = self.args['region']
        self.startdate = datetime.date.fromisoformat(
            str(self.args['startdate']))
        self.consumptionurl = 'https://api.octopus.energy/' + \
            'v1/electricity-meter-points/' + str(MPAN) + '/meters/' + \
            str(SERIAL) + '/consumption/'
        self.costurl = 'https://api.octopus.energy/v1/products/' + \
            'AGILE-18-02-21/electricity-tariffs/E-1R-AGILE-18-02-21-' + \
            str(region).upper() + '/standard-unit-rates/'
        time = datetime.datetime.now()
        time = time + datetime.timedelta(seconds=5)
        self.run_every(self.cost_and_usage_callback, time, 120 * 60)

    def cost_and_usage_callback(self, kwargs):
        today = datetime.date.today()
        self.yesterday = datetime.date(today.year, today.month, today.day-1)
        startyear = datetime.date(today.year, 1, 1)
        startmonth = datetime.date(today.year, today.month, 1)

        if self.startdate > startmonth:
            startmonth = self.startdate

        if self.startdate > startyear:
            startyear = self.startdate

        monthlyusage, monthlycost = self.calculate_cost_and_usage(
            start=startmonth)
        print('Total monthly usage: {} kWh'.format(monthlyusage))
        print('Total monthly cost: {} p'.format(monthlycost))

        yearlyusage, yearlycost = self.calculate_cost_and_usage(
            start=startyear)
        print('Total yearly usage: {} kWh'.format(yearlyusage))
        print('Total yearly cost: {} p'.format(yearlycost))

        self.set_state('sensor.octopus_yearly_usage',
                       state=round(yearlyusage, 2),
                       attributes={'unit_of_measurement': 'kWh',
                                   'icon': 'mdi:flash'})
        self.set_state('sensor.octopus_yearly_cost',
                       state=round(yearlycost/100, 2),
                       attributes={'unit_of_measurement': '£',
                                   'icon': 'mdi:cash'})
        self.set_state('sensor.octopus_monthly_usage',
                       state=round(monthlyusage, 2),
                       attributes={'unit_of_measurement': 'kWh',
                                   'icon': 'mdi:flash'})
        self.set_state('sensor.octopus_monthly_cost',
                       state=round(monthlycost/100, 2),
                       attributes={'unit_of_measurement': '£',
                                   'icon': 'mdi:cash'})

    def calculate_count(self, start):
        numberdays = self.yesterday-start
        numberdays = numberdays.days
        self.expectedcount = ((numberdays+1)*48)-1

    def calculate_cost_and_usage(self, start):
        self.calculate_count(start=start)
        rconsumption = requests.get(url=self.consumptionurl +
                                    '?order_by=period&period_from=' +
                                    start.isoformat() +
                                    'T00:00:00Z&period_to=' +
                                    self.yesterday.isoformat() +
                                    'T23:59:59Z&page_size=' +
                                    str(self.expectedcount),
                                    auth=(self.auth, ''))

        rcost = requests.get(url=self.costurl + '?period_from=' +
                             start.isoformat() + 'T00:00:00Z&period_to=' +
                             self.yesterday.isoformat() + 'T23:59:59Z')

        jconsumption = json.loads(rconsumption.text)
        jcost = json.loads(rcost.text)

        jconsumption[u'count']

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
            if ((results[curridx][u'interval_start']) !=
               (cost[curridx][u'valid_from'])):
                print('Unmatched consumption {}'.format(
                    results[curridx][u'interval_start']) +
                    ' / cost {}'.format(cost[curridx][u'valid_from']))
            price = price + ((cost[curridx][u'value_inc_vat']) *
                             (results[curridx][u'consumption']))
        return usage, price
