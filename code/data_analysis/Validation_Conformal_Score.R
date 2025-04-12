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

# Set Networks and such
Replicate <- 1

# Turn on JIT
enableJIT(3)

# Load files
seed_maps <- np$load("seed_maps_no_cereb.npy")
phenos <- read.delim("ABIDE1_Pheno_PSM_matched.tsv")
seed_maps_val <- np$load("abide_2_seed_maps_no_cereb.npy")
phenos_val <- read.delim("ABIDE2_Pheno_PSM_matched.tsv")
output_directory <- ""
if (!dir.exists(output_directory)) {
  dir.create(output_directory, recursive = TRUE)
}

# Generate a bootstrap training sample
bootstrap_train <- 1:dim(phenos)[1]
# Generate a bootstrap testing sample
bootstrap_test <- 1:dim(phenos_val)[1]

# Make a vector to store p_values
p_values <- c()
p0_values <- c()

# Loop over networks
for (Network in 1:18) {

  # Get working frames
  working_map <- seed_maps[,,Network]
  working_map_val <- seed_maps_val[,,Network]
  regressed_vars <- as.matrix(cbind(1,phenos$AGE_AT_SCAN,phenos$fd_scrubbed))
  regressed_vars_val <- as.matrix(cbind(1,phenos_val$AGE_AT_SCAN,phenos_val$fd_scrubbed))
  classes_var <- ifelse(phenos$DX_GROUP == "Control", 0, 1)

  # Start to compute p_values
  for (i_test in 1:dim(phenos_val)[1]) {
    # Start timer
    tick <- proc.time()

    # Make augmented data sets
    working_map_i <- rbind(working_map[bootstrap_train,],
                           working_map_val[bootstrap_test[i_test],])
    regressed_vars_i <- rbind(regressed_vars[bootstrap_train,],
                              regressed_vars_val[bootstrap_test[i_test],])

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

    # Print outcomes
    #sink(paste('Output_Instance_',Replicate,'.txt',sep = ''), append = TRUE)
    print(c(Network,i_test,p_values[i_test],p0_values[i_test],proc.time()-tick))
  }
  # Write out results (train labs, test labs, p_values, 1-confidence)
  write.csv(cbind(bootstrap_train,bootstrap_test,p_values,p0_values),
            file = file.path(output_directory,paste('Results_Real_Network_',Network,'.csv',sep = '')))

}
