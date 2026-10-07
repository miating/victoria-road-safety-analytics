# Key Insights

These findings come from the queries in `sql/analytics/`. The full result tables are in
[`analysis_results.md`](analysis_results.md). Unless stated otherwise, the period is the complete
years 2012-2024. KSI means a crash in which someone was killed or seriously injured.

## Read this first: what the data can and cannot say

- **Injury crashes only.** There are only 4 non-injury crashes in 200,754 records. Every figure below describes crashes where someone was hurt, not all crashes.
- **No exposure data.** The dataset has no traffic volumes or kilometres travelled. A place, time or group with more crashes may simply have more traffic. Raw counts are therefore **not risk rates**.
- **Severity share, not crash risk.** Most comparisons use the *share of crashes that were KSI*. This describes how bad crashes are when they happen, not how likely they are to happen.
- **Association, not causation.** None of these results show that a factor *causes* more or worse crashes. Where an obvious confounder exists (usually speed), I say so.

## 1. Trends: no clear improvement in serious outcomes

- Comparing the 2012-2014 average with the 2022-2024 average:

  | Measure | Change |
  |---|---|
  | Injury crashes | +8.4% |
  | KSI crashes | +1.2% |
  | Fatal crashes | +8.7% |
  | Persons killed | +6.1% (258 to 273 per year) |

- Deaths were highest in 2023 (295) and 2016 (290), and lowest in 2020 (211), when COVID-19 restrictions reduced travel.
- **The 2017-2018 dip is probably a recording change, not a safety improvement.**
  - Total crashes fell by about 15% in 2017, but the fall was almost entirely in *other injury* crashes (9,707 in 2016 to 7,005 in 2018).
  - Serious injury crashes stayed at about 5,500 a year.
  - At the same time, the share of crashes with police attendance rose from about 73% to 81%.
  - This pattern fits fewer minor, non-police-attended crashes being captured in those years. I have not been able to confirm this from DTP documentation, so year-on-year comparisons of total crashes across 2016-2019 should be treated with care.
  - This is also why the KSI share swings between 33% and 45%.

## 2. Time: busiest in the afternoon, most severe at night and on weekends

- **Volume:** 3pm-6pm is the busiest period (15:00-17:59 is 24.4% of all crashes). There is also a morning peak at 8am.
- **Severity:**
  - The early hours are the opposite. Between 2am and 4am only about 0.8% of crashes happen each hour, but around half of them are KSI (51.7% at 3am).
  - During the afternoon peak, the KSI share is about 34-36%.
- **Day of week:**
  - Friday has the most crashes per day (43.4).
  - Sunday has the fewest (33.2), but the highest KSI share (42.0%) and fatal share (2.01%). Saturday is second on both.
- **Weekend vs weekday:**
  - Weekend crashes are twice as likely to happen at night (9.8% of weekend crashes vs 4.9% of weekday crashes).
  - Weekend crashes are more severe in every time band.
- **Seasonality is mild.**
  - Daily crash rates range from 0.90 (September) to 1.11 (February and March) of the average day. January, a holiday month, is low (0.92).
  - Severity barely changes by month (KSI share 36-39%).

## 3. Location: volume in the growth suburbs, severity in the country

- **Volume (2020-2024):**
  - Casey had the most crashes (3,718, 5.2% of the state), followed by Melbourne, Geelong and Hume.
  - These are large or fast-growing LGAs, so the ranking mostly reflects population and traffic.
- **Severity:**
  - The LGAs with the highest KSI share are rural, for example:

    | LGA | KSI share |
    |---|---|
    | Strathbogie | 59.3% |
    | Golden Plains | 55.2% |
    | Moyne | 55.2% |
    | Corangamite | 55.1% |

  - These are about 17-22 percentage points above the state average. This is consistent with higher-speed rural roads.
  - Geelong stands out as both high-volume and high-severity: 51.0% of its 2020-2024 crashes were KSI.
- **Hotspots:**
  - The location with the most crashes in 2020-2024 was Cemetery Road / Princes Street in Melbourne (26 crashes).
  - Three of the top 20 locations are on Clyde-Five Ways Road in Casey. Clyde-Five Ways Road / Ballarto Road had 22 crashes, 12 of them KSI, with a median of 27 days between crashes.
