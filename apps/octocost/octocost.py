import datetime
import json

import dateutil.parser
import pytz
import requests
from appdaemon.plugins.hass import hassapi as hass


class OctoCost(hass.Hass):
    def initialize(self):
        self.auth = self.args["auth"]
        MPAN = self.args["mpan"]
        SERIAL = self.args["serial"]
        region = self.args.get("region", self.find_region(MPAN))
        gas = self.args.get("gas", None)
        if gas:
            gas_tariff = gas.get("gas_tariff", None)
            MPRN = gas.get("mprn", None)
            GASSERIAL = gas.get("gasserial", None)
            gasstartdate = datetime.date.fromisoformat(str(gas.get("gas_startdate")))

        elecstartdate = datetime.date.fromisoformat(str(self.args["startdate"]))

        consumptionurl = (
            "https://api.octopus.energy/"
            + "v1/electricity-meter-points/"
            + str(MPAN)
            + "/meters/"
            + str(SERIAL)
            + "/consumption/"
        )
        costurl = (
            "https://api.octopus.energy/v1/products/"
            + "AGILE-18-02-21/electricity-tariffs/E-1R-AGILE-18-02-21-"
            + str(region).upper()
            + "/standard-unit-rates/"
        )

        if gas:
            gasconsumptionurl = (
                "https://api.octopus.energy/"
                + "v1/gas-meter-points/"
                + str(MPRN)
                + "/meters/"
                + str(GASSERIAL)
                + "/consumption/"
            )
            gascosturl = (
                "https://api.octopus.energy/v1/products/"
                + gas_tariff
                + "/gas-tariffs/G-1R-"
                + gas_tariff
                + "-"
                + str(region).upper()
                + "/standard-unit-rates/"
            )

        self.run_in(
            self.cost_and_usage_callback,
            5,
            use=consumptionurl,
            cost=costurl,
            date=elecstartdate,
        )
        if gas:
            self.run_in(
                self.cost_and_usage_callback,
                65,
                use=gasconsumptionurl,
                cost=gascosturl,
                date=gasstartdate,
                gas=True,
            )

        for hour in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]:
            self.run_daily(
                self.cost_and_usage_callback,
                datetime.time(hour, 5, 0),
                use=consumptionurl,
                cost=costurl,
                date=elecstartdate,
            )

            if gas:
                self.run_daily(
                    self.cost_and_usage_callback,
                    datetime.time(hour, 7, 0),
                    use=gasconsumptionurl,
                    cost=gascosturl,
                    date=gasstartdate,
                    gas=True,
                )

    @classmethod
    def find_region(cls, mpan):
        url = "https://api.octopus.energy/v1/electricity-meter-points/" + str(mpan)
        meter_details = requests.get(url)
        json_meter_details = json.loads(meter_details.text)
        region = str(json_meter_details["gsp"][-1])
        return region

    def cost_and_usage_callback(self, kwargs):
        self.useurl = kwargs.get("use")
        self.costurl = kwargs.get("cost")
        self.startdate = kwargs.get("date")
        self.gas = kwargs.get("gas", False)
        today = datetime.date.today()
        self.yesterday = today - datetime.timedelta(days=1)
        startyear = datetime.date(today.year, 1, 1)
        startmonth = datetime.date(today.year, today.month, 1)
        startday = self.yesterday

        if today == startmonth:
            if today.month == 1:
                startmonth = datetime.date(today.year - 1, 12, 1)
            else:
                startmonth = datetime.date(today.year, today.month - 1, 1)
        if today == startyear:
            startyear = datetime.date(today.year - 1, 1, 1)

        if self.startdate > startmonth:
            startmonth = self.startdate

        if self.startdate > startyear:
            startyear = self.startdate

        dayusage, daycost = self.calculate_cost_and_usage(start=startday)
        self.log("Yesterday usage: {}".format(dayusage), level="INFO")
        self.log("Yesterday cost: {} p".format(daycost), level="INFO")

        monthlyusage, monthlycost = self.calculate_cost_and_usage(start=startmonth)
        self.log("Total monthly usage: {}".format(monthlyusage), level="INFO")
        self.log("Total monthly cost: {} p".format(monthlycost), level="INFO")

        yearlyusage, yearlycost = self.calculate_cost_and_usage(start=startyear)
        self.log("Total yearly usage: {}".format(yearlyusage), level="INFO")
        self.log("Total yearly cost: {} p".format(yearlycost), level="INFO")

        if not self.gas:
            self.set_state(
                "sensor.octopus_yearly_usage",
                state=round(yearlyusage, 2),
                attributes={"unit_of_measurement": "kWh", "icon": "mdi:flash"},
            )
            self.set_state(
                "sensor.octopus_yearly_cost",
                state=round(yearlycost / 100, 2),
                attributes={"unit_of_measurement": "£", "icon": "mdi:cash"},
            )
            self.set_state(
                "sensor.octopus_monthly_usage",
                state=round(monthlyusage, 2),
                attributes={"unit_of_measurement": "kWh", "icon": "mdi:flash"},
            )
            self.set_state(
                "sensor.octopus_monthly_cost",
                state=round(monthlycost / 100, 2),
                attributes={"unit_of_measurement": "£", "icon": "mdi:cash"},
            )
            self.set_state(
                "sensor.octopus_day_usage",
                state=round(dayusage, 2),
                attributes={"unit_of_measurement": "kWh", "icon": "mdi:flash"},
            )
            self.set_state(
                "sensor.octopus_day_cost",
                state=round(daycost / 100, 2),
                attributes={"unit_of_measurement": "£", "icon": "mdi:cash"},
            )
        else:
            self.set_state(
                "sensor.octopus_yearly_gas_usage",
                state=round(yearlyusage, 2),
                attributes={"unit_of_measurement": "m3", "icon": "mdi:fire"},
            )
            self.set_state(
                "sensor.octopus_yearly_gas_cost",
                state=round(yearlycost / 100, 2),
                attributes={"unit_of_measurement": "£", "icon": "mdi:cash"},
            )
            self.set_state(
                "sensor.octopus_monthly_gas_usage",
                state=round(monthlyusage, 2),
                attributes={"unit_of_measurement": "m3", "icon": "mdi:fire"},
            )
            self.set_state(
                "sensor.octopus_monthly_gas_cost",
                state=round(monthlycost / 100, 2),
                attributes={"unit_of_measurement": "£", "icon": "mdi:cash"},
            )

    def calculate_count(self, start):
        numberdays = self.yesterday - start
        numberdays = numberdays.days
        self.expectedcount = ((numberdays + 1) * 48) - 1

    def calculate_cost_and_usage(self, start):
        self.calculate_count(start=start)
        self.log("period_from: {}T00:00:00Z".format(start.isoformat()), level="DEBUG")
        self.log(
            "period_to: {}T23:59:59Z".format(self.yesterday.isoformat()), level="DEBUG"
        )
        rconsumption = requests.get(
            url=self.useurl
            + "?order_by=period&period_from="
            + start.isoformat()
            + "T00:00:00Z&period_to="
            + self.yesterday.isoformat()
            + "T23:59:59Z&page_size="
            + str(self.expectedcount),
            auth=(self.auth, ""),
        )

        rcost = requests.get(
            url=self.costurl
            + "?period_from="
            + start.isoformat()
            + "T00:00:00Z&period_to="
            + self.yesterday.isoformat()
            + "T23:59:59Z"
        )

        if rconsumption.status_code != 200:
            self.log(
                "Error {} getting consumption data: {}".format(
                    rconsumption.status_code, rconsumption.text
                ),
                level="ERROR",
            )
        if rcost.status_code != 200:
            self.log(
                "Error {} getting cost data: {}".format(rcost.status_code, rcost.text),
                level="ERROR",
            )

        jconsumption = json.loads(rconsumption.text)
        jcost = json.loads(rcost.text)

        usage = 0
        price = 0
        cost = []
        utc = pytz.timezone("UTC")

        results = jconsumption[u"results"]

        while jcost[u"next"]:
            cost.extend(jcost[u"results"])
            rcost = requests.get(url=jcost[u"next"])
            jcost = json.loads(rcost.text)

        cost.extend(jcost[u"results"])
        cost.reverse()

        for period in results:
            curridx = results.index(period)
            usage = usage + (results[curridx][u"consumption"])
            if not self.gas:
                if (results[curridx][u"interval_start"]) != (
                    cost[curridx][u"valid_from"]
                ):
                    # Daylight Savings?
                    consumption_date = results[curridx][u"interval_start"]
                    if consumption_date.endswith("+01:00"):
                        date_time = dateutil.parser.parse(consumption_date)
                        utc_datetime = date_time.astimezone(utc)
                        utc_iso = utc_datetime.isoformat().replace("+00:00", "Z")
                        if utc_iso == (cost[curridx][u"valid_from"]):
                            (results[curridx][u"interval_start"]) = utc_iso
                        else:
                            self.log(
                                "UTC Unmatched consumption {}".format(
                                    results[curridx][u"interval_start"]
                                )
                                + " / cost {}".format(cost[curridx][u"valid_from"]),
                                level="ERROR",
                            )
                    else:
                        self.log(
                            "Unmatched consumption {}".format(
                                results[curridx][u"interval_start"]
                            )
                            + " / cost {}".format(cost[curridx][u"valid_from"]),
                            level="ERROR",
                        )
                price = price + (
                    (cost[curridx][u"value_inc_vat"])
                    * (results[curridx][u"consumption"])
                )
            else:
                # Only dealing with gas price which doesn't vary at the moment
                if jcost["count"] == 1:
                    cost = jcost["results"][0][u"value_inc_vat"]
                    price = price + cost * (results[curridx][u"consumption"])
                else:
                    self.log("Error: can only process fixed price gas", level="ERROR")
                    price = 0

        return usage, price
