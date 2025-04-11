# Hien Nguyen, 2019
# https://hiendn.github.io/

# Load libraries
library(compiler)
library(fastcluster)
library(reticulate)
use_python("")
library(Rcpp)
library(RcppArmadillo)
library(Rfast)
np <- import("numpy")

# Read in arguments from command line
args <- commandArgs(TRUE)
Working_Directory <- args[1]
Output_Directory <- args[2]

# Turn on JIT
enableJIT(3)

# Set working directory
setwd(Working_Directory)

# Load files
phenos <- read.delim("ABIDE1_Pheno_PSM_matched.tsv")
# Get working frames
regressed_vars <- as.matrix(cbind(1,phenos$AGE_AT_SCAN,phenos$fd_scrubbed))
classes_var <- ifelse(phenos$DX_GROUP == "Control", 0, 1)

for (Random.Seed in 1:100) {
  # Set a random seed
  set.seed(Random.Seed)
  # Generate a bootstrap training sample
  bootstrap_train <- sample(1:dim(phenos)[1], replace = TRUE)
  # Generate a bootstrap testing sample
  bootstrap_test <- sample(1:dim(phenos)[1], replace = TRUE)

  # Make a vector to store p_values
  p_values <- c()
  p0_values <- c()

  # Start to compute p_values
  for (i_test in 1:dim(phenos)[1]) {
    # Start timer
    tick <- proc.time()

    # Make augmented data sets
    regressed_vars_i <- rbind(regressed_vars[bootstrap_train,],
                              regressed_vars[bootstrap_test[i_test],])

    # Compute p-values
    classes_var_i <- c(classes_var[bootstrap_train],1)
    n_sub_in_bootstrap <- dim(regressed_vars_i)
    # Conduct logistic regression
    #logistic_reg <- glm.fit(cbind(1,weight_mat),classes_var_i,family=binomial())
    logistic_reg <- glm.fit(regressed_vars_i,classes_var_i,family=binomial())
    # Compute alpha list
    eps_val <- 10^-16
    alpha_list <- (-1)^classes_var_i*logistic_reg$linear.predictors*eps_val^classes_var_i
    # Compute the p-value of the new individual
    p_values[i_test] <- mean(alpha_list>alpha_list[n_sub_in_bootstrap]) +
      mean(alpha_list==alpha_list[n_sub_in_bootstrap])

    # Compute compliment to p-values
    classes_var_i <- c(classes_var[bootstrap_train],0)

    # Conduct logistic regression
    logistic_reg <- glm.fit(regressed_vars_i,classes_var_i,family=binomial())
    # Compute alpha list
    eps_val <- 10^-16
    alpha_list <- (-1)^classes_var_i*logistic_reg$linear.predictors*eps_val^classes_var_i
    # Compute the p-value of the new individual
    p0_values[i_test] <- mean(alpha_list>alpha_list[n_sub_in_bootstrap]) +
      mean(alpha_list==alpha_list[n_sub_in_bootstrap])

    # Print outcomes
    #sink(paste('Output_Instance_',Replicate,'.txt',sep = ''), append = TRUE)
    #print(c(Network,i_test,p_values[i_test],p0_values[i_test],proc.time()-tick))
  }
  # Write out results (train labs, test labs, p_values, 1-confidence)
  write.csv(cbind(bootstrap_train,bootstrap_test,p_values,p0_values),
            file = file.path(Output_Directory, paste('Results_Instance_',Random.Seed,'_NULL_Model_age_fd.csv',sep = '')))
}