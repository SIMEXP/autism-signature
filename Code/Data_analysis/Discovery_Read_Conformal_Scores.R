# Hien Nguyen, 2019
# https://hiendn.github.io/

# Set working directory
setwd("")

# Load phenotypes
phenos <- read.delim("ABIDE1_Pheno_PSM_matched.tsv")
classes_var <- ifelse(phenos$DX_GROUP == "Control", 0, 1)

#################################################################
##                     Read Bootstrap P-values                 ##
#################################################################

# Make storage list
Replicate_list <- list()

for (Replicate in 1:100) {

  # Initialize an array for the results
  Results_array <- array(NA,
                         c(dim(phenos)[1],4,18))

  for (Network in 1:18) {
    # Read from file
    Read_file <- read.csv(paste('Results_Instance_',Replicate,'_Network_',Network,'.csv',sep = ''),
                          header = TRUE)

    # Store file to array
    Results_array[,,Network] <- as.matrix(Read_file[,2:5])
  }

  # Put array in list
  Replicate_list[[Replicate]] <- Results_array
}

#################################################################
##                   Compute combined p-values                 ##
#################################################################

### Subnets
Subnets_list <- list()
order_vector <- c(18,3,9,5,16,1,13,4,12,2,7,10,11,6,17,8,14,15)
Subnets_list[[1]] <- 3
Subnets_list[[2]] <- 18
Subnets_list[[3]] <- c(2,7,10)
Subnets_list[[4]] <- c(1,5,9,16)
Subnets_list[[5]] <- c(4,12,13)
Subnets_list[[6]] <- c(8,14,15)
Subnets_list[[7]] <- c(6,11,17)
Subnets_list[[8]] <- 1:18
Subnets_results_list <- list()
# Loop over subnet
for (subnet in 1:length(Subnets_list)) {

  # Combine Conformal
  Combine0_mat <- matrix(NA,dim(phenos)[1],100)
  Combine1_mat <- matrix(NA,dim(phenos)[1],100)
  Combine_results_mat <- matrix(NA,100,3)
  for (Replicate in 1:100) {
    # If there is only one network in the group, just use the value of this network
    if (length(Subnets_list[[subnet]])==1) {
      Combine0_mat[,Replicate] <- Replicate_list[[Replicate]][,4,Subnets_list[[subnet]]]
      Combine1_mat[,Replicate] <- Replicate_list[[Replicate]][,3,Subnets_list[[subnet]]]
      # If there is more than one network in the group, combine all p-values across the networks
    } else {
      Combine0_mat[,Replicate] <- apply(Replicate_list[[Replicate]][,4,Subnets_list[[subnet]]]^2,
                                        1,
                                        mean)
      Combine1_mat[,Replicate] <- apply(Replicate_list[[Replicate]][,3,Subnets_list[[subnet]]]^2,
                                        1,
                                        mean)
    }
  }

  Pvalue0_combine <- (2*Combine0_mat)^(1/2)
  Pvalue1_combine <- (2*Combine1_mat)^(1/2)
  write.table(Pvalue0_combine, file=paste("combined_networks_", subnet, "_p0.tsv", sep=""), sep="\t")
  write.table(Pvalue1_combine, file=paste("combined_networks_", subnet, "_p1.tsv", sep=""), sep="\t")

  Signif <- 0.2
  for (Replicate in 1:100)
  {
    # Take the first network for the current bootstrap because the subjects are the same across all networks
    # and we are only going to use this variable to determine the clinical label of individuals.
    WORKING <- Replicate_list[[Replicate]][,,1]

    # Store the results in a matrix of shape (100,3) with rows being bootstrap samples and columns being
    # 1: Number of individuals in the prediction region
    # 2: Accuracy of prediction in the prediction region
    # 3: Accuracy of prediction for everyone (including those that the model has no idea how to classify and just calls "No label")
    Combine_results_mat[Replicate,] <- c(
      length(WORKING[which(Pvalue1_combine[,Replicate]>Signif & Pvalue0_combine[,Replicate]<=Signif),2]),

      mean(classes_var[WORKING[which(Pvalue1_combine[,Replicate]>Signif & Pvalue0_combine[,Replicate]<=Signif),2]]),

      (sum(classes_var[WORKING[which(Pvalue1_combine[,Replicate]>Signif & Pvalue0_combine[,Replicate]<=Signif),2]]) +
         sum(1-classes_var[WORKING[which(Pvalue1_combine[,Replicate]<=Signif & Pvalue0_combine[,Replicate]>Signif),2]]) +
         length(classes_var[WORKING[which(Pvalue1_combine[,Replicate]>=Signif & Pvalue0_combine[,Replicate]>=Signif),2]]))/410
    )

  }
  # A list of length subnets that contains the results matrix for each combination of networks from above.
  Subnets_results_list[[subnet]] <- Combine_results_mat
}

