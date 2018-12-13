packages_needed <- c("randomForest")
packages_missing <-
  packages_needed[!(packages_needed %in% installed.packages()[,"Package"])]
if(length(packages_missing))
  install.packages(packages_missing, repos='http://cran.uni-muenster.de')

library(randomForest)

dataset <- function() {
    data(ToothGrowth) # The Effect of Vitamin C on Tooth Growth in Guinea Pigs
    x <- ToothGrowth[,2:3]
    y <- ToothGrowth[,1]
    list(x, y)
}

train.randomForest <- function(x, y) {
    randomForest(x, y)
}
