version 18.0
clear all
set more off
capture log close _all

log using "../reports/project_entry2_stata_full.log", text replace

import delimited "../data/project_entry2_monthly.csv", clear
gen mdate = monthly(month, "YM")
format mdate %tm
tsset mdate
gen byte month_of_year_stata = month(dofm(mdate))

tempname handle
postfile `handle' str45 model_id str32 outcome str32 term double estimate std_error statistic p_value ci_low ci_high n_obs r_squared using "../data/project_entry2_stata_results_tmp.dta", replace
global PROJECT_ENTRY2_POST_HANDLE "`handle'"

program define _post_newey_rows
    args model_id outcome
    local terms "_cons time post_july2024 time_after_july2024"
    local r2 = .
    capture local r2 = e(r2)
    foreach term of local terms {
        local b = _b[`term']
        local se = _se[`term']
        local t = `b' / `se'
        local p = 2 * ttail(e(df_r), abs(`t'))
        local lo = `b' - invttail(e(df_r), 0.025) * `se'
        local hi = `b' + invttail(e(df_r), 0.025) * `se'
        post $PROJECT_ENTRY2_POST_HANDLE ("`model_id'") ("`outcome'") ("`term'") (`b') (`se') (`t') (`p') (`lo') (`hi') (e(N)) (`r2')
    }
    post $PROJECT_ENTRY2_POST_HANDLE ("`model_id'") ("`outcome'") ("monthFE") (.) (.) (.) (.) (.) (.) (e(N)) (`r2')
end

newey high_sensitivity_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test1_high_sensitivity_count high_sensitivity_count

newey high_sensitivity_share_all time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test2_high_share_all high_sensitivity_share_all

* Test 3A: Lower group
newey index_lower_pre_mean ///
    time post_july2024 time_after_july2024 ///
    i.month_of_year_stata, lag(3)
_post_newey_rows test3_lower_index index_lower_pre_mean
lincom time + time_after_july2024

* Test 3B: High group
newey index_high_pre_mean ///
    time post_july2024 time_after_july2024 ///
    i.month_of_year_stata, lag(3)
_post_newey_rows test3_high_index index_high_pre_mean
lincom time + time_after_july2024

* Test 3C: High minus Lower
newey index_diff_pre_mean ///
    time post_july2024 time_after_july2024 ///
    i.month_of_year_stata, lag(3)
_post_newey_rows test3_high_minus_lower_difference index_diff_pre_mean
test time_after_july2024 = 0

postclose `handle'
macro drop PROJECT_ENTRY2_POST_HANDLE
use "../data/project_entry2_stata_results_tmp.dta", clear
gen str24 stata_status = "STATA_EXECUTED"
export delimited "../reports/project_entry2_stata_regression_table.csv", replace

log close _all