#################################################################
##          Compute combined split-network p-values            ##
#################################################################

# A vector that denotes the order of networks in the hierarchical linkage
order_vector <- c(18,3,9,5,16,1,13,4,12,2,7,10,11,6,17,8,14,15)
Split_list <- list()
# Define the breakpoints between subnetworks based on the order_vector
# These numbers are not network numbers but positions inside the order vector
# The corresponding network number is then order_vector[position_number]
Split_list[[1]] <- c(0,9,18)

spl <- 1
Split_array <- array(NA,c(100,3,spl+1))
subnet <- 1
# Loop over subnet
for (subnet in 1:(spl+1)) {
  # Combine Conformal
  TestBootID_mat <- matrix(NA,dim(phenos)[1],100)
  Combine0_mat <- matrix(NA,dim(phenos)[1],100)
  Combine1_mat <- matrix(NA,dim(phenos)[1],100)
  Combine_results_mat <- matrix(NA,100,3)
  for (Replicate in 1:100) {
    # (bootstrap_train,bootstrap_test,p_values,p0_values)
    WORKING <- Replicate_list[[Replicate]][,,1]
    TestBootID_mat[, Replicate] <- WORKING[,2]
    # If there is only one network in the group, just use the value of this network.
    # The way this is computed here is:
    # 1) take the next breakpoint after the current one
    # 2) check how far away from the current one it is. This is the number of networks in the current split
    # 3) if the next breakpoint is only 1 larger than the current one, then the current split contains only a single network
    if ((Split_list[[spl]][subnet+1]-Split_list[[spl]][subnet])==1) {
      # We know that there is only one network in the current split and it's position number is equal to the next breakpoint.
      # So we get the network by using the next breakpoint directly
      Combine0_mat[,Replicate] <- Replicate_list[[Replicate]][,4,
                                                              order_vector[Split_list[[spl]][subnet+1]]]
      Combine1_mat[,Replicate] <- Replicate_list[[Replicate]][,3,
                                                              Split_list[[spl]][subnet+1]]
    }
    # If there is more than one network in the group, combine all p-values across the networks
    # !!!! Here we are using the squared mean
    else {
      # Now we need to get all the networks in the current split. They are delimited by the positions between the current and the
      # next breakpoint. Since the left breakpoint is not included in the set (because unless it is also the first breakpoint, it
      # is included in the preceding set) we add 1 to the left breakpoint but not to the right. If it was the first breakpoint, it's
      # value would be 0 so this still works.
      Combine0_mat[,Replicate] <- apply(Replicate_list[[Replicate]][,4,
                                                                    order_vector[(1+Split_list[[spl]][subnet]):Split_list[[spl]][subnet+1]]]^2,
                                        1,
                                        mean)
      Combine1_mat[,Replicate] <- apply(Replicate_list[[Replicate]][,3,
                                                                    order_vector[(1+Split_list[[spl]][subnet]):Split_list[[spl]][subnet+1]]]^2,
                                        1,
                                        mean)
    }
  }
  Pvalue0_combine <- (2*Combine0_mat)^(1/2)
  Pvalue1_combine <- (2*Combine1_mat)^(1/2)
  write.table(Pvalue0_combine, file=paste("split_net_", subnet, "_p0.tsv", sep=""), sep="\t")
  write.table(Pvalue1_combine, file=paste("split_net_", subnet, "_p1.tsv", sep=""), sep="\t")

}
