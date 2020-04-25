import appdaemon.plugins.hass.hassapi as hass
import datetime
import requests
import json
import dateutil.parser
import pytz


class OctoCost(hass.Hass):
    def initialize(self):
        self.auth = self.args['auth']
        MPAN = self.args['mpan']
        SERIAL = self.args['serial']
        region = self.args.get('region', self.find_region(MPAN))

        self.startdate = datetime.date.fromisoformat(
            str(self.args['startdate']))

        consumptionurl = 'https://api.octopus.energy/' + \
            'v1/electricity-meter-points/' + str(MPAN) + '/meters/' + \
            str(SERIAL) + '/consumption/'
        costurl = 'https://api.octopus.energy/v1/products/' + \
            'AGILE-18-02-21/electricity-tariffs/E-1R-AGILE-18-02-21-' + \
            str(region).upper() + '/standard-unit-rates/'

        self.run_in(self.cost_and_usage_callback, 5,
                    use=consumptionurl, cost=costurl)

        for hour in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]:
            self.run_hourly(self.cost_and_usage_callback,
                            datetime.time(hour, 0, 0),
                            use=consumptionurl,
                            cost=costurl)

    def find_region(mpan):
        url = 'https://api.octopus.energy/v1/electricity-meter-points/' + \
              str(mpan)
        meter_details = requests.get(url)
        json_meter_details = json.loads(meter_details.text)
        region = str(json_meter_details['gsp'][-1])
        return region

    def cost_and_usage_callback(self, kwargs):
        self.useurl = kwargs.get('use')
        self.costurl = kwargs.get('cost')
        today = datetime.date.today()
        self.yesterday = today - datetime.timedelta(days=1)
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
        rconsumption = requests.get(url=self.useurl +
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

        usage = 0
        price = 0
        cost = []
        utc = pytz.timezone('UTC')

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
                # Daylight Savings?
                consumption_date = (results[curridx][u'interval_start'])
                if consumption_date.endswith('+01:00'):
                    date_time = dateutil.parser.parse(consumption_date)
                    utc_datetime = date_time.astimezone(utc)
                    utc_iso = utc_datetime.isoformat().replace("+00:00", "Z")
                    if utc_iso == (cost[curridx][u'valid_from']):
                        (results[curridx][u'interval_start']) = utc_iso
                    else:
                        print('UTC Unmatched consumption {}'.format(
                            results[curridx][u'interval_start']) +
                            ' / cost {}'.format(cost[curridx][u'valid_from']))
                else:
                    print('Unmatched consumption {}'.format(
                        results[curridx][u'interval_start']) +
                        ' / cost {}'.format(cost[curridx][u'valid_from']))
            price = price + ((cost[curridx][u'value_inc_vat']) *
                             (results[curridx][u'consumption']))
        return usage, price
