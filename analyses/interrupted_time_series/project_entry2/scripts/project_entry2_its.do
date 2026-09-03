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
    local terms "_cons time post_july2024 time_after_july2024 2.month_of_year_stata 3.month_of_year_stata 4.month_of_year_stata 5.month_of_year_stata 6.month_of_year_stata 7.month_of_year_stata 8.month_of_year_stata 9.month_of_year_stata 10.month_of_year_stata 11.month_of_year_stata 12.month_of_year_stata"
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
end

newey high_c05_s3_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test1_primary_high_c05_s3 high_c05_s3_count

newey high_c03_s3_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test1_robust_high_c03_s3 high_c03_s3_count

newey high_c05_s3_timing_cons_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test1_timing_conservative_high_c05_s3 high_c05_s3_timing_cons_count

newey high_share_classified_c05_s3 time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test2_primary_high_share_classified high_share_classified_c05_s3

newey high_share_all_c05_s3 time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test2_robust_high_share_all high_share_all_c05_s3

newey high_share_classified_c03_s3 time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test2_robust_c03_high_share_classified high_share_classified_c03_s3

newey high_c05_s3_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test3_high_c05_s3 high_c05_s3_count

newey low_strict_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test3_low_strict low_strict_count

newey not_high_count time post_july2024 time_after_july2024 i.month_of_year_stata, lag(3)
_post_newey_rows test3_not_high not_high_count

postclose `handle'
macro drop PROJECT_ENTRY2_POST_HANDLE
use "../data/project_entry2_stata_results_tmp.dta", clear
gen str24 stata_status = "STATA_EXECUTED"
export delimited "../reports/project_entry2_stata_regression_table.csv", replace

log close _all
