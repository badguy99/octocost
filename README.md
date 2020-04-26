# octocost
Octocost is an app which works under [AppDaemon](https://www.home-assistant.io/docs/ecosystem/appdaemon/) within [Home Assistant](https://www.home-assistant.io/) which shows the yearly and month cost and usage of the Octopus Energy Agile Octopus Tariff
It creates and sets sensors for yearly and monthly cost (£) and usage (kWh), up to yesterday:
```
sensor.octopus_yearly_cost
sensor.octopus_yearly_usage
sensor.octopus_monthly_cost
sensor.octopus_monthly_usage
```
If can also pull monthly and yearly gas cost and usage, and have sensors for them set up, if the gas section is included in the yaml configuration:
```
sensor.octopus_yearly_gas_cost
sensor.octopus_yearly_gas_usage
sensor.octopus_monthly_gas_cost
sensor.octopus_monthly_gas_usage
```

The data is updated once every two hours, although in reality the data Octopus Energy gets only seems to be updated once a day, so this is a compromise between trying to be up-to-date, and not hammering their servers, when the data doesn't update very frequently anyway.

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)

### Installation
Use [HACS](https://github.com/custom-components/hacs) or download the octoblock directory from inside the apps directory [here](https://github.com/badguy99/octocost/releases) to your local apps directory, then add the configuration to enable the octocost module.


### Apps.yaml Configuration
```yaml
octocost:
  module: octocost 
  class: OctoCost 
  region: H
  mpan: <13 digit MPAN number>
  serial:  <Serial number>
  auth: <Octopus Energy API Key>
  startdate: 2020-02-23
  gas:
    mprn: <Gas MPRN number>
    gasserial: <Gas meter serial number>
    gas_tariff: FIX-12M-20-02-12
    gas_startdate: 2020-02-23
``` 
The module and class sections need to remain as above, other sections should be changed as required. The whole gas section is optional and can be excluded if not required.

| Field         | Changeable | Example          |
| -----         | ---------- | -------          |
| Title         | Yes        | octocost         |
| module        | No         | octocost         |
| class         | No         | OctoCost         |
| region        | Yes        | H                |
| mpan          | Yes        | 2000012345678    |
| serial        | Yes        | 20L123456        |
| auth          | Yes        | sk_live_abcdefg  |
| startdate     | Yes        | 2020-02-23       |
| gas:          | Yes        |                  |
| mprn          | Yes        | 1234567890       |
| gasserial     | Yes        | E1S12345678901   |
| gas_tariff    | Yes        | FIX-12M-20-02-12 |
| gas_startdate | Yes        | 2020-02-23       |

The `startdate` setting should be set to the date you started on the Agile Octopus tariff, not the date you joined Octopus Energy. It is used to adjust the start point if you joined within the current year or month, it should not be left blank if you joined earlier.
`region` is the region letter from the end of `E-1R-AGILE-18-02-21-H` which can be found on the [Octopus Energy developer dashboard](https://octopus.energy/dashboard/developer/) webpage in the Unit Rates section for your account.

### Lovelace UI Cards
Once the sensors are created, they can be displayed as cards within the Lovelace UI. For example:
```
      - entities:
          - entity: sensor.octopus_yearly_usage
            icon: 'mdi:flash'
            name: Yearly Usage (kWh)
          - entity: sensor.octopus_yearly_cost
            icon: 'mdi:cash'
            name: Yearly Cost (£)
          - entity: sensor.octopus_monthly_usage
            icon: 'mdi:flash'
            name: Monthly Usage (kWh)
          - entity: sensor.octopus_monthly_cost
            icon: 'mdi:cash'
            name: Monthly Cost (£)
        show_icon: true
        title: Octopus Usage / Cost
        type: glance
```
![Example Lovelace UI Usage and Cost glance card](https://github.com/badguy99/octocost/blob/master/LovelaceUsageCard.PNG)
