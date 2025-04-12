# Hien Nguyen, 2019
# https://hiendn.github.io/

# Load libraries
library(compiler)
library(fastcluster)
library(reticulate)
library(Rcpp)
library(RcppArmadillo)
library(Rfast)
np <- import("numpy")

# Read in arguments from command line
args <- commandArgs(TRUE)
Random.Seed <- strtoi(args[1])
Replicate <- strtoi(args[2])
Network <- strtoi(args[3])
Working_Directory <- args[4]
Output_Directory <- args[5]
Debug.Flag <- ifelse(length(args) >= 6, args[6] == "TRUE", FALSE)

# Turn on JIT
enableJIT(3)

# Set working directory
setwd(Working_Directory)

# Load files
# Shape: (Subjects, Voxels, Networks)
seed_maps <- np$load("seed_maps_no_cereb.npy")
phenos <- read.delim("ABIDE1_Pheno_PSM_matched.tsv")

# Reduce data size for debugging
if (Debug.Flag) {
  cat("⚠️  DEBUG MODE ACTIVE: limiting phenos to 20 rows\n"); flush.console()
  phenos <- phenos[1:20, ]
}

# Set a random seed
set.seed(Random.Seed)

# Generate a bootstrap training sample
bootstrap_train <- sample(1:dim(phenos)[1], replace = TRUE)
# Generate a bootstrap testing sample
bootstrap_test <- sample(1:dim(phenos)[1], replace = TRUE)

# Get working frames
working_map <- seed_maps[,,Network]
regressed_vars <- as.matrix(cbind(1,phenos$AGE_AT_SCAN,phenos$fd_scrubbed))
classes_var <- ifelse(phenos$DX_GROUP == "Control", 0, 1)

# Make a vector to store p_values
p_values <- c()
p0_values <- c()

# Start to compute p_values
for (i_test in 1:dim(phenos)[1]) {
  # Verbose progress
  cat(paste("🧮 Iteration", i_test, "of", dim(phenos)[1], "\n")); flush.console()
  # Start timer
  tick <- proc.time()

  # Make augmented data sets
  working_map_i <- rbind(working_map[bootstrap_train,],
                         working_map[bootstrap_test[i_test],])
  regressed_vars_i <- rbind(regressed_vars[bootstrap_train,],
                            regressed_vars[bootstrap_test[i_test],])

  # Make a matrix to store the residuals
  resid_map <- matrix(NA,dim(working_map_i)[1],dim(working_map_i)[2])
  for (ii in 1:dim(working_map_i)[2]) {
    resid_map[,ii] <- residuals(.lm.fit(regressed_vars_i,c(working_map_i[,ii])))
  }

  # Scale the residual map
  resid_map <- transpose(resid_map)
  resid_map <- standardise(resid_map)
  resid_map <- transpose(resid_map)

  # Make a distance map
  dist_mat <- Dist(resid_map, method = 'euclidean')

  # Conduct Hclust
  HC <- hclust(as.dist(dist_mat),method = 'ward.D')

  # Cut the tree
  sub_num <- 5
  HC_clustering <- cutree(HC, k = sub_num)

  # Compute the mean subtypes
  sub_means <- matrix(NA,sub_num,dim(resid_map)[2])
  for (ii in 1:sub_num) {
    sub_means[ii,] <- colMeans(resid_map[which(HC_clustering==ii),])
  }

  # Obtain weights
  vecInside <- Vectorize(function(x, y) cor(resid_map[x,],sub_means[y,]))
  weight_mat <- outer(1:dim(resid_map)[1],1:sub_num,vecInside)

  # Compute p-values
  classes_var_i <- c(classes_var[bootstrap_train],1)
  # Conduct logistic regression
  logistic_reg <- glm.fit(cbind(1,weight_mat),classes_var_i,family=binomial())
  # Compute alpha list
  eps_val <- 10^-16
  alpha_list <- (-1)^classes_var_i*logistic_reg$linear.predictors*eps_val^classes_var_i
  # Compute the p-value of the new individual
  p_values[i_test] <- mean(alpha_list>alpha_list[dim(resid_map)[1]]) +
    mean(alpha_list==alpha_list[dim(resid_map)[1]])

  # Compute compliment to p-values
  classes_var_i <- c(classes_var[bootstrap_train],0)
  # Conduct logistic regression
  logistic_reg <- glm.fit(cbind(1,weight_mat),classes_var_i,family=binomial())
  # Compute alpha list
  eps_val <- 10^-16
  alpha_list <- (-1)^classes_var_i*logistic_reg$linear.predictors*eps_val^classes_var_i
  # Compute the p-value of the new individual
  p0_values[i_test] <- mean(alpha_list>alpha_list[dim(resid_map)[1]]) +
    mean(alpha_list==alpha_list[dim(resid_map)[1]])
}

# Write out results (train labs, test labs, p_values, 1-confidence)
write.csv(cbind(bootstrap_train,bootstrap_test,p_values,p0_values),
     file = file.path(Output_Directory, paste('Results_Instance_',Replicate,'_Network_',Network,'.csv',sep = '')))
