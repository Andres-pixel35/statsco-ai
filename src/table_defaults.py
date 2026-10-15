# Per-table fallbacks for what a question leaves unsaid (which measure, unit, series...).
# build_sql_prompt attaches only the entries of the tables retrieved for the question.
# They fill gaps only - a question that names a measure/unit/series/breakdown overrides them.
TABLE_DEFAULTS = {
    "births": "`breakdown_dimension = 'national_total'` for a national count; the number of "
              "births, not the birth rate.",
    "child_labor": "most rows exist in two units, so always add a `unit` filter: `unit = "
                   "'percent'` (the child labor rate), `unit = 'people'` only for how many. "
                   "`concept = 'Working minors'`, "
                   "`geography_name = 'National total'`, `sex = 'total'`, "
                   "`breakdown_dimension = 'total'`.",
    "consumer_price_index": "inflation/CPI means `scope = 'city'`, `scope_member = 'National "
                            "total'`, `measure = 'annual_change_pct'` (annual inflation), not "
                            "the index, monthly or year-to-date change; the index only for "
                            "'index value/level/points'.",
    "deaths_by_department_and_cause": "`place_basis = 'place_of_residence'`; the number of "
                                      "deaths, not a death rate.",
    "deaths_by_municipality_and_cause": "the number of deaths.",
    "deaths_national": "the number of deaths, not the death rate.",
    "economic_activity_index": "`dataset = 'original'`, `measure = 'annual_growth_pct'`, "
                               "`activity = 'Total ISE'`. A question about the ISE / economic "
                               "activity index that names no measure ('how did it do', 'what "
                               "was the ISE in July', 'the monthly economic activity index') "
                               "gets annual growth, never the index; the index only for 'index "
                               "value/level/points'. Monthly growth exists only in `dataset = "
                               "'seasonally_adjusted'`.",
    "fiscal_balance": "the deficit/balance as `unit = 'percent'` (of GDP): concept "
                      "'Total Deficit / Surplus' for annual rows, 'Total Deficit' for month/"
                      "quarter rows. Revenue and spending in `unit = 'billions of COP'`.",
    "gdp_annual": "growth means `series = 'real (base 2015)'`, `measure = "
                  "'annual_growth_pct'`; the size of GDP (no growth word) means `series = "
                  "'nominal (2015 methodology)'`, `measure = 'level'`. Same split per capita.",
    "gdp_quarterly": "`approach = 'production'`, `breakdown_table = 'summary'`, `price_basis = "
                     "'constant 2015 prices'`, concept 'Gross Domestic Product'. Growth: "
                     "`year_over_year_growth_pct` for quarters, `annual_growth_pct` for annual "
                     "rows; the size of GDP (no growth word) is `measure = 'level'`.",
    "interest_rates": "an interest rate means `rate_type = 'monetary_policy'`; "
                      "'lending_average' only for lending, loan, credit or bank rates.",
    "labor_market": "`dataset = 'labor_force'`, `geography_name = 'National total'` (a named "
                    "department or region switches the dataset). In every dataset - regions "
                    "and departments too - always add a `sex` filter (`sex = 'total'` unless "
                    "the question names men or women) and `breakdown_dimension = 'total'` "
                    "unless it names a breakdown. A year with no month, window or semester "
                    "named always adds `period_type = 'annual'`, so the year's windows don't "
                    "come back beside the annual row. Informality means `dataset = "
                    "'informality'`, concept 'Informal', reported as `share_pct` (the "
                    "informality rate), not people.",
    "minimum_wage": "`concept = 'monthly minimum wage'`, `measure = 'nominal'`.",
    "misery_index": "`component = 'misery_index'`.",
    "population_departmental": "`measure = 'population'`.",
    "population_municipal": "`measure = 'population'`.",
    "population_national": "`measure = 'population'`.",
    "poverty_by_household_profile": "`poverty_type = 'monetary'`; `profile_subject = "
                                    "'household_head'` when the characteristic exists for both.",
    "poverty_by_sex": "`poverty_type = 'monetary'`.",
    "poverty_indicators": "`metric = 'poverty_incidence'` (the poverty rate, not people), "
                          "`poverty_type = 'monetary'`.",
    "productivity": "productivity means `approach = 'value_added'`, concept 'Total Factor "
                    "Productivity'; labor productivity means `approach = "
                    "'labor_per_hour_worked'`, concept 'Labor productivity per hour worked'.",
    "public_debt_balances": "`debt_scope = 'total'`, `measure = 'share_of_gdp_pct'`.",
    "public_debt_composition": "`debt_scope = 'total'`.",
    "traveler_flows": "`direction = 'inbound_foreigners'`.",
    "unemployment_monthly": "a plain unemployment rate question (no seasonally adjusted, "
                            "rolling three-month, sex, region or department named) reads "
                            "`unemployment_monthly` with `series = 'original'`; `labor_market` "
                            "only when it names a breakdown or a three-month window.",
}
