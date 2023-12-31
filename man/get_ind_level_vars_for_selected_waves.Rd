% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/ukhls_data_reshapers.R
\name{get_ind_level_vars_for_selected_waves}
\alias{get_ind_level_vars_for_selected_waves}
\title{Get individual level variables for selected waves}
\usage{
get_ind_level_vars_for_selected_waves(
  varnames,
  vartypes,
  waves = letters[1:11],
  econLevel = 3,
  verbose = FALSE
)
}
\arguments{
\item{varnames}{the names of the variables to extract. Character vector of length k}

\item{vartypes}{the type of data (labels or values) to extract. Character vector of length k}

\item{waves}{character vector of valid waves}

\item{econLevel}{the level of aggregation to perform on the jbstat variable. Defaults to 3 (7 levels)}

\item{verbose}{Whether to give a detailed report of progress}
}
\value{
out - a widened and tidied dataset with wave, pidp, and selected variables as columns,
INCLUDING the state in the next wave
}
\description{
Get individual level variables for selected waves
}
