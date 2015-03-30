packages_needed <- c("randomForest")
packages_missing <-
  packages_needed[!(packages_needed %in% installed.packages()[,"Package"])]
if(length(packages_missing))
  install.packages(packages_missing, repos='http://cran.uni-muenster.de')

library(randomForest)

dataset <- function() {
    x <- iris[,1:4]
    y <- as.factor(iris[,5])
    list(x, y)
}

train.randomForest <- function(x, y) {
    randomForest(x, as.factor(y))
}