- **Rates per resident (2012-2024, ABS population):**
  - Victoria had 85.1 KSI crashes per 100,000 residents per year.
  - Casey, first by count, is 12% below that rate (75.1). Melbourne is 86% above it (158.2), because the CBD draws far more traffic than its residents generate.
  - The highest rates are rural: Murrindindi 313.5, Towong 272.0, Strathbogie 257.2, Mansfield 243.8. Tourist routes and through traffic make these overstate the risk to residents.
  - So counts point to where the most crashes happen and rates to where they are most out of proportion; a road safety team needs both.
- **Crashes cluster:**
  - The 1% of locations with the most crashes account for 11.3% of all crashes.
  - The top 10% account for 34.5%.
  - This only counts locations that had at least one crash, so true concentration across the whole road network is higher. This kind of concentration is the case for targeting engineering treatments at specific sites.

## 4. Environment: conditions matter less than speed

- **Wet roads are not associated with more severe crashes.**
  - Within every speed band, the KSI share on wet roads is equal to or lower than on dry roads. In 100-110 km/h zones it is 45.3% wet vs 52.2% dry.
  - One possible explanation is that drivers slow down in the wet, and that wet conditions add many minor crashes. The data cannot test this.
- **Weather:**
  - Fog (45.4% KSI, 3.59% fatal) and strong winds (43.4%) have the highest severity shares.
  - Rain (37.2%) is slightly below clear weather (39.7%).
- **Darkness without street lights** has the highest severity:
  - 51.4% KSI and 5.24% fatal, against 36.9% and 1.46% in daylight.
  - However, 52.8% of those crashes are in 100-110 km/h zones, compared with 14.9% of daytime crashes. Most of this difference is likely about road type and speed, not light alone.
  - Dark roads *with* street lights (mostly urban) have a much lower fatal share (1.71%).
- **Speed is the clearest severity gradient in the data.**
  - Dry-road KSI share rises from 35.2% (50 km/h or less) to 52.2% (100-110 km/h).
  - Fatal share rises from 0.82% to 5.16%.
- **"Not known" conditions have very low severity** (for example, 20.4% KSI where weather is not known). Severe crashes appear to be recorded more completely, so missing values are not random.

## 5. Vehicles and people: vulnerable road users carry the risk

- **Motorcycles:**
  - They are 7.8% of vehicles involved, but are in the highest share of KSI crashes (49.1%).
  - Motorcyclists are killed or seriously injured in 47.0% of their crashes.
  - They account for 16.5% of all deaths while being 6.1% of people involved.
- **Pedestrians:**
  - They have the highest death rate when involved: 28.5 per 1,000, against 5.7 per 1,000 for drivers.
  - They are 4.0% of people involved, but 15.0% of deaths.
- **Heavy vehicles** show the gap between involvement and harm:
  - They are in fatal crashes at 55.3 per 1,000 vehicles, almost five times the rate for light passenger vehicles (11.7).
  - Yet only 8.0% of their own occupants are killed or seriously injured.
  - The harm falls mostly on others in the crash.
- **Age:**
  - People aged 30-39 are the largest group involved (17.9%).
  - Severity rises steadily with age: 17-20% KSI for working ages, 24.6% for 65-69 and 34.1% for 70+.
  - The 70+ group also has the most deaths of any age group (627). This is consistent with older people being more physically vulnerable in a crash.
  - Young people aged 18-25 are 19.4% of everyone involved.

## 6. Performance: off track for the 2030 goal

- The Victorian Road Safety Strategy 2021-2030 aims to halve road deaths by 2030. It cites 266 deaths in 2019, which matches this data. It does not name a formal baseline year, so 2019 is an assumption here.
- A straight-line path from 266 in 2019 to 133 in 2030 puts 2024 at 206 deaths. The actual figure was 284, 38% above the path.
- Deaths were below the path in 2020 and 2021 (211 and 234), during COVID-19 travel restrictions, and above it from 2022.
- To reach 133 in 2030 from 284 in 2024, deaths would need to fall by 11.9% every year.

## Possible next steps

- Add traffic volume data. Population by LGA is now used for per-resident rates, but a true risk rate needs distance travelled.
- Check the 2017-2018 recording change with DTP before using total-crash trends for those years.
- Investigate the Clyde-Five Ways Road corridor in Casey, which appears three times in the top 20 hotspots.
